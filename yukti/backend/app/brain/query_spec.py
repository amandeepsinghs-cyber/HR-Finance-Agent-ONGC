"""QuerySpec model and patch semantics (B2.1).

A QuerySpec is the frozen, versioned description of a data question. It serialises
to exactly the contract-v2 `query_spec` shape (`yukti/contracts/answer_contract.schema.json`,
`$defs.query_spec`), and a follow-up is expressed as a `SpecPatch` (`$defs.spec_patch`)
applied deterministically to the previous spec — never as a keyword hack.

Logical field names (``wc``, ``discipline``, ``grade``, ``station_tenure_years`` ...) are
defined per subject in `semantic_model.yaml`; the compiler maps them to columns.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

Op = Literal["=", "!=", ">", ">=", "<", "<=", "in", "not_in", "between", "like"]
Aggregation = Literal["count", "sum", "avg", "min", "max", "distinct_count", "ratio"]
ChartKind = Literal["pie", "donut", "bar", "column", "hbar", "stacked_bar", "grouped_bar", "line", "area", "combo",
                    "histogram", "box", "treemap", "heatmap", "waterfall", "bullet", "gauge", "funnel",
                    "scatter", "kpi", "table", "map"]


# Entity fields whose `in` filter + leading dimension means "compare these side by side".
COMPARE_FIELDS = {"wc", "asset", "field", "region", "discipline", "fy"}


class Filter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    op: Op = "="
    value: Any = None

    @field_validator("value")
    @classmethod
    def _shape(cls, v, info):
        op = info.data.get("op")
        if op in ("in", "not_in") and not isinstance(v, list):
            return [v]
        if op == "between" and (not isinstance(v, list) or len(v) != 2):
            raise ValueError("between needs [low, high]")
        return v

    def key(self) -> Tuple[str, str, str]:
        val = sorted(map(str, self.value)) if isinstance(self.value, list) else str(self.value)
        return (self.field, self.op, str(val))


class Period(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    fy: Optional[str] = Field(default=None, pattern=r"^FY\d{2}$")
    from_: Optional[str] = Field(default=None, alias="from")
    to: Optional[str] = None
    grain: Optional[Literal["year", "quarter", "month", "day"]] = None


class Sort(BaseModel):
    model_config = ConfigDict(extra="forbid")
    by: str
    dir: Literal["asc", "desc"] = "desc"


class QuerySpec(BaseModel):
    """Contract-v2 `query_spec` (version 1)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    version: Literal[1] = 1
    domain: Optional[Literal["hr", "finance", "policy"]] = None
    metric: str
    aggregation: Optional[Aggregation] = None
    dimensions: List[str] = Field(default_factory=list)
    filters: List[Filter] = Field(default_factory=list)
    period: Optional[Period] = None
    grain: Literal["aggregate", "row"] = "aggregate"
    sort: Optional[Sort] = None
    limit: Optional[int] = Field(default=None, ge=1)
    self_scope: bool = False

    # ------------------------------------------------------------ helpers
    def filter_on(self, field: str) -> Optional[Filter]:
        return next((f for f in self.filters if f.field == field), None)

    def to_contract(self) -> Dict[str, Any]:
        """Exactly the contract `query_spec` object (no nulls, 'from' alias)."""
        d = self.model_dump(by_alias=True, exclude_none=True, mode="json")
        d.pop("self_scope", None)
        return d

    @classmethod
    def from_contract(cls, data: Dict[str, Any]) -> "QuerySpec":
        return cls.model_validate(data)

    def is_compare(self) -> Optional[Tuple[str, List[Any]]]:
        """(field, values) when the spec splits an answer into 2–4 side-by-side entities."""
        if not self.dimensions or self.dimensions[0] not in COMPARE_FIELDS:
            return None  # e.g. grade IN (E5, E6, E7) + by grade is a breakdown, not a side-by-side comparison
        f = self.filter_on(self.dimensions[0])
        if f and f.op == "in" and isinstance(f.value, list) and 2 <= len(f.value) <= 4:
            return f.field, list(f.value)
        return None


