"""Deterministic synthetic metric data for the August 2026 learning lab."""

from datetime import date, timedelta

DATA_START = date(2026, 8, 1)
DATA_DAYS = 31
CHANNELS = ("App", "API")
MERCHANT_GROUPS = ("连锁商家", "中小商家", "新入驻商家")

_WEEKLY_FACTORS = (-0.025, -0.01, 0.005, 0.018, 0.035, 0.052, -0.015)


def _date_keys() -> list[str]:
    return [(DATA_START + timedelta(days=offset)).isoformat() for offset in range(DATA_DAYS)]


def _split_total(total: float, shares: tuple[float, ...]) -> list[float]:
    """Round components while keeping their sum exactly equal to the total."""
    values = [round(total * share, 2) for share in shares[:-1]]
    values.append(round(total - sum(values), 2))
    return values


def build_premium_values(
    *,
    base: float,
    daily_growth: float,
    phase: int,
    total_overrides: dict[str, float] | None = None,
    channel_overrides: dict[str, dict[str, float]] | None = None,
) -> dict[str, dict[str, object]]:
    """Build daily amount data with consistent overall and breakdown totals."""
    values: dict[str, dict[str, object]] = {}
    total_overrides = total_overrides or {}
    channel_overrides = channel_overrides or {}

    for offset, date_key in enumerate(_date_keys()):
        weekly_factor = _WEEKLY_FACTORS[(offset + phase) % len(_WEEKLY_FACTORS)]
        total = round(base * (1 + daily_growth * offset) * (1 + weekly_factor), 2)
        total = total_overrides.get(date_key, total)

        if date_key in channel_overrides:
            channel = channel_overrides[date_key]
        else:
            app_share = 0.64 + ((offset + phase) % 5 - 2) * 0.004
            app, api = _split_total(total, (app_share, 1 - app_share))
            channel = {"App": app, "API": api}

        chain_share = 0.44 + ((offset + phase) % 4 - 1.5) * 0.006
        small_share = 0.39 + ((offset + phase) % 3 - 1) * 0.005
        new_share = 1 - chain_share - small_share
        chain, small, new = _split_total(
            total,
            (chain_share, small_share, new_share),
        )
        values[date_key] = {
            "overall": total,
            "merchant": {
                "连锁商家": chain,
                "中小商家": small,
                "新入驻商家": new,
            },
            "channel": channel,
        }
    return values


def build_rate_values(
    *,
    base_percent: float,
    daily_change: float,
    phase: int,
) -> dict[str, dict[str, object]]:
    """Build daily percentage-point data; rate breakdowns are not additive."""
    values: dict[str, dict[str, object]] = {}
    wave = (-0.42, -0.18, 0.06, 0.21, 0.37, 0.52, -0.27)

    for offset, date_key in enumerate(_date_keys()):
        overall = round(base_percent + daily_change * offset + wave[(offset + phase) % 7], 2)
        values[date_key] = {
            "overall": overall,
            "merchant": {
                "连锁商家": round(overall + 1.35, 2),
                "中小商家": round(overall - 0.55, 2),
                "新入驻商家": round(overall - 1.7, 2),
            },
            "channel": {
                "App": round(overall + 0.9, 2),
                "API": round(overall - 1.25, 2),
            },
        }
    return values
