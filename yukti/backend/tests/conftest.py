"""Shared pytest setup for the Yukti backend.

The v3 branch reads the v3 BigQuery datasets (`hrfin_*_v3`, published in P5.6).
Live-BigQuery tests assert v3 numbers (e.g. V19 943/419/645, reconciled field P&L),
so default the dataset suffix to `v3` unless the caller sets it explicitly.
Running `BQ_DATASET_SUFFIX= pytest ...` still targets the legacy P0 datasets.
"""

import os

os.environ.setdefault("BQ_DATASET_SUFFIX", "v3")
