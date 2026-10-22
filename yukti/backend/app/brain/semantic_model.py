"""Semantic model loader (B2): subjects, fields, metrics and templates from `semantic_model.yaml`."""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

MODEL_PATH = Path(__file__).resolve().parent / "semantic_model.yaml"


@dataclass
class FieldDef:
    name: str
    column: str
    kind: str = "categorical"          # entity:<type> | categorical | number | bool | fy
    label: Optional[str] = None

    @property
    def entity(self) -> Optional[str]:
        return self.kind.split(":", 1)[1] if self.kind.startswith("entity:") else None


@dataclass
class MetricDef:
    name: str
    subject: str
    expr: str
    aggregation: str
    unit: str
    label: str
    data_class: str = "general"
    polarity: Optional[str] = None


@dataclass
class SubjectDef:
    name: str
    domain: str
    table: str
    description: str
    period: str                         # snapshot | fiscal_year | fixed
    fields: Dict[str, FieldDef]
    metrics: Dict[str, MetricDef]
    base_filter: Optional[str] = None
    default_fy: Optional[str] = None
    row_columns: List[Dict[str, Any]] = field(default_factory=list)
    row_sort: Optional[Dict[str, str]] = None
    row_only: bool = False
    companions: List[str] = field(default_factory=list)
    dimension_fallbacks: Dict[str, str] = field(default_factory=dict)
    asof: Optional[Dict[str, Any]] = None


@dataclass
class TemplateDef:
    name: str
    domain: str
    label: str
    description: str
    period: str
    default_from: Optional[str] = None
    default_to: Optional[str] = None
    certified_id: Optional[str] = None


class SemanticModel:
    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.anchor_date: str = raw.get("anchor_date", "2026-10-19")
        self.subjects: Dict[str, SubjectDef] = {}
        self.metrics: Dict[str, MetricDef] = {}
        for sname, s in (raw.get("subjects") or {}).items():
            fields = {fn: FieldDef(name=fn, **fd) for fn, fd in (s.get("fields") or {}).items()}
            metrics = {}
            for mn, md in (s.get("metrics") or {}).items():
                metrics[mn] = MetricDef(name=mn, subject=sname, expr=md["expr"], aggregation=md.get("aggregation", "sum"),
                                        unit=md.get("unit", ""), label=md.get("label", mn),
                                        data_class=md.get("data_class", "general"), polarity=md.get("polarity"))
            subj = SubjectDef(
                name=sname, domain=s.get("domain", "hr"), table=s["table"], description=s.get("description", ""),
                period=s.get("period", "fixed"), fields=fields, metrics=metrics, base_filter=s.get("base_filter"),
                default_fy=s.get("default_fy"), row_columns=s.get("row_columns") or [], row_sort=s.get("row_sort"),
                row_only=bool(s.get("row_only")), companions=s.get("companions") or [],
                dimension_fallbacks=s.get("dimension_fallbacks") or {}, asof=s.get("asof"),
            )
            self.subjects[sname] = subj
            for mn, m in metrics.items():
                if mn in self.metrics:
                    raise ValueError(f"metric name {mn} defined twice")
                self.metrics[mn] = m
        self.templates: Dict[str, TemplateDef] = {
            tn: TemplateDef(name=tn, **td) for tn, td in (raw.get("templates") or {}).items()
        }

    def resolve_metric(self, name: str) -> Tuple[Optional[SubjectDef], Optional[MetricDef], Optional[TemplateDef]]:
        if name in self.templates:
            return None, None, self.templates[name]
        m = self.metrics.get(name)
        if not m:
            return None, None, None
        return self.subjects[m.subject], m, None

    def all_field_names(self) -> List[str]:
        names = set()
        for s in self.subjects.values():
            names.update(s.fields)
        return sorted(names | {"region"})


@lru_cache(maxsize=1)
def get_semantic_model() -> SemanticModel:
    return SemanticModel(yaml.safe_load(MODEL_PATH.read_text(encoding="utf-8")))
