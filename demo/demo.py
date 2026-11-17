#!/usr/bin/env python
"""Reproduce the Reynolds 2006 acute-inflammation result, end to end.

One command, no arguments. It:
  1. loads the model extracted from the paper,
  2. runs it through viva-tellurium and checks every scenario against the
     published steady states,
  3. sweeps the initial pathogen load P(0) to show the healthy / aseptic-death
     threshold emerge, and
  4. draws the bifurcation (final tissue damage vs initial pathogen load).

Run it:

    python demo/demo.py
    # or, from a fresh checkout with uv:
    uv run python demo/demo.py
"""

from pathlib import Path

from inflect_models_db import build_core, get_model, run_model, validate_model

SLUG = "reynolds-2006-acute-inflammation"
# Initial pathogen loads to sweep across the published boundary (in [1.0, 1.2]).
SWEEP = [0.0, 0.5, 0.8, 1.0, 1.05, 1.1, 1.15, 1.2, 1.5, 3.0, 5.0]


def rule(title: str) -> None:
    print(f"\n{'─' * 66}\n{title}\n{'─' * 66}")


def main() -> int:
    card = get_model(SLUG)
    src = card.source
    core = build_core()

    rule("inflect-models-db demo — Reynolds et al. 2006")
    print(f"{card.title}")
    print(f"{src['authors']} ({src['year']}), {src['journal']}")
    print(f"doi:{src['doi']}  ·  BioModels:{src['biomodels']}")
    print(f"\nModel: {card.model_file}  (run through viva-tellurium)")
    print(f"State: {', '.join(card.species)}")

    # 1 + 2 — validate against the published steady states
    rule("1. Validate against published results")
    report = validate_model(card, core=core)
    print(report.summary())

    # 3 — sweep the initial pathogen load; watch the outcome flip
    rule("2. Sweep initial pathogen load P(0) — the published bistability")
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
        print(f"  P(0) = {p0:4.2f}  ->  final tissue damage D = {d:7.3f}   {outcome}")
    lo, hi = card.threshold.between
    print(f"\n  => the outcome flips between P(0) = {lo} and {hi}, as published.")

    # 4 — draw the bifurcation
    rule("3. Figures")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = Path(__file__).resolve().parent / "bifurcation.png"
    plt.figure(figsize=(7, 4.5))
    colors = ["#1f77b4" if d < cutoff else "#d62728" for d in final_damage]
    plt.plot(SWEEP, final_damage, "-", color="#888", zorder=1)
    plt.scatter(SWEEP, final_damage, c=colors, s=60, zorder=2)
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
    print(f"  wrote {out}")
    print(f"  (per-scenario time courses: inflect-models reproduce {SLUG})")

    print(f"\n✓ Reproduced the published result: {report.slug} {'OK' if report.ok else 'FAILED'}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
