"""
utils/__init__.py
=================
General-purpose utility helpers shared across the application.
"""


def format_currency(value: float | None, suffix: str = "") -> str:
    """
    Return a human-readable currency string.
    e.g. 1_500_000_000 → "$1.50B"
    """
    if value is None or value == 0:
        return "N/A"
    sign = "-" if value < 0 else ""
    abs_val = abs(value)
    if abs_val >= 1e12:
        return f"{sign}${abs_val / 1e12:.2f}T{suffix}"
    if abs_val >= 1e9:
        return f"{sign}${abs_val / 1e9:.2f}B{suffix}"
    if abs_val >= 1e6:
        return f"{sign}${abs_val / 1e6:.2f}M{suffix}"
    return f"{sign}${abs_val:,.0f}{suffix}"


def safe_pct(value: float | None, decimals: int = 1) -> str:
    """Return a formatted percentage string, or 'N/A' if value is None/0."""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}%"


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min_val and max_val."""
    return max(min_val, min(max_val, value))
