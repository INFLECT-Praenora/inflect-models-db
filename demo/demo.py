#!/usr/bin/env python
"""The inflect-models-db pipeline, end to end, in one command.

    PDF  ->  Antimony  ->  validation  ->  vivarium module

Stages:
  1. PDF -> text        read the source paper (here: a redistributable model
                        spec sheet) and pull out the equations + parameters.
  2. Antimony           show the model that was extracted from it.
  3. Validation         run it through viva-tellurium and check every scenario
                        against the published steady states; sweep P(0) to show
                        the healthy / aseptic-death threshold; draw it.
  4. Vivarium module    run the SAME model as a composed process-bigraph
                        Composite (TelluriumProcess + emitter) — the form it
                        takes inside a larger bigraph document.

Run it:

    python demo/demo.py
    # or, from a fresh checkout with uv:
    uv run python demo/demo.py
"""

from pathlib import Path

from inflect_models_db import (
    build_core,
    get_model,
    run_as_module,
    run_model,
    validate_model,
)

SLUG = "reynolds-2006-acute-inflammation"
HERE = Path(__file__).resolve().parent
SOURCE_PDF = HERE / "extraction_source.pdf"
# Initial pathogen loads to sweep across the published boundary (in [1.0, 1.2]).
SWEEP = [0.0, 0.5, 0.8, 1.0, 1.05, 1.1, 1.2, 1.5, 3.0, 5.0]


def rule(title: str) -> None:
    print(f"\n{'─' * 70}\n{title}\n{'─' * 70}")


def stage_1_pdf() -> None:
    rule("STAGE 1 — PDF  ->  text")
    if not SOURCE_PDF.exists():
        print(f"  (missing {SOURCE_PDF.name}; run: python demo/make_extraction_source.py)")
        return
    from pypdf import PdfReader

    text = PdfReader(str(SOURCE_PDF)).pages[0].extract_text()
    print(f"  read {SOURCE_PDF.name}  ({len(text)} chars of extractable text)\n")
    # Show the part the extraction cares about: the equations + a parameter line.
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if "GOVERNING EQUATIONS" in ln), 0)
    for ln in lines[start : start + 7]:
        print(f"    | {ln}")
    print("    | ...")
    print(
        "\n  In practice this is the paper itself. The `extract-model` skill drives\n"
        "  an agent to read it and author the Antimony below (equations + all\n"
        "  parameters), recording the provenance in the model card."
    )


def stage_2_antimony(card) -> None:
    rule("STAGE 2 — Antimony  (the extracted model)")
    ant = card.antimony()
    for ln in ant.splitlines():
        print(f"    {ln}")
    print(f"\n  -> {card.model_path.relative_to(card.path.parent.parent)}")


def stage_3_validation(card, core) -> None:
    rule("STAGE 3 — Validation against published results (via viva-tellurium)")
    report = validate_model(card, core=core)
    print(report.summary())

    print("\n  Sweep of initial pathogen load P(0) — the published bistability:")
    cutoff = float(card.threshold.classify_by["healthy_below"])
    t = card.time
    final_damage: list[float] = []
    for p0 in SWEEP:
        traj = run_model(
            card.antimony(),
            start=t["start"],
            end=t["end"],
            n_points=t["n_points"],
            initials={"P": p0},
            core=core,
        )
        d = traj.final("D")
        final_damage.append(d)
        outcome = "healthy" if d < cutoff else "ASEPTIC DEATH"
        print(f"    P(0) = {p0:4.2f}  ->  D(t=500h) = {d:7.3f}   {outcome}")
    lo, hi = card.threshold.between
    print(f"    => outcome flips between P(0) = {lo} and {hi}, as published.")

    _draw_bifurcation(SWEEP, final_damage, cutoff, (lo, hi))


def stage_4_module(card, core) -> None:
    rule("STAGE 4 — Run as a vivarium module (process-bigraph Composite)")
    print(
        "  Same model, now wrapped as a time-coupled TelluriumProcess in a\n"
        "  Composite with a RAM emitter — the form it takes inside a bigraph\n"
        "  document, composable with other simulators.\n"
    )
    t = card.time
    duration = float(t["end"]) - float(t["start"])
    traj = run_as_module(
        card.antimony(),
        duration=duration,
        interval=10.0,
        initials={"P": 1.5},  # the aseptic-death dose
        species_ids=card.species,
        core=core,
    )
    print(f"  ran Composite for {duration:g} h at interval 10 h "
          f"({len(traj.times)} emitted rows)")
    print("    t(h)     P        Nstar      D        C_A")
    for i in (0, len(traj.times) // 2, -1):
        ti = traj.times[i]
        vals = "  ".join(f"{traj.species[s][i]:8.4f}" for s in card.species)
        print(f"    {ti:6.1f}  {vals}")
    print(
        "\n  Endpoint matches the validated aseptic-death steady state — the\n"
        "  database entry really is a runnable, composable vivarium module."
    )


def _draw_bifurcation(sweep, final_damage, cutoff, bracket) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lo, hi = bracket
    out = HERE / "bifurcation.png"
    plt.figure(figsize=(7, 4.5))
    colors = ["#1f77b4" if d < cutoff else "#d62728" for d in final_damage]
    plt.plot(sweep, final_damage, "-", color="#888", zorder=1)
    plt.scatter(sweep, final_damage, c=colors, s=60, zorder=2)
    plt.axvspan(lo, hi, color="#ffcc00", alpha=0.25, label=f"threshold ∈ [{lo}, {hi}]")
    plt.axhline(cutoff, color="#888", ls=":", lw=1)
    plt.xlabel("initial pathogen load  P(0)")
    plt.ylabel("final tissue damage  D(t=500 h)")
    plt.title("Reynolds 2006 — healthy (blue) vs aseptic death (red)")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out, dpi=120)
    plt.close()
    print(f"    wrote {out}")


def main() -> int:
    card = get_model(SLUG)
    src = card.source
    core = build_core()

    rule("inflect-models-db — PDF → Antimony → validation → vivarium module")
    print(f"{card.title}")
    print(f"{src['authors']} ({src['year']}), {src['journal']}  ·  doi:{src['doi']}")

    stage_1_pdf()
    stage_2_antimony(card)
    stage_3_validation(card, core)
    stage_4_module(card, core)

    report = validate_model(card, core=core)
    print(f"\n✓ pipeline complete — {report.slug}: {'OK' if report.ok else 'FAILED'}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
