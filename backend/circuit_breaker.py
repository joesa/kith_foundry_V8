"""
Per-provider circuit breaker for LLM calls.

Protects against slow or failing LLM providers cascading into worker
exhaustion (backed-up Inngest queues, unavailable uvicorn workers).

Each uvicorn worker process maintains its own in-process state — no Redis
needed.  The benefit is local: a single process stops hammering a dead
provider within seconds and fast-fails new requests while the window is open.

States
------
CLOSED    Normal operation. Failures tracked in a rolling window.
OPEN      Provider is unhealthy. All calls raise CircuitOpenError immediately.
HALF_OPEN Recovery probe. One call allowed; success → CLOSED, failure → OPEN.

Usage
-----
    from circuit_breaker import llm_breaker, CircuitOpenError

    try:
        response = await llm_breaker.call(
            provider="anthropic",
            coro=litellm.acompletion(model=..., ...)
        )
    except CircuitOpenError as e:
        # Fast-fail path
        raise
    except Exception:
        # Normal LLM error (already recorded by breaker)
        raise
"""
import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Raised when the circuit is OPEN and the call is fast-failed."""
    def __init__(self, provider: str, retry_after: float):
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(
            f"LLM provider '{provider}' circuit is OPEN — "
            f"retry in {retry_after:.0f}s"
        )


@dataclass
class _ProviderCircuit:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_ts: float = 0.0
    # Protects HALF_OPEN probe — only one concurrent probe allowed
    _probe_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class CircuitBreaker:
    """
    Parameters
    ----------
    failure_threshold : int
        Consecutive failures before opening the circuit (default 5).
    open_duration : float
        Seconds to stay OPEN before switching to HALF_OPEN (default 60).
    call_timeout : float
        Per-call timeout in seconds (default 120). Applied via asyncio.wait_for.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        open_duration: float = 60.0,
        call_timeout: float = 120.0,
    ):
        self._threshold = failure_threshold
        self._open_duration = open_duration
        self._call_timeout = call_timeout
        self._circuits: dict[str, _ProviderCircuit] = {}

    def _get(self, provider: str) -> _ProviderCircuit:
        if provider not in self._circuits:
            self._circuits[provider] = _ProviderCircuit()
        return self._circuits[provider]

    def state(self, provider: str) -> CircuitState:
        c = self._get(provider)
        if c.state == CircuitState.OPEN:
            if time.monotonic() - c.last_failure_ts >= self._open_duration:
                c.state = CircuitState.HALF_OPEN
        return c.state

    def _on_success(self, provider: str) -> None:
        c = self._get(provider)
        c.failure_count = 0
        c.state = CircuitState.CLOSED

    def _on_failure(self, provider: str) -> None:
        c = self._get(provider)
        c.failure_count += 1
        c.last_failure_ts = time.monotonic()
        if c.failure_count >= self._threshold:
            c.state = CircuitState.OPEN
            print(
                f"[circuit_breaker] '{provider}' OPENED after "
                f"{c.failure_count} failures"
            )

    async def call(self, provider: str, coro: Awaitable[Any]) -> Any:
        """
        Wrap an awaitable LLM call with circuit-breaker logic and timeout.

        Parameters
        ----------
        provider : str
            Provider name used as the circuit key (e.g. "anthropic", "openai").
        coro : Awaitable
            The coroutine to execute (e.g. litellm.acompletion(...)).
        """
        circuit_state = self.state(provider)

        if circuit_state == CircuitState.OPEN:
            c = self._get(provider)
            retry_after = self._open_duration - (time.monotonic() - c.last_failure_ts)
            raise CircuitOpenError(provider, max(0.0, retry_after))

        if circuit_state == CircuitState.HALF_OPEN:
            c = self._get(provider)
            # Only one probe at a time; others fast-fail while probe is running
            if c._probe_lock.locked():
                raise CircuitOpenError(provider, self._open_duration)
            async with c._probe_lock:
                return await self._execute(provider, coro)

        # CLOSED — normal path
        return await self._execute(provider, coro)

    async def _execute(self, provider: str, coro: Awaitable[Any]) -> Any:
        try:
            result = await asyncio.wait_for(coro, timeout=self._call_timeout)
            self._on_success(provider)
            return result
        except asyncio.TimeoutError:
            self._on_failure(provider)
            raise TimeoutError(
                f"LLM provider '{provider}' timed out after {self._call_timeout}s"
            )
        except CircuitOpenError:
            raise
        except Exception:
            self._on_failure(provider)
            raise

    # ── Synchronous helpers (for streaming call sites) ────────────────────────

    @staticmethod
    def extract_provider(model: str) -> str:
        """'anthropic/claude-3-5' → 'anthropic', 'gpt-4o' → 'openai'."""
        if "/" in model:
            return model.split("/")[0]
        # Bare model names — best-effort provider guess
        m = model.lower()
        if m.startswith("claude"):
            return "anthropic"
        if m.startswith(("gpt", "o1", "o3")):
            return "openai"
        if m.startswith("gemini"):
            return "gemini"
        return "default"

    def check(self, provider: str) -> None:
        """Raise CircuitOpenError immediately if the circuit is OPEN."""
        circuit_state = self.state(provider)
        if circuit_state == CircuitState.OPEN:
            c = self._get(provider)
            retry_after = self._open_duration - (time.monotonic() - c.last_failure_ts)
            raise CircuitOpenError(provider, max(0.0, retry_after))
        if circuit_state == CircuitState.HALF_OPEN:
            c = self._get(provider)
            if c._probe_lock.locked():
                raise CircuitOpenError(provider, self._open_duration)

    def record_success(self, provider: str) -> None:
        self._on_success(provider)

    def record_failure(self, provider: str) -> None:
        self._on_failure(provider)

    @property
    def default_timeout(self) -> float:
        return self._call_timeout

    def status(self) -> dict:
        """Return current circuit states for all tracked providers (for health checks)."""
        return {
            p: {
                "state": self.state(p).value,
                "failures": c.failure_count,
            }
            for p, c in self._circuits.items()
        }


# Module-level singleton shared by all call sites within this process
llm_breaker = CircuitBreaker(
    failure_threshold=5,
    open_duration=60.0,
    call_timeout=120.0,
)
