#!/usr/bin/env python
"""Merge gate: every model directory must hold a validated model.

Run in CI (and locally before opening/merging a PR). It walks **every**
subdirectory of ``inflect_models_db/models/`` — not just the ones with a ``card.yaml`` — so a
paper-only submission (a PDF with no Antimony yet) is reported as *pending
extraction* and fails the gate. A model is accepted only when its Antimony has
been created and it validates against the published results in its card.

Exit code 0 iff every model directory is complete and valid.
"""

from __future__ import annotations

import sys
from pathlib import Path

from inflect_models_db.card import load_card
from inflect_models_db.registry import models_root
from inflect_models_db.run import build_core
from inflect_models_db.validate import validate_model


def main() -> int:
    root = models_root()
    dirs = sorted(p for p in root.iterdir() if p.is_dir()) if root.exists() else []
    if not dirs:
        print(f"no model directories under {root}")
        return 0

    core = build_core()
    ok = True
    for d in dirs:
        slug = d.name
        card_yaml = d / "card.yaml"

        if not card_yaml.is_file():
            # Paper-only / half-finished submission: not mergeable yet.
            ok = False
            has_paper = (d / "paper").exists() or any(d.glob("**/*.pdf"))
            why = (
                "pending extraction — PDF present but no card.yaml/model.ant yet"
                if has_paper
                else "no card.yaml"
            )
            print(f"[PENDING] {slug}: {why}")
            print(f"          run the `extract-model` skill to author and validate it")
            continue

        try:
            card = load_card(card_yaml)
        except Exception as e:  # noqa: BLE001 — report any card error as a gate failure
            ok = False
            print(f"[INVALID] {slug}: card.yaml error: {e}")
            continue

        try:
            report = validate_model(card, core=core)
        except Exception as e:  # noqa: BLE001
            ok = False
            print(f"[ERROR]   {slug}: validation raised: {e}")
            continue

        if report.ok:
            print(f"[OK]      {slug}: validates against published results")
        else:
            ok = False
            print(f"[FAIL]    {slug}:")
            for line in report.summary().splitlines()[1:]:
                if "FAIL" in line or "FAILED" in line:
                    print(f"          {line.strip()}")

    print()
    if ok:
        print("gate: PASS — every model is extracted and validated")
        return 0
    print("gate: FAIL — not mergeable until every model above is green")
    return 1


if __name__ == "__main__":
    sys.exit(main())
