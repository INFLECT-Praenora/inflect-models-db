"""The structured extraction artifact loads and reconciles with the model.

Two layers:

* an integration test parametrized over every curated model — any model that
  ships an ``extraction.yaml`` must pass the (deterministic) fidelity grade;
* pure unit tests of the grading logic with synthetic inputs (no tellurium),
  so the reconciliation rules are pinned independently of any real model.
"""

import pytest

from inflect_models_db.extraction import (
    Equation,
    Extraction,
    InitialCondition,
    Parameter,
    StateVar,
    Target,
    extraction_for,
)
from inflect_models_db.grade import grade_components, grade_model

# --- integration: real models -------------------------------------------------


def test_extraction_fidelity_grade(card):
    """Every model with an extraction.yaml passes the gating fidelity grade."""
    report = grade_model(card)
    if report is None:
        pytest.skip(f"{card.slug}: no extraction.yaml")
    assert report.ok, "\n" + report.summary()


def test_extraction_matches_card_species(card):
    """The extraction's declared state ids match the card's watched species."""
    ex = extraction_for(card)
    if ex is None:
        pytest.skip(f"{card.slug}: no extraction.yaml")
    assert set(ex.state_ids) == set(card.species), (
        f"{card.slug}: extraction states {ex.state_ids} != card species {card.species}"
    )


# --- unit: synthetic extraction, no tellurium ---------------------------------


def _ex(**over) -> Extraction:
    """A minimal, fully-faithful extraction for a 1-state, 1-param toy model."""
    base = {
        "slug": "toy",
        "state_variables": [StateVar("X", "thing", "au")],
        "equations": [Equation("X", "k*X", "Eq. 1")],
        "parameters": [Parameter("k", 0.5, "1/s", "Table 1")],
        "initial_conditions": [InitialCondition("X", 1.0, "baseline")],
        "targets": [Target("ss", "steady state", "Fig. 1")],
        "source": {},
        "notes": "",
        "path": None,
        "raw": {},
    }
    base.update(over)
    return Extraction(**base)


def test_grade_all_green():
    comps = grade_components(_ex(), species_ids=["X"], param_ids=["k"])
    assert all(c.ok for c in comps), [str(c) for c in comps]


def test_grade_uncited_parameter_fails():
    ex = _ex(parameters=[Parameter("k", 0.5, "1/s", "")])  # no source
    comps = {c.name: c for c in grade_components(ex, ["X"], ["k"])}
    assert not comps["param-citation"].ok
    assert comps["param-coverage"].ok  # coverage still fine


def test_grade_param_in_model_not_extracted_fails_coverage():
    comps = {c.name: c for c in grade_components(_ex(), ["X"], ["k", "k2"])}
    assert not comps["param-coverage"].ok
    assert "k2" in comps["param-coverage"].detail


def test_grade_undeclared_species_fails_coverage():
    comps = {c.name: c for c in grade_components(_ex(), ["X", "Y"], ["k"])}
    assert not comps["state-coverage"].ok
    assert "Y" in comps["state-coverage"].detail


def test_grade_missing_equation_fails_coverage():
    ex = _ex(equations=[])  # X has no transcribed equation
    comps = {c.name: c for c in grade_components(ex, ["X"], ["k"])}
    assert not comps["state-coverage"].ok


def test_grade_no_targets_fails():
    ex = _ex(targets=[])
    comps = {c.name: c for c in grade_components(ex, ["X"], ["k"])}
    assert not comps["target-citation"].ok


def test_grade_uncited_initial_fails():
    ex = _ex(initial_conditions=[InitialCondition("X", 1.0, "")])
    comps = {c.name: c for c in grade_components(ex, ["X"], ["k"])}
    assert not comps["initials-citation"].ok
