"""test_world_bible_integrity.py: Enforce integrity and immutability of World Bible specifications.

Governing Policy (DELEGATION_PLAYBOOK.md § HARD RULES):
- Single source of truth: every generator reads data_bank/world_bible/*.yaml. Nothing is hard-coded that the Bible defines.
- Generators must NEVER mutate, edit, or inject attributes into world_bible/reference/*.yaml or other World Bible specs.
- Any discrepancy between the current world_bible/ files and the authoritative manifest
  (data_bank/tests/world_bible_manifest.sha256) causes this test to fail, listing changed/added/removed files.

Exclusions:
- data_bank/world_bible/derived/** (dynamically generated artifacts)
- data_bank/world_bible/story_register_actuals.yaml (dynamically generated actuals registry)
- Temporary, hidden, or cache files (.DS_Store, __pycache__)

Usage:
- Lead rebaselining:
    uv run python tests/test_world_bible_integrity.py --write-manifest
- Integrity verification (CLI):
    uv run python tests/test_world_bible_integrity.py
- Pytest execution:
    uv run pytest tests/test_world_bible_integrity.py
"""

import hashlib
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pytest

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent
WORLD_BIBLE_DIR = DATA_BANK_ROOT / "world_bible"
MANIFEST_FILE = Path(__file__).resolve().parent / "world_bible_manifest.sha256"

# Authoritative exclusions (generated files or transient cache)
EXCLUDED_REL_PATHS = {
    "story_register_actuals.yaml",
}


def is_file_excluded(path: Path) -> bool:
    """Check if file should be excluded from World Bible integrity tracking."""
    rel = path.relative_to(WORLD_BIBLE_DIR)
    rel_str = str(rel).replace("\\", "/")

    if rel_str in EXCLUDED_REL_PATHS:
        return True
    if rel_str.startswith("derived/") or rel.parts[0] == "derived":
        return True
    if path.name.startswith(".") or "__pycache__" in path.parts:
        return True
    return False


