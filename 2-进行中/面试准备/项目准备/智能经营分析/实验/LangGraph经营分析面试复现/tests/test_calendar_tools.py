import pytest

from business_analysis_repro.calendar_tools import calculate_business_period


@pytest.mark.parametrize(
    ("mode", "unit", "offset", "expected"),
    [
        ("rolling", "week", 0, ("2026-08-24", "2026-08-30")),
        ("calendar", "week", 0, ("2026-08-24", "2026-08-30")),
        ("calendar", "week", -1, ("2026-08-17", "2026-08-23")),
        ("calendar", "month", 0, ("2026-08-01", "2026-08-30")),
        ("calendar", "month", -1, ("2026-07-01", "2026-07-31")),
        ("calendar", "year", 0, ("2026-01-01", "2026-08-30")),
    ],
)
def test_business_period_semantics(
    mode: str,
    unit: str,
    offset: int,
    expected: tuple[str, str],
) -> None:
    result = calculate_business_period(
        reference_date="2026-08-30",
        mode=mode,  # type: ignore[arg-type]
        unit=unit,  # type: ignore[arg-type]
        offset=offset,
    )

    assert (result["start_date"], result["end_date"]) == expected


def test_exact_date_is_normalized_by_the_same_tool_contract() -> None:
    result = calculate_business_period(
        reference_date="2026-08-30",
        mode="exact",
        unit="day",
        exact_date="2026-08-15",
    )

    assert result["start_date"] == result["end_date"] == "2026-08-15"


def test_exact_mode_rejects_an_incomplete_specification() -> None:
    with pytest.raises(ValueError, match="exact模式"):
        calculate_business_period(
            reference_date="2026-08-30",
            mode="exact",
            unit="week",
        )
