"""Validate a model's output against the published results in its card.

Two kinds of check, both driven off ``card.yaml``:

* **scenario steady state** — run each named scenario and assert every watched
  species settles within ``tol`` of the published ``target``.
* **threshold** — sweep the control variable across the published boundary and
  assert the outcome *flips* (healthy below the bracket, non-healthy above),
  reproducing the paper's bistability.

``reproduce_figures`` renders the scenario trajectories to PNG so a reviewer can
eyeball the reproduction next to the paper's figure.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from inflect_models_db.run import Trajectory, build_core, run_model, run_scenario


@dataclasses.dataclass(frozen=True)
class Check:
    species: str
    observed: float
    target: float
    tol: float

    @property
    def ok(self) -> bool:
        return abs(self.observed - self.target) <= self.tol

    def __str__(self) -> str:
        mark = "PASS" if self.ok else "FAIL"
        return (
            f"[{mark}] {self.species}: observed={self.observed:.4g} "
            f"target={self.target:.4g} (tol {self.tol:g})"
        )


@dataclasses.dataclass(frozen=True)
class ScenarioResult:
    name: str
    checks: list[Check]

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)


@dataclasses.dataclass(frozen=True)
class ThresholdResult:
    variable: str
    lo: float
    hi: float
    lo_outcome: str
    hi_outcome: str

    @property
    def ok(self) -> bool:
        # The published result is a *flip*: healthy below the bracket,
        # non-healthy above it.
        return self.lo_outcome == "healthy" and self.hi_outcome != "healthy"

    def __str__(self) -> str:
        mark = "PASS" if self.ok else "FAIL"
        return (
            f"[{mark}] threshold in {self.variable} within [{self.lo}, {self.hi}]: "
            f"{self.lo}->{self.lo_outcome}, {self.hi}->{self.hi_outcome}"
        )


@dataclasses.dataclass(frozen=True)
class ConvergenceResult:
    """Did the scenario actually reach steady state (so endpoint targets are
    meaningful, not read mid-transient)?"""

    scenario: str
    max_rel_change: float
    threshold: float

    @property
    def ok(self) -> bool:
        return self.max_rel_change <= self.threshold

    def __str__(self) -> str:
        mark = "PASS" if self.ok else "FAIL"
        return (
            f"[{mark}] {self.scenario}: converged "
            f"(max rel. change over final window = {self.max_rel_change:.2e} "
            f"<= {self.threshold:g})"
        )


@dataclasses.dataclass(frozen=True)
class OracleResult:
    """Full-trajectory agreement with an independent reference encoding
    (e.g. the curated BioModels SBML), per species, by NRMSE."""

    scenario: str
    per_species_nrmse: dict[str, float]
    threshold: float

    @property
    def worst(self) -> float:
        return max(self.per_species_nrmse.values()) if self.per_species_nrmse else 0.0

    @property
    def ok(self) -> bool:
        return self.worst <= self.threshold

    def __str__(self) -> str:
        mark = "PASS" if self.ok else "FAIL"
        worst_sp = max(self.per_species_nrmse, key=self.per_species_nrmse.get)
        return (
            f"[{mark}] {self.scenario}: matches independent oracle "
            f"(worst NRMSE {self.worst:.2e} on {worst_sp} <= {self.threshold:g})"
        )


@dataclasses.dataclass(frozen=True)
class ModelReport:
    slug: str
    scenarios: list[ScenarioResult]
    threshold: ThresholdResult | None
    convergence: list[ConvergenceResult] = dataclasses.field(default_factory=list)
    oracle: list[OracleResult] = dataclasses.field(default_factory=list)

    @property
    def ok(self) -> bool:
        return (
            all(s.ok for s in self.scenarios)
            and (self.threshold is None or self.threshold.ok)
            and all(c.ok for c in self.convergence)
            and all(o.ok for o in self.oracle)
        )

    def summary(self) -> str:
        lines = [f"{self.slug}: {'OK' if self.ok else 'FAILED'}"]
        for s in self.scenarios:
            lines.append(f"  scenario {s.name}: {'OK' if s.ok else 'FAILED'}")
            for c in s.checks:
                lines.append(f"    {c}")
        for c in self.convergence:
            lines.append(f"  {c}")
        for o in self.oracle:
            lines.append(f"  {o}")
        if self.threshold is not None:
            lines.append(f"  {self.threshold}")
        return "\n".join(lines)


def validate_scenario(card, name: str, core=None) -> ScenarioResult:
    traj = run_scenario(card, name, core=core)
    sc = card.scenario(name)
    checks = [
        Check(
            species=sp,
            observed=traj.final(sp),
            target=spec["target"],
            tol=spec["tol"],
        )
        for sp, spec in sc.expect.items()
    ]
    return ScenarioResult(name=name, checks=checks)


def _classify(card, control_value: float, core) -> str:
    """Run the model at one control value and classify the outcome.

    Uses the card's ``threshold.classify_by`` = {variable, healthy_below}: the
    outcome is 'healthy' when the readout variable's final value is below the
    cutoff, else 'non-healthy'.
    """
    th = card.threshold
    readout = th.classify_by["variable"]
    cutoff = float(th.classify_by["healthy_below"])
    t = card.time
    traj = run_model(
        card.antimony(),
        start=t["start"],
        end=t["end"],
        n_points=t["n_points"],
        initials={th.variable: control_value},
        core=core,
    )
    return "healthy" if traj.final(readout) < cutoff else "non-healthy"


def check_threshold(card, core=None) -> ThresholdResult | None:
    if card.threshold is None:
        return None
    core = core or build_core()
    lo, hi = card.threshold.between
    return ThresholdResult(
        variable=card.threshold.variable,
        lo=lo,
        hi=hi,
        lo_outcome=_classify(card, lo, core),
        hi_outcome=_classify(card, hi, core),
    )


def check_convergence(card, name: str, core=None) -> ConvergenceResult:
    """Confirm the scenario reached steady state: the largest relative change
    of any species across the final 10% of the trajectory is below the card's
    ``steady_state.rel_change_below`` (default 1e-3). Guards against reading a
    target mid-transient (e.g. too short a time span)."""
    ss = card.steady_state or {}
    thr = float(ss.get("rel_change_below", 1e-3))
    traj = run_scenario(card, name, core=core)
    n = len(traj.times)
    window = max(2, n // 10)
    watched = card.species or list(traj.species)
    worst = 0.0
    for sp in watched:
        series = traj.series(sp)
        tail = series[-window:]
        scale = max(abs(v) for v in series) or 1.0
        rel = (max(tail) - min(tail)) / scale
        worst = max(worst, rel)
    return ConvergenceResult(scenario=name, max_rel_change=worst, threshold=thr)


def check_oracle(card, name: str, core=None) -> OracleResult | None:
    """Compare the extracted model's full trajectory against an independent
    reference encoding, per species, by NRMSE.

    The oracle is run through a *different* path from the model under test — the
    curated SBML is simulated directly by tellurium/libroadrunner, not through
    the repo's Antimony — so agreement is real corroboration, not a tautology.
    Returns None when the card declares no oracle.
    """
    if not card.oracle:
        return None
    import numpy as np
    import tellurium as te

    spec = card.oracle
    if spec.get("kind", "sbml") != "sbml":
        raise ValueError(f"{card.slug}: unsupported oracle kind {spec.get('kind')!r}")
    thr = float(spec.get("nrmse_below", 1e-2))

    ours = run_scenario(card, name, core=core)
    sc = card.scenario(name)
    t = card.time
    sbml = (card.path / spec["file"]).read_text()

    rr = te.loadSBMLModel(sbml)
    rr.reset()
    for k, v in sc.initials.items():
        rr[f"init({k})"] = float(v)
    selections = ["time"] + [f"[{s}]" for s in card.species]
    res = rr.simulate(t["start"], t["end"], t["n_points"], selections)

    per_species: dict[str, float] = {}
    for i, sp in enumerate(card.species):
        ref = np.asarray(res[:, i + 1], dtype=float)
        got = np.asarray(ours.series(sp), dtype=float)
        rng = float(ref.max() - ref.min())
        denom = rng if rng > 1e-9 else max(float(np.abs(ref).max()), 1e-9)
        per_species[sp] = float(np.sqrt(np.mean((got - ref) ** 2)) / denom)
    return OracleResult(scenario=name, per_species_nrmse=per_species, threshold=thr)


def validate_model(card, core=None) -> ModelReport:
    core = core or build_core()
    scenarios = [validate_scenario(card, n, core=core) for n in card.scenario_names]
    threshold = check_threshold(card, core=core)
    convergence = [check_convergence(card, n, core=core) for n in card.scenario_names]
    oracle = [
        o
        for n in card.scenario_names
        if (o := check_oracle(card, n, core=core)) is not None
    ]
    return ModelReport(
        slug=card.slug,
        scenarios=scenarios,
        threshold=threshold,
        convergence=convergence,
        oracle=oracle,
    )


def reproduce_figures(card, outdir: str | Path | None = None, core=None) -> list[Path]:
    """Render each scenario's trajectory to a PNG under the model's figures/.

    One figure per card entry of kind 'outcome-scenarios': a grid with one panel
    per species, one line per scenario. Returns the paths written.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    core = core or build_core()
    outdir = Path(outdir) if outdir else (card.path / "figures")
    outdir.mkdir(parents=True, exist_ok=True)

    trajs: dict[str, Trajectory] = {
        sc.name: run_scenario(card, sc.name, core=core) for sc in card.scenarios
    }

    written: list[Path] = []
    for fig_spec in card.figures or [{"name": "outcomes", "kind": "outcome-scenarios"}]:
        species = card.species or sorted(next(iter(trajs.values())).species)
        n = len(species)
        ncols = 2
        nrows = (n + ncols - 1) // ncols
        fig, axes = plt.subplots(nrows, ncols, figsize=(9, 3 * nrows), squeeze=False)
        for idx, sp in enumerate(species):
            ax = axes[idx // ncols][idx % ncols]
            for name, traj in trajs.items():
                ax.plot(traj.times, traj.series(sp), label=name, lw=2)
            ax.set_title(sp)
            ax.set_xlabel(f"time ({card.time.get('units', 'a.u.')})")
            ax.grid(alpha=0.3)
            if idx == 0:
                ax.legend(fontsize=8)
        for j in range(n, nrows * ncols):
            axes[j // ncols][j % ncols].axis("off")
        fig.suptitle(f"{card.slug} — {fig_spec.get('name', 'figure')}", fontsize=12)
        fig.tight_layout()
        out = outdir / fig_spec.get("file", f"{fig_spec.get('name', 'figure')}.png").replace(
            "figures/", ""
        )
        fig.savefig(out, dpi=120)
        plt.close(fig)
        written.append(out)
    return written
