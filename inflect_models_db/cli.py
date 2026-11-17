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

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
