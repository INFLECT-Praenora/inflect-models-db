"""The bigraph bridge: every curated model registers as a process-bigraph
composite generator and runs as a composite, reproducing the card's targets.

This is the contract that lets a model drop into the simulation-core (or any
process-bigraph document) as a registered composite — not just a script.
"""

from process_bigraph.composite_spec import all_specs, clear_registry
from process_bigraph.composite_spec import get as get_spec

from inflect_models_db import bigraph as B
from inflect_models_db.run import run_as_module


def test_generator_name_is_valid_identifier(card):
    name = B.generator_name(card.slug)
    assert name.startswith(B.GENERATOR_PREFIX)
    assert name.isidentifier()


def test_card_observables_nonempty(card):
    obs = B.card_observables(card)
    assert obs, f"{card.slug}: no observables derivable from card"
    # species-declared cards expose exactly those
    if card.species:
        assert obs == list(card.species)


def test_interval_and_duration_from_time_block(card):
    assert B.card_duration(card) > 0
    assert B.card_interval(card) > 0


def test_register_all_registers_every_model():
    clear_registry()
    names = B.register_all()
    assert names, "no models registered"
    ids = set(all_specs())
    for n in names:
        # spec id is the dotted module path + generator name
        assert any(sid.endswith("." + n) for sid in ids), f"{n} not in registry"


def test_card_to_generator_builds_runnable_composite(card):
    """The registered composite builds a document for each scenario and, run as a
    composite, reproduces the card's published steady-state targets."""
    clear_registry()
    B.card_to_generator(card)
    sid = next(s for s in all_specs() if s.endswith("." + B.generator_name(card.slug)))
    spec = get_spec(sid)
    assert spec is not None

    for sc in card.scenarios:
        # the document builds through the registered spec (dashboard path)
        doc = spec.to_document({"scenario": sc.name}, core=None)
        assert doc.get("state", doc), f"{card.slug}/{sc.name}: empty document"

        # and running it reproduces the card's targets (engine path)
        req = B.scenario_request(card, sc.name)
        traj = run_as_module(
            req["antimony"],
            duration=req["duration"],
            interval=max(1.0, req["duration"] / 100.0),
            initials=req["initials"],
            species_ids=req["observables"],
        )
        for sp, exp in sc.expect.items():
            observed = traj.final(sp)
            tol = max(exp["tol"], 0.02 * abs(exp["target"]))
            assert abs(observed - exp["target"]) <= tol, (
                f"{card.slug}/{sc.name}: {sp}={observed:.4g} vs "
                f"published {exp['target']} (tol {tol:g})"
            )


def test_scenario_request_defaults_to_first_scenario(card):
    req = B.scenario_request(card)
    assert req["scenario"] == card.scenario_names[0]
    assert req["observables"] == B.card_observables(card)
    assert set(req) >= {
        "slug", "scenario", "antimony", "initials",
        "observables", "duration", "interval", "start",
    }
