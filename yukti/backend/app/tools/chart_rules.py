"""Re-exports chart selection, precedence, and ChartSpec builder from `app.brain.chart_rules`."""

from __future__ import annotations

from app.brain.chart_rules import (
    CHART_KINDS,
    PAT_COLUMN_RE,
    PBT_COLUMN_RE,
    build_chart_spec,
    compute_histogram_bins,
    detect_unit,
    extract_requested_chart_kind,
    is_pbt_column,
    is_pure_replot_request,
    resolve_kind,
    select_chart_kind,
)

__all__ = [
    "CHART_KINDS",
    "PAT_COLUMN_RE",
    "PBT_COLUMN_RE",
    "build_chart_spec",
    "compute_histogram_bins",
    "detect_unit",
    "extract_requested_chart_kind",
    "is_pbt_column",
    "is_pure_replot_request",
    "resolve_kind",
    "select_chart_kind",
]
