from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import litellm
from pydantic import BaseModel, Field

from circuit_breaker import CircuitOpenError, llm_breaker
from prompts import MODE_CLASSIFIER_PROMPT


class ModeAlternative(BaseModel):
    productMode: str
    styleMode: str
    confidence: float = Field(ge=0.0, le=1.0)


class ModeReasoning(BaseModel):
    matchedKeywords: list[str] = Field(default_factory=list)
    matchedFeatures: list[str] = Field(default_factory=list)
    matchedAudienceSignals: list[str] = Field(default_factory=list)
    matchedToneSignals: list[str] = Field(default_factory=list)


class ModeClassificationResult(BaseModel):
    productMode: str
    styleMode: str
    confidence: float = Field(ge=0.0, le=1.0)
    alternatives: list[ModeAlternative] = Field(default_factory=list)
    reasoning: ModeReasoning = Field(default_factory=ModeReasoning)


def _extract_json(text: str) -> dict | list | None:
    clean = text.strip()
    if "```json" in clean:
        clean = clean.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in clean:
        clean = clean.split("```", 1)[1].split("```", 1)[0].strip()

    start = None
    open_ch = None
    close_ch = None
    depth = 0
    in_str = False
    esc = False
    for i, ch in enumerate(clean):
        if esc:
            esc = False
            continue
        if ch == "\\" and in_str:
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if start is None and ch in ("{", "["):
            start = i
            open_ch = ch
            close_ch = "}" if ch == "{" else "]"
            depth = 1
            continue
        if start is not None:
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(clean[start : i + 1])
                    except json.JSONDecodeError:
                        return None
    return None


