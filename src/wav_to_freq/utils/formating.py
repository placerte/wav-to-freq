import math

def is_finite(x: float) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def custom_format(x: float | None, fmt: str) -> str:
    if x is None or not is_finite(x):
        return ""
    return format(float(x), fmt)


def custom_mean(xs: list[float]) -> float | None:
    return (sum(xs) / len(xs)) if xs else None


def custom_min(xs: list[float]) -> float | None:
    return min(xs) if xs else None


def custom_max(xs: list[float]) -> float | None:
    return max(xs) if xs else None
