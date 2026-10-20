"""
test_v0_harness.py — Wrapper in data_bank/tests/ pointing to verify/tests/test_v0_harness.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verify.tests.test_v0_harness import *
