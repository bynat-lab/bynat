"""Security guardrails for dynamic expressions evaluated via ``DataFrame.eval``."""

from typing import Any

__all__ = ["is_safe_expression"]

_BLOCKED_TOKENS = ("__", "@", "import", "lambda", ";")


def is_safe_expression(expression: Any) -> bool:
    """Perform a lightweight safety check for dynamic eval expressions.

    Notes:
        This is a guardrail, not a full sandbox. It blocks clearly risky
        tokens and non-string payloads before passing expressions to
        `DataFrame.eval`.

        Blocked tokens are `__`, `@`, `import`, `lambda`, and `;`
        (matched case-insensitively). A blank or non-string expression is
        also rejected.

    Args:
        expression (Any): Candidate expression text.

    Returns:
        bool: True if the expression passes basic safety checks, otherwise
        False.
    """
    if not isinstance(expression, str) or not expression.strip():
        return False

    lowered = expression.lower()

    return not any(token in lowered for token in _BLOCKED_TOKENS)