class DesignModeService:
    def __init__(self) -> None:
        self._pack: dict[str, Any] | None = None
        backend_dir = Path(__file__).resolve().parent
        repo_root = backend_dir.parent
        self._candidate_paths = [
            backend_dir / "data" / "design_mode_engine_pack.json",
            repo_root / "design_mode_engine_pack.json",
            repo_root / "design-mode-implementation-pack" / "data" / "design_mode_engine_pack.json",
        ]

    def load_pack(self) -> dict[str, Any]:
        if self._pack is not None:
            return self._pack
        for path in self._candidate_paths:
            if path.exists():
                self._pack = json.loads(path.read_text(encoding="utf-8"))
                return self._pack
        raise FileNotFoundError("design_mode_engine_pack.json not found in expected locations")

    def get_all_product_modes(self) -> list[str]:
        pack = self.load_pack()
        categories = pack.get("product_mode_categories", {})
        return [mode for modes in categories.values() for mode in modes]

    def get_all_style_modes(self) -> list[str]:
        return list(self.load_pack().get("style_modes", []))

    def get_product_mode_categories(self) -> dict[str, list[str]]:
        categories = self.load_pack().get("product_mode_categories", {})
        return {key: list(values) for key, values in categories.items()}

    def get_design_profile(self, product_mode: str) -> dict[str, Any] | None:
        return self.load_pack().get("design_type_profiles", {}).get(product_mode)

    def get_blueprint(self, product_mode: str) -> dict[str, Any] | None:
        return self.load_pack().get("composition_blueprints", {}).get(product_mode)

    def validate_product_mode(self, product_mode: str | None) -> bool:
        return product_mode is None or product_mode in self.get_all_product_modes()

    def validate_style_mode(self, style_mode: str | None) -> bool:
        return style_mode is None or style_mode in self.get_all_style_modes()

    def get_mode_options(self) -> dict[str, Any]:
        product_modes = self.get_all_product_modes()
        style_modes = self.get_all_style_modes()
        return {
            "productModes": sorted(product_modes),
            "styleModes": sorted(style_modes),
            "productModeCategories": self.get_product_mode_categories(),
            "styleCount": len(style_modes),
            "productModeCount": len(product_modes),
        }

    def get_mode_context(self, product_mode: str, style_mode: str, *, confidence: float | None = None, locked_by_user: bool = False) -> dict[str, Any]:
        profile = self.get_design_profile(product_mode) or {}
        blueprint = self.get_blueprint(product_mode) or {}
        return {
            "productMode": product_mode,
            "styleMode": style_mode,
            "confidence": confidence,
            "lockedByUser": locked_by_user,
            "designType": profile.get("design_type"),
            "layoutModel": profile.get("layout_model"),
            "density": profile.get("density"),
            "recommendedPatterns": profile.get("recommended_patterns", []),
            "blueprint": {
                "defaultPages": blueprint.get("default_pages", []),
                "sectionOrder": blueprint.get("section_order", []),
                "responsiveRules": blueprint.get("responsive_rules", {}),
            },
        }

    def build_mode_context_block(self, product_mode: str, style_mode: str, *, confidence: float | None = None, locked_by_user: bool = False) -> str:
        ctx = self.get_mode_context(product_mode, style_mode, confidence=confidence, locked_by_user=locked_by_user)
        lines = [
            "DESIGN MODE CONTEXT",
            f"Product Mode: {ctx['productMode']}",
            f"Style Mode: {ctx['styleMode']}",
        ]
        if ctx.get("confidence") is not None:
            lines.append(f"Confidence: {ctx['confidence']:.4f}")
        if ctx.get("designType"):
            lines.append(f"Design Type: {ctx['designType']}")
        if ctx.get("layoutModel"):
            lines.append(f"Layout Model: {ctx['layoutModel']}")
        if ctx.get("density"):
            lines.append(f"Density: {ctx['density']}")
        if ctx.get("recommendedPatterns"):
            lines.append("Recommended Patterns: " + ", ".join(ctx["recommendedPatterns"]))
        blueprint = ctx.get("blueprint", {})
        if blueprint.get("defaultPages"):
            lines.append("Default Pages: " + ", ".join(blueprint["defaultPages"]))
        if blueprint.get("sectionOrder"):
            lines.append("Section Order: " + " -> ".join(blueprint["sectionOrder"]))
        responsive = blueprint.get("responsiveRules", {})
        if responsive:
            lines.append(
                "Responsive Rules: "
                + "; ".join(f"{key}={value}" for key, value in responsive.items())
            )
        lines.append(f"Locked By User: {'yes' if locked_by_user else 'no'}")
        return "\n".join(lines)

    async def classify_design_mode(
        self,
        *,
        model_id: str,
        llm_kwargs: dict[str, Any],
        prompt: str,
        app_name: str | None = None,
        app_type: str | None = None,
        description: str | None = None,
        features: list[str] | None = None,
        target_audience: str | None = None,
        preferred_style: str | None = None,
        required_product_mode: str | None = None,
    ) -> ModeClassificationResult:
        product_modes = self.get_all_product_modes()
        style_modes = self.get_all_style_modes()
        user_prompt = f"""
Project prompt: {prompt}
App name: {app_name or ''}
App type: {app_type or ''}
Description: {description or ''}
Features: {', '.join(features or [])}
Target audience: {target_audience or ''}
Preferred style: {preferred_style or ''}
Required product mode: {required_product_mode or ''}

Available product modes:
{', '.join(product_modes)}

Available style modes:
{', '.join(style_modes)}
""".strip()

        provider = llm_breaker.extract_provider(model_id)
        try:
            llm_breaker.check(provider)
            response = await llm_breaker.call(
                provider,
                litellm.acompletion(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": MODE_CLASSIFIER_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    stream=False,
                    timeout=llm_breaker.default_timeout,
                    **llm_kwargs,
                ),
            )
            raw = response.choices[0].message.content or ""
            payload = _extract_json(raw)
            if not isinstance(payload, dict):
                raise ValueError("Mode classifier returned invalid JSON")
            result = ModeClassificationResult.model_validate(payload)
        except CircuitOpenError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Design mode classification failed: {exc}") from exc

        if required_product_mode:
            result.productMode = required_product_mode
        if preferred_style and self.validate_style_mode(preferred_style):
            result.styleMode = preferred_style
        return result


design_mode_service = DesignModeService()
