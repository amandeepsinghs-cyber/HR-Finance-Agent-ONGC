"""Re-exports chart selection, precedence, and ChartSpec builder from `app.brain.chart_rules`."""

from __future__ import annotations

from app.brain.chart_rules import (
    ALL_KINDS,
    CHART_KINDS,
    DataProfile,
    PART_OF_WHOLE,
    PAT_COLUMN_RE,
    PBT_COLUMN_RE,
    build_chart_spec,
    compatibility,
    compute_histogram_bins,
    detect_unit,
    extract_requested_chart_kind,
    is_pbt_column,
    is_pure_replot_request,
    kinds_for,
    profile,
    resolve_kind,
    select_chart_kind,
)

__all__ = [
    "ALL_KINDS",
    "CHART_KINDS",
    "DataProfile",
    "PART_OF_WHOLE",
    "PAT_COLUMN_RE",
    "PBT_COLUMN_RE",
    "build_chart_spec",
    "compatibility",
    "compute_histogram_bins",
    "detect_unit",
    "extract_requested_chart_kind",
    "is_pbt_column",
    "is_pure_replot_request",
    "kinds_for",
    "profile",
    "resolve_kind",
    "select_chart_kind",
]