class Compare(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    values: List[Any] = Field(min_length=2, max_length=4)


class SpecPatch(BaseModel):
    """Contract-v2 `spec_patch`: a partial QuerySpec merged onto the current one."""

    model_config = ConfigDict(extra="forbid")
    add_filters: List[Filter] = Field(default_factory=list)
    remove_filters: List[str] = Field(default_factory=list)
    dimensions: Optional[List[str]] = None
    period: Optional[Period] = None
    grain: Optional[Literal["aggregate", "row"]] = None
    sort: Optional[Sort] = None
    limit: Optional[int] = Field(default=None, ge=1)
    chart_kind: Optional[ChartKind] = None
    metric: Optional[str] = None
    aggregation: Optional[Aggregation] = None
    compare: Optional[Compare] = None

    def to_contract(self) -> Dict[str, Any]:
        d = self.model_dump(by_alias=True, exclude_none=True, mode="json")
        return {k: v for k, v in d.items() if v not in ([], None)}

    def is_presentation_only(self) -> bool:
        """True when the patch only changes the chart (no new query needed)."""
        d = self.to_contract()
        return set(d) <= {"chart_kind"} and "chart_kind" in d


def apply_patch(spec: QuerySpec, patch: SpecPatch) -> QuerySpec:
    """Deterministic patch semantics.

    - ``add_filters``: a filter on a field already filtered **replaces** it (entity shift,
      e.g. Delhi -> Mumbai); otherwise it is appended (narrowing, e.g. "only E5 and above").
    - ``remove_filters``: drop filters by field name.
    - ``dimensions``: replace the breakdown ("by discipline"); ``[]`` removes it.
    - ``period``: time shift. Setting ``fy`` clears ``from``/``to`` and vice versa; ``grain`` merges.
    - ``grain``: aggregate <-> row ("give me their names"). Switching to ``row`` keeps filters.
    - ``compare``: split into side-by-side entities: filter ``field in [current value, *values]``
      and make ``field`` the leading dimension. The current value of that field is kept first.
    - ``metric`` / ``aggregation`` / ``sort`` / ``limit``: replace.
    - ``chart_kind`` is presentation only; it never changes the spec.
    """
    new = copy.deepcopy(spec)

    if patch.remove_filters:
        drop = set(patch.remove_filters)
        new.filters = [f for f in new.filters if f.field not in drop]

    for f in patch.add_filters:
        new.filters = [x for x in new.filters if x.field != f.field] + [copy.deepcopy(f)]

    if patch.compare:
        field = patch.compare.field
        current = new.filter_on(field)
        vals: List[Any] = []
        if current is not None:
            vals += current.value if isinstance(current.value, list) else [current.value]
        vals += [v for v in patch.compare.values if v not in vals]
        new.filters = [x for x in new.filters if x.field != field] + [Filter(field=field, op="in", value=vals[:4])]
        new.dimensions = [field] + [d for d in new.dimensions if d != field]
        if new.grain == "row":
            new.grain = "aggregate"

    if patch.dimensions is not None:
        dims = list(patch.dimensions)
        cmp = new.is_compare()
        if cmp and cmp[0] not in dims:
            dims = [cmp[0]] + dims  # keep the comparison split when adding a breakdown
        new.dimensions = dims

    if patch.period is not None:
        cur = new.period.model_dump(by_alias=True, exclude_none=True) if new.period else {}
        upd = patch.period.model_dump(by_alias=True, exclude_none=True)
        if "fy" in upd:
            cur.pop("from", None)
            cur.pop("to", None)
        if "from" in upd or "to" in upd:
            cur.pop("fy", None)
        cur.update(upd)
        new.period = Period.model_validate(cur) if cur else None

    if patch.grain is not None:
        new.grain = patch.grain
        if patch.grain == "row":
            new.aggregation = None
    if patch.metric is not None:
        if patch.metric != new.metric and patch.sort is None:
            new.sort = None  # a sort on the old metric's column is meaningless for the new one
        new.metric = patch.metric
    if patch.aggregation is not None:
        new.aggregation = patch.aggregation
    if patch.sort is not None:
        new.sort = patch.sort
    if patch.limit is not None:
        new.limit = patch.limit
    return QuerySpec.model_validate(new.model_dump(by_alias=True))


def shift_period(spec: QuerySpec, years: int) -> QuerySpec:
    """Time shift helper: FY26 -> FY25 for years=-1 (used by 'vs last year' insights/chips)."""
    p = spec.period
    if not p or not p.fy:
        return spec
    n = int(p.fy[2:]) + years
    return apply_patch(spec, SpecPatch(period=Period(fy=f"FY{n:02d}")))
