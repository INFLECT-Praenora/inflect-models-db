"""Tiny CLI: ``inflect-models {list,validate,reproduce}``."""

from __future__ import annotations

import argparse
import sys

from inflect_models_db.registry import all_cards, get_model, list_models
from inflect_models_db.validate import reproduce_figures, validate_model


def _cmd_list(_args) -> int:
    slugs = list_models()
    if not slugs:
        print("no models found")
        return 0
    for card in all_cards():
        src = card.source
        cite = f"{src.get('authors', '?')} ({src.get('year', '?')})"
        print(f"{card.slug:40s} {cite}")
    return 0


def _cmd_validate(args) -> int:
    cards = [get_model(args.slug)] if args.slug else all_cards()
    ok = True
    for card in cards:
        report = validate_model(card)
        print(report.summary())
        ok = ok and report.ok
    return 0 if ok else 1


def _cmd_reproduce(args) -> int:
    cards = [get_model(args.slug)] if args.slug else all_cards()
    for card in cards:
        paths = reproduce_figures(card)
        for p in paths:
            print(f"wrote {p}")
    return 0


def _cmd_grade(args) -> int:
    """Grade extraction fidelity: does the Antimony faithfully encode the paper
    (every state, parameter, and target reconciled + cited)? Complements
    `validate` (which checks the published numbers). Models without an
    extraction.yaml are skipped, not failed."""
    from inflect_models_db.grade import grade_model

    cards = [get_model(args.slug)] if args.slug else all_cards()
    ok = True
    graded = 0
    for card in cards:
        report = grade_model(card, llm=args.llm)
        if report is None:
            print(f"{card.slug}: no extraction.yaml — skipped")
            continue
        graded += 1
        print(report.summary())
        ok = ok and report.ok
    if graded == 0:
        print("no models with an extraction.yaml to grade")
    return 0 if ok else 1


def _cmd_composites(_args) -> int:
    """Show the process-bigraph composite each model exposes — the handle a host
    (e.g. simulation-core) runs it by."""
    from inflect_models_db import bigraph

    cards = all_cards()
    if not cards:
        print("no models found")
        return 0
    for card in cards:
        obs = ", ".join(bigraph.card_observables(card))
        scen = ", ".join(card.scenario_names)
        print(f"{bigraph.generator_name(card.slug):44s} "
              f"scenarios=[{scen}] observables=[{obs}]")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inflect-models")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list curated models").set_defaults(func=_cmd_list)

    p_val = sub.add_parser("validate", help="validate against published results")
    p_val.add_argument("slug", nargs="?", help="model slug (default: all)")
    p_val.set_defaults(func=_cmd_validate)

    p_rep = sub.add_parser("reproduce", help="regenerate validation figures")
    p_rep.add_argument("slug", nargs="?", help="model slug (default: all)")
    p_rep.set_defaults(func=_cmd_reproduce)

    p_grade = sub.add_parser(
        "grade",
        help="grade extraction fidelity (Antimony vs the paper's structured reading)",
    )
    p_grade.add_argument("slug", nargs="?", help="model slug (default: all)")
    p_grade.add_argument(
        "--llm",
        action="store_true",
        help="also run the optional LLM reviewer (non-gating; needs INFLECT_LLM_REVIEW_CMD)",
    )
    p_grade.set_defaults(func=_cmd_grade)

    sub.add_parser(
        "composites",
        help="list the process-bigraph composite each model exposes (for simulation-core)",
    ).set_defaults(func=_cmd_composites)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
