#!/usr/bin/env bash
# Installs a local git pre-commit hook that blocks commits when the progress
# tracker finds integrity errors (stale checklist, closed bug with open step,
# ✅ step without G4 review). Bypass in an emergency with: git commit --no-verify
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
HOOK="$ROOT/.git/hooks/pre-commit"
cat > "$HOOK" <<'EOF'
#!/usr/bin/env bash
ROOT="$(git rev-parse --show-toplevel)"
python3 "$ROOT/scripts/progress/build_progress.py" --check || {
  echo "pre-commit: progress tracker found integrity errors (see above). Update UPGRADE_CHECKLIST.md / BUG_REGISTER.md, then re-run." >&2
  exit 1
}
git add "$ROOT/PROGRESS.md"
EOF
chmod +x "$HOOK"
echo "Installed $HOOK"