def compute_file_sha256(path: Path) -> str:
    """Compute hex SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def collect_world_bible_hashes() -> Dict[str, str]:
    """Scan world_bible/ and return a dict mapping relative repo path to SHA-256 hex string."""
    hashes: Dict[str, str] = {}
    if not WORLD_BIBLE_DIR.exists():
        return hashes

    for p in sorted(WORLD_BIBLE_DIR.rglob("*")):
        if p.is_file() and not is_file_excluded(p):
            rel_key = str(p.relative_to(DATA_BANK_ROOT)).replace("\\", "/")
            hashes[rel_key] = compute_file_sha256(p)

    return hashes


def read_manifest(manifest_path: Path = MANIFEST_FILE) -> Optional[Dict[str, str]]:
    """Read SHA-256 manifest file if present, returning dict of path -> sha256."""
    if not manifest_path.exists():
        return None

    manifest: Dict[str, str] = {}
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                digest, rel_path = parts
                manifest[rel_path.strip()] = digest.strip().lower()

    return manifest


def write_manifest(manifest_path: Path = MANIFEST_FILE) -> Dict[str, str]:
    """Write authoritative manifest of current World Bible files."""
    hashes = collect_world_bible_hashes()
    lines = [
        "# World Bible SHA-256 Integrity Manifest\n",
        "# Generated via: uv run python tests/test_world_bible_integrity.py --write-manifest\n",
        f"# Total tracked files: {len(hashes)}\n",
        "# FORMAT: <sha256_hex>  <relative_path>\n",
    ]
    for rel_path in sorted(hashes.keys()):
        lines.append(f"{hashes[rel_path]}  {rel_path}\n")

    with open(manifest_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return hashes


def compare_against_manifest() -> Tuple[List[Dict[str, str]], List[str], List[str]]:
    """Compare current files against manifest, returning (changed, added, removed)."""
    manifest = read_manifest(MANIFEST_FILE)
    if manifest is None:
        raise FileNotFoundError(
            f"Manifest not found: {MANIFEST_FILE.relative_to(DATA_BANK_ROOT)}\n"
            f"Run with --write-manifest to baseline: uv run python tests/test_world_bible_integrity.py --write-manifest"
        )

    current = collect_world_bible_hashes()

    current_keys = set(current.keys())
    manifest_keys = set(manifest.keys())

    added = sorted(list(current_keys - manifest_keys))
    removed = sorted(list(manifest_keys - current_keys))

    changed = []
    for path in sorted(list(current_keys & manifest_keys)):
        if current[path].lower() != manifest[path].lower():
            changed.append({
                "path": path,
                "expected": manifest[path],
                "actual": current[path],
            })

    return changed, added, removed


# -----------------------------------------------------------------------------
# PYTEST TEST INTERFACE
# -----------------------------------------------------------------------------
def test_world_bible_integrity():
    """Verify that no World Bible specification files have been modified or injected."""
    if not MANIFEST_FILE.exists():
        pytest.fail(
            f"World Bible manifest missing: {MANIFEST_FILE.relative_to(DATA_BANK_ROOT)}\n"
            f"The lead must baseline the manifest via: uv run python tests/test_world_bible_integrity.py --write-manifest",
            pytrace=False,
        )

    changed, added, removed = compare_against_manifest()

    if changed or added or removed:
        error_lines = ["\nWORLD BIBLE INTEGRITY VIOLATION DETECTED:"]
        if changed:
            error_lines.append(f"\n  [CHANGED FILES] ({len(changed)} file(s)):")
            for c in changed:
                error_lines.append(f"    - {c['path']}")
                error_lines.append(f"        Expected SHA-256: {c['expected']}")
                error_lines.append(f"        Actual SHA-256:   {c['actual']}")
        if added:
            error_lines.append(f"\n  [ADDED FILES] ({len(added)} file(s)):")
            for a in added:
                error_lines.append(f"    - {a}")
        if removed:
            error_lines.append(f"\n  [REMOVED FILES] ({len(removed)} file(s)):")
            for r in removed:
                error_lines.append(f"    - {r}")

        error_lines.append("\nGenerators must NEVER mutate files under data_bank/world_bible/.")
        error_msg = "\n".join(error_lines)
        pytest.fail(error_msg, pytrace=False)


# -----------------------------------------------------------------------------
# STANDALONE CLI RUNNER
# -----------------------------------------------------------------------------
def main():
    """CLI interface for checking or writing World Bible integrity manifest."""
    args = sys.argv[1:]

    if "--write-manifest" in args:
        print("=" * 70)
        print("BASELINING WORLD BIBLE SHA-256 MANIFEST")
        print("=" * 70)
        hashes = write_manifest(MANIFEST_FILE)
        print(f"Successfully wrote manifest with {len(hashes)} files to:")
        print(f"  {MANIFEST_FILE.relative_to(DATA_BANK_ROOT)}")
        print("\nTracked files:")
        for rel_path, digest in sorted(hashes.items()):
            print(f"  {digest[:12]}...  {rel_path}")
        print("=" * 70)
        sys.exit(0)

    print("=" * 70)
    print("WORLD BIBLE SHA-256 INTEGRITY CHECK")
    print("=" * 70)

    if not MANIFEST_FILE.exists():
        print(f"ERROR: Manifest missing at {MANIFEST_FILE.relative_to(DATA_BANK_ROOT)}")
        print("To baseline, run: uv run python tests/test_world_bible_integrity.py --write-manifest")
        sys.exit(1)

    try:
        changed, added, removed = compare_against_manifest()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if not changed and not added and not removed:
        print(f"SUCCESS: All tracked World Bible files match {MANIFEST_FILE.name}.")
        print("=" * 70)
        sys.exit(0)

    print(f"FAILED: Discrepancies found against {MANIFEST_FILE.name}:")
    if changed:
        print(f"\n  CHANGED ({len(changed)}):")
        for c in changed:
            print(f"    - {c['path']}")
            print(f"        Expected: {c['expected']}")
            print(f"        Actual:   {c['actual']}")
    if added:
        print(f"\n  ADDED ({len(added)}):")
        for a in added:
            print(f"    - {a}")
    if removed:
        print(f"\n  REMOVED ({len(removed)}):")
        for r in removed:
            print(f"    - {r}")

    print("\n" + "=" * 70)
    print("RESULT: FAILED World Bible Integrity Verification.")
    sys.exit(1)


if __name__ == "__main__":
    main()
