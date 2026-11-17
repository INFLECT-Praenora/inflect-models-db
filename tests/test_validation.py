"""Every model reproduces the published results declared in its card.

These are the regression tests that make the database trustworthy: each scenario
must settle within tolerance of the published steady state, and each declared
threshold must flip the outcome across the published bracket.
"""

from inflect_models_db.validate import (
    check_convergence,
    check_oracle,
    check_threshold,
    validate_scenario,
)


def test_scenarios_match_published_steady_states(card, core):
    for name in card.scenario_names:
        result = validate_scenario(card, name, core=core)
        failures = [str(c) for c in result.checks if not c.ok]
        assert result.ok, (
            f"{card.slug}/{name} did not match published results:\n  "
            + "\n  ".join(failures)
        )


def test_threshold_reproduces_published_bifurcation(card, core):
    result = check_threshold(card, core=core)
    if result is None:
        return  # model declares no threshold
    assert result.ok, f"{card.slug}: {result}"


def test_scenarios_reach_steady_state(card, core):
    """Endpoint targets are only meaningful if the run actually converged."""
    for name in card.scenario_names:
        result = check_convergence(card, name, core=core)
        assert result.ok, f"{card.slug}: {result}"


def test_matches_independent_oracle(card, core):
    """When the card declares an oracle, the extracted model's full trajectory
    must agree with that independent encoding."""
    for name in card.scenario_names:
        result = check_oracle(card, name, core=core)
        if result is None:
            return  # no oracle declared for this model
        assert result.ok, f"{card.slug}: {result} (per-species {result.per_species_nrmse})"
