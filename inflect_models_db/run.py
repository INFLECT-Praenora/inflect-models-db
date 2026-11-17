"""Run an extracted model **through viva-tellurium**.

Every model in this database is executed by wrapping its Antimony as a
``viva_tellurium.TelluriumUTCStep`` (a one-shot uniform-time-course Step over
libroadrunner/CVODE) and firing it once. Running through viva-tellurium — rather
than calling tellurium directly — is deliberate: it is the same process-bigraph
bridge the rest of the ecosystem composes with, so a model validated here is a
model that drops straight into a bigraph document.

Initial-condition overrides (the dosing scenarios) are applied by rewriting the
species-initialisation lines in the Antimony text, so the Step still resets to
the intended state on each firing.
"""

from __future__ import annotations

import dataclasses
import re

from process_bigraph import allocate_core

from viva_tellurium import TelluriumUTCStep, register_tellurium_types


@dataclasses.dataclass(frozen=True)
class Trajectory:
    """Dense trajectory returned by a run."""

    times: list[float]
    species: dict[str, list[float]]

    def final(self, name: str) -> float:
        return self.species[name][-1]

    def series(self, name: str) -> list[float]:
        return self.species[name]

    @property
    def species_ids(self) -> list[str]:
        return list(self.species)


def build_core():
    """A fresh process-bigraph core with viva-tellurium's types registered."""
    core = allocate_core()
    register_tellurium_types(core)
    return core


def apply_initials(antimony: str, overrides: dict[str, float]) -> str:
    """Rewrite ``<species> = <value>`` initialisation lines in the Antimony.

    Matches a species id at a word boundary followed by ``=`` and a numeric
    literal, replacing only the first such assignment per species (the
    initialisation). Rate rules (``P'`` = ...) are left untouched because the
    apostrophe breaks the ``\\b<id>\\s*=`` match.
    """
    out = antimony
    for sp, val in overrides.items():
        pattern = rf"(?m)(\b{re.escape(sp)}\s*=\s*)[-+0-9.eE]+"
        new, n = re.subn(pattern, rf"\g<1>{val}", out, count=1)
        if n == 0:
            raise ValueError(
                f"apply_initials: no initialisation for {sp!r} found to override"
            )
        out = new
    return out


def run_model(
    antimony: str,
    *,
    start: float,
    end: float,
    n_points: int,
    initials: dict[str, float] | None = None,
    core=None,
) -> Trajectory:
    """Run an Antimony model over [start, end] and return the trajectory."""
    model = apply_initials(antimony, initials or {})
    core = core or build_core()
    step = TelluriumUTCStep(
        config={
            "model": model,
            "model_format": "antimony",
            "start_time": float(start),
            "end_time": float(end),
            "n_points": int(n_points),
        },
        core=core,
    )
    result = step.update({})
    return Trajectory(
        times=list(result["time_series"]),
        species={k: list(v) for k, v in result["species_trajectories"].items()},
    )


def run_scenario(card, scenario_name: str, core=None) -> Trajectory:
    """Run one of a card's named scenarios."""
    sc = card.scenario(scenario_name)
    t = card.time
    return run_model(
        card.antimony(),
        start=t["start"],
        end=t["end"],
        n_points=t["n_points"],
        initials=sc.initials,
        core=core or build_core(),
    )


# --- running the model as a composable vivarium (process-bigraph) module -----
#
# The functions above drive a one-shot UTC Step. The ones below instead wrap the
# model as a *time-coupled* ``TelluriumProcess`` inside a process-bigraph
# ``Composite`` with a RAM emitter — i.e. exactly the form a model takes when it
# is dropped into a larger bigraph document and composed with other simulators.


def as_vivarium_document(
    antimony: str,
    *,
    interval: float = 1.0,
    initials: dict[str, float] | None = None,
) -> dict:
    """Build a process-bigraph composite document for the model.

    Returns a document dict (TelluriumProcess + stores + RAM emitter) ready for
    ``process_bigraph.Composite({'state': doc}, core=...)``. Initial-condition
    overrides are passed as native ``species_overrides`` rather than text edits.
    """
    from viva_tellurium import make_tellurium_document

    return make_tellurium_document(
        model=antimony,
        model_format="antimony",
        interval=interval,
        species_overrides={k: float(v) for k, v in (initials or {}).items()},
    )


def _floating_species_ids(antimony: str) -> list[str]:
    import tellurium as te

    return list(te.loadAntimonyModel(antimony).getFloatingSpeciesIds())


def run_as_module(
    antimony: str,
    *,
    duration: float,
    interval: float = 1.0,
    initials: dict[str, float] | None = None,
    species_ids: list[str] | None = None,
    core=None,
) -> Trajectory:
    """Run the model as a composed process-bigraph module; return a Trajectory.

    Wraps the Antimony as a time-driven ``TelluriumProcess``, composes it with a
    RAM emitter, runs the ``Composite`` for ``duration``, and reshapes the
    emitted rows into a :class:`Trajectory`. This is the path that proves a model
    in this database is a real, composable vivarium module — not just a script.
    """
    from process_bigraph import Composite, gather_emitter_results
    from process_bigraph.emitter import RAMEmitter

    from viva_tellurium import TelluriumProcess

    core = core or build_core()
    core.register_link("TelluriumProcess", TelluriumProcess)
    core.register_link("ram-emitter", RAMEmitter)

    doc = as_vivarium_document(antimony, interval=interval, initials=initials)
    sim = Composite({"state": doc}, core=core)
    sim.run(float(duration))

    rows = gather_emitter_results(sim)[("emitter",)]
    ids = species_ids or _floating_species_ids(antimony)
    times = [float(r["time"]) for r in rows]
    # The species port is a bulk numpy array ordered by the model's floating
    # species ids (viva-tellurium's default bulk_species=True).
    species = {
        sid: [float(r["species"][i]) for r in rows] for i, sid in enumerate(ids)
    }
    return Trajectory(times=times, species=species)
