"""Rulebook content definitions for Step 3.1: ONGC Internal Rulebook Reconstructions.

Synthesizes public extracts, court judgments, circulars, and reference data into
7 comprehensive ONGC-style formal rulebooks.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class Subclause:
    ref: str
    title: str
    text: str

@dataclass
class Clause:
    clause_ref: str
    clause_title: str
    clause_text: str
    subclauses: List[Subclause] = field(default_factory=list)
    maps_to_question_ids: str = ""
    source_basis: str = "reconstruction"
    table_headers: Optional[List[str]] = None
    table_rows: Optional[List[List[str]]] = None

@dataclass
class Chapter:
    chapter_num: int
    title: str
    clauses: List[Clause] = field(default_factory=list)

@dataclass
class Annexure:
    annexure_id: str
    title: str
    description: str
    table_headers: Optional[List[str]] = None
    table_rows: Optional[List[List[str]]] = None
    notes: Optional[str] = None

@dataclass
class AmendmentRecord:
    revision_no: str
    date: str
    authority: str
    summary_of_changes: str

@dataclass
class Rulebook:
    doc_id: str
    title: str
    short_title: str
    ref_code: str
    effective_date: str
    issuer: str
    approving_authority: str
    classification: str
    preamble: str
    definitions: Dict[str, str]
    chapters: List[Chapter]
    annexures: List[Annexure]
    amendment_history: List[AmendmentRecord]
    real_excerpts_concordance: List[Dict[str, str]]
