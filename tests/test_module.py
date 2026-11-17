"""Running a model as a composed process-bigraph module agrees with the
published results — the same model, exercised through the vivarium path."""

from inflect_models_db.run import run_as_module


def test_run_as_module_matches_published(card, core):
    """For every scenario, the time-coupled Composite run lands on the card's
    published steady-state targets (looser tol: coupling interval + emitter)."""
    t = card.time
    duration = float(t["end"]) - float(t["start"])
    for sc in card.scenarios:
        traj = run_as_module(
            card.antimony(),
            duration=duration,
            interval=max(1.0, duration / 100.0),
            initials=sc.initials,
            species_ids=card.species or None,
            core=core,
        )
        for sp, spec in sc.expect.items():
            observed = traj.final(sp)
            tol = max(spec["tol"], 0.02 * abs(spec["target"]))
            assert abs(observed - spec["target"]) <= tol, (
                f"{card.slug}/{sc.name} module run: {sp}={observed:.4g} "
                f"vs published {spec['target']} (tol {tol:g})"
            )
