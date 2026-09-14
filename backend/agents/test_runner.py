from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from agents.fix_drafting import FixDraft, ManualInvestigationFix


class TestResult(BaseModel):
    status: Literal["passed", "failed", "skipped"]
    checks_run: list[str]
    summary: str


class TestRunnerAgent:
    """Perform safe static checks without executing generated fix content."""

    def run(self, fix_draft: FixDraft | ManualInvestigationFix) -> TestResult:
        if fix_draft.fix_type != "code" or fix_draft.risk_level == "high":
            return TestResult(
                status="skipped",
                checks_run=[],
                summary="skipped: manual review required before running validation",
            )

        if not fix_draft.diff_or_snippet.strip():
            return TestResult(
                status="failed",
                checks_run=["non-empty fix content check"],
                summary="Static validation failed: the code fix contains no diff or snippet to inspect.",
            )

        checks_run = ["non-empty fix content check"]
        language = self._infer_language(fix_draft.file_hint, fix_draft.diff_or_snippet)
        if language == "Python":
            checks_run.append("Python AST parse check")
            return self._check_python(fix_draft.diff_or_snippet, checks_run)

        checks_run.append(f"{language} brace and parenthesis balance check")
        if self._balanced_delimiters(fix_draft.diff_or_snippet):
            return TestResult(
                status="passed",
                checks_run=checks_run,
                summary=(
                    "Static validation passed: the proposed code content is non-empty and delimiters are balanced. "
                    "This is a simulated check, not a full test-suite execution."
                ),
            )

        return TestResult(
            status="failed",
            checks_run=checks_run,
            summary=(
                "Static validation failed: unbalanced braces or parentheses were detected. "
                "This is a simulated check, not a full test-suite execution."
            ),
        )

    def _infer_language(self, file_hint: str, content: str) -> str:
        suffix = Path(file_hint).suffix.lower()
        if suffix in {".py", ".pyi"} or re.search(r"\b(def|import|from|class)\s+", content):
            return "Python"
        if suffix in {".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".cs", ".cpp", ".c"}:
            return suffix.removeprefix(".")
        return "generic code"

    def _check_python(self, content: str, checks_run: list[str]) -> TestResult:
        source = self._strip_diff_markers(content)
        try:
            ast.parse(source)
        except SyntaxError as exc:
            return TestResult(
                status="failed",
                checks_run=checks_run,
                summary=(
                    f"Static Python parse failed at line {exc.lineno}: {exc.msg}. "
                    "This is a simulated check, not a full test-suite execution."
                ),
            )

        return TestResult(
            status="passed",
            checks_run=checks_run,
            summary=(
                "Static Python AST parse passed. This is a simulated check, not a full test-suite execution. "
                "The proposed code was not executed."
            ),
        )

    def _strip_diff_markers(self, content: str) -> str:
        lines = []
        for line in content.splitlines():
            if line.startswith(("+++ ", "--- ", "@@ ")):
                continue
            if line.startswith(("+", "-")):
                lines.append(line[1:])
            else:
                lines.append(line)
        return "\n".join(lines)

    def _balanced_delimiters(self, content: str) -> bool:
        pairs = {"}": "{", ")": "(", "]": "["}
        opening = set(pairs.values())
        stack: list[str] = []
        for character in content:
            if character in opening:
                stack.append(character)
            elif character in pairs:
                if not stack or stack.pop() != pairs[character]:
                    return False
        return not stack


__all__ = ["TestResult", "TestRunnerAgent"]
