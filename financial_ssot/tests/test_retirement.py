import os
from pathlib import Path
import re
import pytest

def test_no_retired_files_read():
    backend_dir = Path(__file__).resolve().parent.parent.parent / "yukti" / "backend" / "app"
    
    banned_terms = [
        "build_10yr_financials",
        "financial_notes_corpus.jsonl",
        "ssot_financial_line_context.json",
        "FY_DIRECTOR_ACTIONS"
    ]
    
    violations = []
    
    for root, dirs, files in os.walk(backend_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                content = file_path.read_text(encoding="utf-8")
                
                for term in banned_terms:
                    if term in content:
                        violations.append(f"{file_path.name} contains '{term}'")
                        
    assert not violations, f"Found retired file references: {violations}"
