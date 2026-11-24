"""Expose each curated model as a process-bigraph **composite**.

This is the bridge that lets any model in this database run inside the
simulation-core — or any process-bigraph document — as a *registered composite*,
not just a validation script. It makes good on the database's own promise: "a
model validated here drops straight into a bigraph document as a Process."

A model card already carries everything a run needs: the Antimony, named
scenarios (initial-condition overrides), the observable species, and the time
window. :func:`card_to_generator` turns that into a ``@composite_generator``
whose one scientific knob is *which scenario* to run; :func:`register_all`
registers the whole database so a host (e.g. simulation-core's ``build_core``)
picks up every curated model.

Importing this module does **not** require a simulation engine — registration is
cheap and lazy. *Building* a composite (``to_document`` / running it) needs
``viva-tellurium``, imported only then (via :func:`inflect_models_db.run`).
"""

from __future__ import annotations

from typing import Any, Callable

from process_bigraph.composite_generator import composite_generator

from inflect_models_db.card import ModelCard
from inflect_models_db.registry import all_cards

GENERATOR_PREFIX = "modelsdb_"


def generator_name(slug: str) -> str:
    """The composite-generator name for a model slug (a valid identifier)."""
    return GENERATOR_PREFIX + slug.replace("-", "_")


def card_observables(card: ModelCard) -> list[str]:
    """The model's observable ids: the card's declared ``model.species`` if
    present, else the union of every scenario's ``expect`` targets."""
    if card.species:
        return list(card.species)
    seen: list[str] = []
    for sc in card.scenarios:
        for s in sc.expect:
            if s not in seen:
                seen.append(s)
    return seen


def card_interval(card: ModelCard) -> float:
    """The per-update time step implied by the card's ``validation.time`` block
    (``(end - start) / (n_points - 1)``)."""
    t = card.time
    n = int(t["n_points"])
    span = float(t["end"]) - float(t["start"])
    return span / max(1, n - 1)


def card_duration(card: ModelCard) -> float:
    t = card.time
    return float(t["end"]) - float(t["start"])


def scenario_request(card: ModelCard, scenario: str | None = None) -> dict[str, Any]:
    """A plain, engine-agnostic run spec for one scenario — the handoff a host
    contract (e.g. simulation-core's ``simulate``) can consume **without**
    importing process-bigraph.

    Returns ``{slug, scenario, antimony, initials, observables, duration,
    interval, start}``. ``scenario`` defaults to the card's first scenario.
    """
    name = scenario or card.scenario_names[0]
    sc = card.scenario(name)
    return {
        "slug": card.slug,
        "scenario": name,
        "antimony": card.antimony(),
        "initials": dict(sc.initials),
        "observables": card_observables(card),
        "duration": card_duration(card),
        "interval": card_interval(card),
        "start": float(card.time["start"]),
    }


def card_to_generator(card: ModelCard) -> Callable[..., dict]:
    """Build **and register** a ``@composite_generator`` for one model card.

    The generated composite is a viva-tellurium document for the model with the
    chosen scenario's initial conditions applied. ``scenario`` selects one of the
    card's named scenarios (default: the first); ``interval`` overrides the
    per-update step (default derived from the card's time block).
    """
    scenarios = {sc.name: sc for sc in card.scenarios}
    default_scenario = card.scenario_names[0]
    interval_default = card_interval(card)
    n_steps = max(1, int(round(card_duration(card) / interval_default)))
    observables = card_observables(card)

    @composite_generator(
        name=generator_name(card.slug),
        description=(
            f"{card.title} — {card.source.get('authors', '')} "
            f"{card.source.get('year', '')}. Curated Antimony from inflect-models-db, "
            f"run via viva-tellurium (exact SBML/CVODE). "
            f"Observables: {', '.join(observables)}. "
            f"Scenarios: {', '.join(card.scenario_names)}."
        ).strip(),
        parameters={
            "scenario": {
                "type": "string",
                "default": default_scenario,
                "description": "Named scenario (initial conditions): "
                + ", ".join(card.scenario_names),
            },
            "interval": {
                "type": "float",
                "default": interval_default,
                "description": "Time units per update",
            },
        },
        default_n_steps=n_steps,
        fidelity="reproduction",
    )
    def _make(core=None, *, scenario: str = default_scenario,
              interval: float = interval_default) -> dict:
        # Lazy: building a composite needs the engine; importing this module does not.
        from inflect_models_db.run import as_vivarium_document
        sc = scenarios.get(scenario)
        if sc is None:
            raise KeyError(
                f"{card.slug}: no scenario {scenario!r} "
                f"(have: {', '.join(scenarios)})"
            )
        return as_vivarium_document(
            card.antimony(), interval=float(interval), initials=sc.initials
        )

    return _make


def register_all(cards: list[ModelCard] | None = None) -> list[str]:
    """Register every curated model as a composite generator.

    Returns the generator names registered. A malformed card is skipped so it
    never blocks the rest. Registration keys on the generator name, so calling
    this more than once is harmless (re-registers the same ids).
    """
    names: list[str] = []
    for card in (cards if cards is not None else all_cards()):
        try:
            card_to_generator(card)
            names.append(generator_name(card.slug))
        except Exception:  # noqa: BLE001 — one bad card never breaks the batch
            continue
    return names
