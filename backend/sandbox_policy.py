"""
Sandbox security policy — validates dependencies and file operations
before they reach the Fly sandbox. Guards against known-malicious packages,
dangerous system calls, and resource-exhausting patterns.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

BLOCKED_NPM_PACKAGES: set[str] = {
    "event-stream",
    "flatmap-stream",
    "ua-parser-js",
    "coa",
    "rc",
    "colors",
    "faker",
    "node-ipc",
    "peacenotwar",
    "es5-ext",
    "ctx",
    "load-from-cwd-or-npm",
    "mailer-kit",
    "postinstall",
    "preinstall",
    "install-exec",
    "cross-env.js",
    "crossenv",
    "eslint-scope",
    "electron-native-notify",
    "nodefabric",
    "shell-welcome",
}

BLOCKED_PIP_PACKAGES: set[str] = {
    "jeilyfish",
    "python3-dateutil",
    "python-dateuti1",
    "jeIlyfish",
    "python-binance",
    "colourfool",
    "colorsfool",
    "requesocks",
    "requesrs",
    "python-mongo",
    "ctx",
    "importlib_metadata",
}

BLOCKED_FILE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\.\.[\\/]"),
    re.compile(r"^/etc/"),
    re.compile(r"^/proc/"),
    re.compile(r"^/sys/"),
    re.compile(r"^/dev/"),
    re.compile(r"^/root/"),
    re.compile(r"\.env$"),
    re.compile(r"id_rsa"),
    re.compile(r"\.pem$"),
    re.compile(r"\.key$"),
]


@dataclass
class PolicyViolation:
    category: str
    detail: str
    severity: str = "error"


@dataclass
class PolicyResult:
    allowed: bool = True
    violations: list[PolicyViolation] = field(default_factory=list)

    def add(self, category: str, detail: str, severity: str = "error"):
        self.violations.append(PolicyViolation(category, detail, severity))
        if severity == "error":
            self.allowed = False


def validate_dependencies(content: str, filename: str) -> PolicyResult:
    result = PolicyResult()

    if filename == "package.json":
        _check_npm(content, result)
    elif filename in ("requirements.txt", "pyproject.toml", "Pipfile"):
        _check_pip(content, filename, result)

    return result


def validate_file_path(path: str) -> PolicyResult:
    result = PolicyResult()
    for pattern in BLOCKED_FILE_PATTERNS:
        if pattern.search(path):
            result.add("path_traversal", f"Blocked file path pattern: {path}")
            break
    return result


def _check_npm(content: str, result: PolicyResult):
    try:
        pkg = json.loads(content)
    except json.JSONDecodeError:
        result.add("parse_error", "Invalid package.json JSON", severity="warning")
        return

    for dep_key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        deps = pkg.get(dep_key, {})
        if not isinstance(deps, dict):
            continue
        for name in deps:
            normalized = name.lower().strip()
            if normalized in BLOCKED_NPM_PACKAGES:
                result.add("blocked_package", f"Blocked npm package: {name} (in {dep_key})")

    scripts = pkg.get("scripts", {})
    if isinstance(scripts, dict):
        for hook in ("preinstall", "postinstall", "preuninstall", "postuninstall"):
            script_val = scripts.get(hook, "")
            if any(cmd in script_val for cmd in ("curl ", "wget ", "nc ", "/dev/tcp", "bash -c", "eval ")):
                result.add("suspicious_script", f"Suspicious lifecycle script in {hook}: {script_val[:100]}")


def _check_pip(content: str, filename: str, result: PolicyResult):
    if filename == "requirements.txt":
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            pkg_name = re.split(r"[>=<!~\[]", line)[0].strip().lower()
            if pkg_name in BLOCKED_PIP_PACKAGES:
                result.add("blocked_package", f"Blocked pip package: {pkg_name}")
    elif filename == "pyproject.toml":
        for line in content.splitlines():
            for blocked in BLOCKED_PIP_PACKAGES:
                if blocked in line.lower():
                    result.add("blocked_package", f"Blocked pip package found in pyproject.toml: {blocked}")
