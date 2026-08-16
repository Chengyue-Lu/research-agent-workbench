"""Immutable isolated-mode bootstrap for the proxy container image."""

from __future__ import annotations

import sys

sys.path.insert(0, "/runtime")

from research_workbench.adapters.codex_egress_container import main  # noqa: E402

raise SystemExit(main())
