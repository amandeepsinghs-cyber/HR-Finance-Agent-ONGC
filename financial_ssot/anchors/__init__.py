"""Anchor tables module for Yukti financial SSOT (SPEC-01 §10, SPEC-05 §5).

Exports the builders for:
- fact_segment
- fact_production_annual
- fact_reserves
- fact_hr_aggregates
- fact_price_realisation
"""
from __future__ import annotations

from financial_ssot.anchors.build_anchors import (
    build_all_anchors,
    build_fact_hr_aggregates,
    build_fact_price_realisation,
    build_fact_production_annual,
    build_fact_reserves,
    build_fact_segment,
)

__all__ = [
    "build_all_anchors",
    "build_fact_segment",
    "build_fact_production_annual",
    "build_fact_reserves",
    "build_fact_hr_aggregates",
    "build_fact_price_realisation",
]
