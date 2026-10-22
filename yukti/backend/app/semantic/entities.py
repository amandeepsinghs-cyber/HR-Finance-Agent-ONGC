"""Single entity dictionary for Yukti AI (B1.2).

The ONE place that maps work-centre / discipline / field / grade codes to names and
aliases (English, Hindi, Hinglish). Data attributes come from `entities.json`
(generated from the dimension tables by `scripts/build_entities.py`); curated
aliases, regions and groups come from `entity_aliases.yaml`.

Every other module must import from here instead of keeping its own map:

    from app.semantic.entities import get_entities
    ents = get_entities()
    ents.resolve_wc("Mumbai mein kitne log hain")  # -> "WC-MUM"
    ents.friendly("WC-DEL")                          # -> "Delhi HQ"
    ents.replace_codes({"wc": "WC-RAJ-BSN"})         # -> {"wc": "Rajasthan Basin"}
"""

from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

import yaml

SEMANTIC_DIR = Path(__file__).resolve().parent
ENTITIES_PATH = SEMANTIC_DIR / "entities.json"
ALIASES_PATH = SEMANTIC_DIR / "entity_aliases.yaml"

# Longest codes first so "WC-RAJ-BSN" is never read as "WC-RAJ" + "-BSN".
CODE_RE = re.compile(r"\b(WC-[A-Z]{3}(?:-[A-Z]{3})?|DISC-[A-Z]{2,4}|FLD-[A-Z0-9]{2,6})\b")
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
_MIN_AUTO_ALIAS_LEN = 4


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _strip_parens(text: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", text or "").strip()


class EntityDictionary:
    """Code <-> name <-> alias resolution for every entity type."""

    def __init__(self, data: Dict[str, Any], aliases: Dict[str, Any]):
        self.work_centres: Dict[str, Dict[str, Any]] = data.get("work_centres", {})
        self.disciplines: Dict[str, Dict[str, Any]] = data.get("disciplines", {})
        self.fields: Dict[str, Dict[str, Any]] = data.get("fields", {})
        self.grades: Dict[str, Dict[str, Any]] = data.get("grades", {})
        self.wc_notes: Dict[str, str] = aliases.get("work_centre_notes") or {}
        self._regions_cfg: Dict[str, Dict[str, Any]] = aliases.get("regions") or {}
        self.discipline_groups: Dict[str, List[str]] = aliases.get("discipline_groups") or {}

        # Region names ("western offshore") must never be swallowed by an automatic work-centre alias
        # derived from e.g. "Western Offshore Basin" (G4 B1 r1).
        self._reserved = {_norm(r) for r in self._regions_cfg} | {_norm(g) for g in self.discipline_groups}
        self.wc_alias = self._build(self.work_centres, aliases.get("work_centres") or {}, with_city=True)
        self.disc_alias = self._build(self.disciplines, aliases.get("disciplines") or {})
        self.field_alias = self._build(self.fields, aliases.get("fields") or {})
        self.grade_alias = {(_norm(a)): code for code, al in (aliases.get("grades") or {}).items() for a in al}

    # ------------------------------------------------------------------ build
    def _build(self, table: Dict[str, Dict[str, Any]], curated: Dict[str, List[str]],
               with_city: bool = False) -> Dict[str, str]:
        auto: Dict[str, set] = {}

        def add(alias: str, code: str) -> None:
            a = _norm(alias)
            if len(a) >= _MIN_AUTO_ALIAS_LEN:
                auto.setdefault(a, set()).add(code)

        city_count: Dict[str, int] = {}
        if with_city:
            for attrs in table.values():
                city = _norm(attrs.get("city", ""))
                city_count[city] = city_count.get(city, 0) + 1
        for code, attrs in table.items():
            for key in ("name", "short_name"):
                if attrs.get(key):
                    add(_strip_parens(attrs[key]), code)
                    add(re.sub(r"\s+(asset|basin|plant)$", "", _strip_parens(attrs[key]), flags=re.I), code)
            if with_city and attrs.get("city") and city_count.get(_norm(attrs["city"])) == 1:
                add(attrs["city"], code)
        # Ambiguous automatic aliases and region/group names are dropped; curated aliases always win.
        reserved = getattr(self, "_reserved", set())
        out = {a: next(iter(codes)) for a, codes in auto.items() if len(codes) == 1 and a not in reserved}
        for code, al in curated.items():
            for a in al:
                out[_norm(a)] = code
        return out

    # ---------------------------------------------------------------- resolve
    @staticmethod
    def _find_all(text: str, alias_map: Dict[str, str]) -> List[Tuple[int, int, str]]:
        """Non-overlapping alias hits (start, end, code), longest alias first."""
        t = _norm(text)
        taken: List[Tuple[int, int]] = []
        hits: List[Tuple[int, int, str]] = []
        for alias in sorted(alias_map, key=len, reverse=True):
            if _DEVANAGARI.search(alias):
                pattern = r"(?<![\u0900-\u097F])" + re.escape(alias) + r"(?![\u0900-\u097F])"
            else:
                pattern = r"(?<![\w&-])" + re.escape(alias) + r"(?![\w&-])"
            for m in re.finditer(pattern, t):
                s, e = m.span()
                if any(s < te and e > ts for ts, te in taken):
                    continue
                taken.append((s, e))
                hits.append((s, e, alias_map[alias]))
        return sorted(hits)

    def resolve_wc(self, text: str) -> Optional[str]:
        """First-mentioned work centre (longest alias wins on overlap), or None."""
        hits = self._find_all(text, self.wc_alias)
        return hits[0][2] if hits else None

    def resolve_wcs(self, text: str) -> List[str]:
        """All distinct work centres in order of mention (e.g. 'Delhi vs Mumbai')."""
        out: List[str] = []
        for _, _, code in self._find_all(text, self.wc_alias):
            if code not in out:
                out.append(code)
        return out

    def resolve_discipline(self, text: str) -> Optional[str]:
        hits = self._find_all(text, self.disc_alias)
        return hits[0][2] if hits else None

    def resolve_disciplines(self, text: str) -> List[str]:
        out: List[str] = []
        t = _norm(text)
        for g, codes in self.discipline_groups.items():
            if re.search(r"\b" + re.escape(g) + r"\b", t):
                out += [c for c in codes if c not in out]
        for _, _, code in self._find_all(text, self.disc_alias):
            if code not in out:
                out.append(code)
        return out

    def resolve_field(self, text: str) -> Optional[str]:
        hits = self._find_all(text, self.field_alias)
        return hits[0][2] if hits else None

    def resolve_grades(self, text: str) -> List[str]:
        out: List[str] = []
        for m in re.finditer(r"\b(E[0-9])\b", text or "", flags=re.I):
            g = m.group(1).upper()
            if g in self.grades and g not in out:
                out.append(g)
        for _, _, code in self._find_all(text, self.grade_alias):
            if code not in out:
                out.append(code)
        return out

    def region_wcs(self, name: str) -> List[str]:
        cfg = self._regions_cfg.get(_norm(name))
        if not cfg:
            return []
        if cfg.get("wc_ids"):
            return list(cfg["wc_ids"])
        return [code for code, a in self.work_centres.items()
                if all(str(a.get(k, "")).lower() == str(v).lower() for k, v in cfg.items())]

    def resolve_region(self, text: str) -> Optional[Tuple[str, List[str]]]:
        """Named region (e.g. 'North East'); ignores words inside a work-centre name ('Eastern Offshore')."""
        t = _norm(text)
        wc_spans = [(s, e) for s, e, _ in self._find_all(text, self.wc_alias)]
        for name in sorted(self._regions_cfg, key=len, reverse=True):
            for m in re.finditer(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", t):
                s, e = m.span()
                if not any(s < we and e > ws for ws, we in wc_spans):
                    return name, self.region_wcs(name)
        return None

    # ---------------------------------------------------------------- display
    def wc_name(self, code: str, short: bool = True) -> str:
        a = self.work_centres.get(code)
        if not a:
            return code
        return a.get("short_name" if short else "name") or a.get("name") or code

    def friendly(self, code: str) -> str:
        """Human label for any known code; unknown strings are returned unchanged."""
        if code in self.work_centres:
            return self.wc_name(code)
        if code in self.disciplines:
            return self.disciplines[code].get("name", code)
        if code in self.fields:
            return self.fields[code].get("name", code)
        return code

    def replace_codes(self, obj: Any) -> Any:
        """Recursively replaces known entity codes inside strings with friendly names."""
        if isinstance(obj, str):
            return CODE_RE.sub(lambda m: self.friendly(m.group(1)), obj)
        if isinstance(obj, dict):
            return {k: self.replace_codes(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.replace_codes(v) for v in obj]
        return obj

    def all_codes(self) -> Dict[str, set]:
        return {"wc": set(self.work_centres), "discipline": set(self.disciplines),
                "field": set(self.fields), "grade": set(self.grades)}


@lru_cache(maxsize=1)
def get_entities() -> EntityDictionary:
    data = json.loads(ENTITIES_PATH.read_text(encoding="utf-8"))
    aliases = yaml.safe_load(ALIASES_PATH.read_text(encoding="utf-8")) or {}
    return EntityDictionary(data, aliases)
