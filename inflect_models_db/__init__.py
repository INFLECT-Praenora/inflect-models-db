"""inflect-models-db: published dynamical models extracted to Antimony.

A curated database of mathematical models lifted from the literature into
Antimony, each one run **through viva-tellurium** and validated against the
quantitative results reported in its source paper.
"""

from inflect_models_db.card import CardError, ModelCard, Scenario, Threshold, load_card
from inflect_models_db.extraction import (
    Extraction,
    ExtractionError,
    extraction_for,
    load_extraction,
)
from inflect_models_db.grade import FidelityReport, GradeComponent, grade_model
from inflect_models_db.registry import all_cards, get_model, list_models, models_root
from inflect_models_db.run import (
    Trajectory,
    apply_initials,
    as_vivarium_document,
    build_core,
    run_as_module,
    run_model,
    run_scenario,
)
from inflect_models_db.validate import (
    Check,
    ConvergenceResult,
    ModelReport,
    OracleResult,
    ScenarioResult,
    ThresholdResult,
    check_convergence,
    check_oracle,
    check_threshold,
    reproduce_figures,
    validate_model,
    validate_scenario,
)

__version__ = "0.1.0"

__all__ = [
    "CardError",
    "ModelCard",
    "Scenario",
    "Threshold",
    "load_card",
    "Extraction",
    "ExtractionError",
    "extraction_for",
    "load_extraction",
    "FidelityReport",
    "GradeComponent",
    "grade_model",
    "all_cards",
    "get_model",
    "list_models",
    "models_root",
    "Trajectory",
    "apply_initials",
    "as_vivarium_document",
    "build_core",
    "run_as_module",
    "run_model",
    "run_scenario",
    "Check",
    "ConvergenceResult",
    "ModelReport",
    "OracleResult",
    "ScenarioResult",
    "ThresholdResult",
    "check_convergence",
    "check_oracle",
    "check_threshold",
    "reproduce_figures",
    "validate_model",
    "validate_scenario",
]
