"""
AST Patch Safety Engine — Phase 5

Validates generated code via tree-sitter AST parsing before it is
written to storage or the sandbox.  Implements the spec algorithm:

    1. Parse file to AST
    2. Identify safe edit zones
    3. Generate minimal diff
    4. Validate syntax
    5. Apply (or reject) patch

Key guarantees:
  - No file with critical parse errors is written to the sandbox.
  - Protected regions (design-contract :root tokens, @lock/@unlock blocks)
    are preserved even if the LLM attempts to overwrite them.
  - The engine is non-blocking: validation failures are surfaced as
    warnings/errors but never crash the pipeline.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import tree_sitter_typescript as _ts_typescript
import tree_sitter_css as _ts_css
import tree_sitter_javascript as _ts_javascript
from tree_sitter import Language, Parser, Node


# ── Severity levels ────────────────────────────────────────────────────────────

class Severity(str, Enum):
    error = "error"       # Blocks write
    warning = "warning"   # Allows write, notifies user
    info = "info"         # Logged only


@dataclass
class ValidationIssue:
    file: str
    line: int
    col: int
    message: str
    severity: Severity
    node_type: str = ""

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "col": self.col,
            "message": self.message,
            "severity": self.severity.value,
            "node_type": self.node_type,
        }


@dataclass
class ValidationResult:
    valid_edits: list[dict] = field(default_factory=list)
    rejected_edits: list[dict] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == Severity.error for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.error)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.warning)

    def to_dict(self) -> dict:
        return {
            "valid_count": len(self.valid_edits),
            "rejected_count": len(self.rejected_edits),
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [i.to_dict() for i in self.issues],
        }


# ── Parser initialization (one-time, module level) ────────────────────────────

_tsx_language = Language(_ts_typescript.language_tsx())
_ts_language = Language(_ts_typescript.language_typescript())
_css_language = Language(_ts_css.language())
_js_language = Language(_ts_javascript.language())

_LANGUAGE_MAP: dict[str, Language] = {
    ".tsx": _tsx_language,
    ".ts": _ts_language,
    ".jsx": _tsx_language,  # JSX is a subset of TSX
    ".js": _js_language,
    ".css": _css_language,
}


def _get_parser(ext: str) -> Parser | None:
    """Create a parser for the given file extension."""
    lang = _LANGUAGE_MAP.get(ext)
    if not lang:
        return None
    return Parser(lang)


# ── AST error extraction ──────────────────────────────────────────────────────

def _find_error_nodes(node: Node) -> list[Node]:
    """Recursively find all ERROR and MISSING nodes in an AST."""
    errors: list[Node] = []
    if node.type == "ERROR" or node.is_missing:
        errors.append(node)
    for child in node.children:
        errors.extend(_find_error_nodes(child))
    return errors


def _get_error_context(content: str, line: int, col: int, context_chars: int = 60) -> str:
    """Extract a snippet of text around the error location."""
    lines = content.split("\n")
    if 0 <= line < len(lines):
        source_line = lines[line]
        start = max(0, col - 20)
        end = min(len(source_line), col + context_chars)
        return source_line[start:end].strip()
    return ""


# ── Safe edit zone detection ──────────────────────────────────────────────────

@dataclass
class SafeZone:
    start_line: int
    end_line: int
    zone_type: str  # "lock", "root_tokens", "imports"
    read_only: bool = True


def _detect_safe_zones(content: str, tree: Any) -> list[SafeZone]:
    """Identify protected regions in a file."""
    zones: list[SafeZone] = []
    lines = content.split("\n")

    # 1. @lock / @unlock comment blocks
    lock_start = None
    for i, line in enumerate(lines):
        if "/* @lock */" in line or "// @lock" in line:
            lock_start = i
        elif lock_start is not None and ("/* @unlock */" in line or "// @unlock" in line):
            zones.append(SafeZone(lock_start, i, "lock"))
            lock_start = None

    # 2. CSS :root design-contract token blocks
    root_match = re.search(
        r'/\*\s*═+\s*DESIGN CONTRACT.*?═+\s*\*/',
        content, re.DOTALL,
    )
    if root_match:
        start_line = content[:root_match.start()].count("\n")
        end_line = content[:root_match.end()].count("\n")
        zones.append(SafeZone(start_line, end_line, "root_tokens"))

    return zones


def _apply_safe_zones(
    old_content: str | None,
    new_content: str,
    file_path: str,
) -> tuple[str, list[ValidationIssue]]:
    """Enforce safe zones: if old content has locked regions, preserve them.

    Returns (final_content, issues).
    """
    if not old_content:
        return new_content, []

    issues: list[ValidationIssue] = []
    ext = _get_ext(file_path)
    parser = _get_parser(ext)
    if not parser:
        return new_content, []

    try:
        old_tree = parser.parse(old_content.encode())
    except Exception:
        return new_content, []

    zones = _detect_safe_zones(old_content, old_tree)
    if not zones:
        return new_content, []

    result_lines = new_content.split("\n")
    old_lines = old_content.split("\n")

    for zone in zones:
        if not zone.read_only:
            continue
        # Extract the protected block from old content
        protected = old_lines[zone.start_line:zone.end_line + 1]
        if not protected:
            continue

        # Check if the protected block was removed or modified in new content
        protected_text = "\n".join(protected)
        if protected_text not in new_content:
            issues.append(ValidationIssue(
                file=file_path,
                line=zone.start_line,
                col=0,
                message=f"Protected {zone.zone_type} zone (lines {zone.start_line}-{zone.end_line}) was modified — restoring original",
                severity=Severity.warning,
                node_type=zone.zone_type,
            ))
            # Re-inject the protected block at the same position
            # (best-effort: insert at the beginning for imports, at original position otherwise)
            if zone.zone_type == "lock" and zone.start_line < len(result_lines):
                result_lines[zone.start_line:zone.start_line] = protected
            elif zone.zone_type == "root_tokens":
                # For CSS root tokens, inject after the last :root { line
                for i, line in enumerate(result_lines):
                    if ":root" in line and "{" in line:
                        # Insert inside the :root block
                        result_lines[i + 1:i + 1] = protected
                        break

    return "\n".join(result_lines), issues


# ── Diff generation ───────────────────────────────────────────────────────────

@dataclass
class DiffResult:
    diff_type: str  # "full_rewrite" | "minimal_patch" | "no_change"
    change_ratio: float
    additions: int
    deletions: int
    unified_diff: str

    def to_dict(self) -> dict:
        return {
            "type": self.diff_type,
            "change_ratio": round(self.change_ratio, 3),
            "additions": self.additions,
            "deletions": self.deletions,
        }


def generate_diff(
    old_content: str | None,
    new_content: str,
    file_path: str,
) -> DiffResult:
    """Generate a diff between old and new file content."""
    if old_content is None or old_content == "":
        return DiffResult("full_rewrite", 1.0, new_content.count("\n") + 1, 0, "")

    if old_content == new_content:
        return DiffResult("no_change", 0.0, 0, 0, "")

    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff_lines = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    ))
    unified = "\n".join(diff_lines)

    additions = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
    deletions = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

    total = max(len(old_lines), len(new_lines))
    change_ratio = (additions + deletions) / max(1, total)

    diff_type = "minimal_patch" if change_ratio < 0.5 else "full_rewrite"

    return DiffResult(diff_type, change_ratio, additions, deletions, unified)


# ── Core validation ───────────────────────────────────────────────────────────

def _get_ext(file_path: str) -> str:
    """Extract file extension."""
    dot = file_path.rfind(".")
    return file_path[dot:] if dot >= 0 else ""


def validate_file(
    file_path: str,
    content: str,
) -> list[ValidationIssue]:
    """Parse a single file and return syntax issues."""
    ext = _get_ext(file_path)
    parser = _get_parser(ext)

    if parser is None:
        # Unsupported extension — skip validation
        return []

    issues: list[ValidationIssue] = []

    try:
        tree = parser.parse(content.encode())
    except Exception as e:
        return [ValidationIssue(
            file=file_path, line=0, col=0,
            message=f"Tree-sitter parse failed: {e}",
            severity=Severity.error,
        )]

    # Find ERROR and MISSING nodes
    error_nodes = _find_error_nodes(tree.root_node)

    for node in error_nodes:
        line = node.start_point[0]
        col = node.start_point[1]
        context = _get_error_context(content, line, col)

        if node.is_missing:
            issues.append(ValidationIssue(
                file=file_path, line=line, col=col,
                message=f"Missing expected syntax near: {context}",
                severity=Severity.error,
                node_type="MISSING",
            ))
        else:
            issues.append(ValidationIssue(
                file=file_path, line=line, col=col,
                message=f"Syntax error near: {context}",
                severity=Severity.error,
                node_type="ERROR",
            ))

    # Additional structural checks for TSX/JSX
    if ext in (".tsx", ".jsx"):
        issues.extend(_check_tsx_structure(content, tree, file_path))

    # Additional checks for CSS
    if ext == ".css":
        issues.extend(_check_css_structure(content, file_path))

    return issues


def _check_tsx_structure(content: str, tree: Any, file_path: str) -> list[ValidationIssue]:
    """Extra checks beyond tree-sitter for TSX files."""
    issues: list[ValidationIssue] = []

    # Check for empty default export (common LLM mistake)
    if "export default" in content:
        # Verify the exported function/component has a return statement
        default_match = re.search(
            r'export\s+default\s+function\s+\w+\s*\([^)]*\)\s*\{([^}]*)\}',
            content, re.DOTALL,
        )
        if default_match and not default_match.group(1).strip():
            line = content[:default_match.start()].count("\n")
            issues.append(ValidationIssue(
                file=file_path, line=line, col=0,
                message="Default export function has empty body",
                severity=Severity.warning,
                node_type="empty_export",
            ))

    # Check for unmatched curly braces (common streaming truncation issue)
    open_braces = content.count("{")
    close_braces = content.count("}")
    if abs(open_braces - close_braces) > 2:
        issues.append(ValidationIssue(
            file=file_path, line=0, col=0,
            message=f"Unbalanced braces: {open_braces} open vs {close_braces} close (possible truncation)",
            severity=Severity.error,
            node_type="brace_mismatch",
        ))

    return issues


def _check_css_structure(content: str, file_path: str) -> list[ValidationIssue]:
    """Extra checks for CSS files."""
    issues: list[ValidationIssue] = []

    open_braces = content.count("{")
    close_braces = content.count("}")
    if open_braces != close_braces:
        issues.append(ValidationIssue(
            file=file_path, line=0, col=0,
            message=f"Unbalanced CSS braces: {open_braces} open vs {close_braces} close",
            severity=Severity.error,
            node_type="css_brace_mismatch",
        ))

    return issues


# ── Main validation entry point ───────────────────────────────────────────────

def validate_edits(
    edits: list[dict],
    existing_files: dict[str, str] | None = None,
) -> ValidationResult:
    """Validate all edits via AST parsing.

    Args:
        edits: List of {"file_path": str, "content": str, "action": "write"}
        existing_files: Optional dict of {file_path: old_content} for diff + safe zone checks

    Returns:
        ValidationResult with valid_edits, rejected_edits, and issues.
    """
    result = ValidationResult()
    existing = existing_files or {}

    for edit in edits:
        fp = edit.get("file_path", "")
        content = edit.get("content", "")

        if not content:
            result.rejected_edits.append(edit)
            result.issues.append(ValidationIssue(
                file=fp, line=0, col=0,
                message="Empty file content",
                severity=Severity.error,
            ))
            continue

        # Step 1: Parse and validate syntax
        file_issues = validate_file(fp, content)

        # Step 2: Safe zone enforcement
        old_content = existing.get(fp)
        if old_content:
            content, zone_issues = _apply_safe_zones(old_content, content, fp)
            file_issues.extend(zone_issues)
            # Update edit content with safe-zone-enforced version
            edit = {**edit, "content": content}

        # Step 3: Generate diff metadata
        diff = generate_diff(old_content, content, fp)
        edit = {**edit, "_diff": diff.to_dict()}

        # Decision: block on critical errors, allow warnings
        critical_errors = [i for i in file_issues if i.severity == Severity.error]
        result.issues.extend(file_issues)

        if critical_errors:
            result.rejected_edits.append(edit)
        else:
            result.valid_edits.append(edit)

    return result


# ── Convenience async wrapper (used by agent_pipeline.py) ─────────────────────

async def validate_edits_async(
    edits: list[dict],
    existing_files: dict[str, str] | None = None,
) -> ValidationResult:
    """Async wrapper around validate_edits for use in async pipeline."""
    import asyncio
    return await asyncio.to_thread(validate_edits, edits, existing_files)
