"""Structured extraction artifact (``extraction.yaml``).

The paper, read into structured form **before** ``model.ant`` is authored: the
state variables, every ODE right-hand side, every parameter, the initial
conditions, and the published targets — each with a pointer to where in the
paper it came from. It is the auditable, diffable record of *how the model was
read out of the paper*, the stage paper2code calls an "analysis artifact".

Authoring this first (rather than going straight to Antimony) means a reviewer
can check the reading against the paper independently of the equations, and the
fidelity grade (:mod:`inflect_models_db.grade`) can reconcile it against the
Antimony that was ultimately written: every declared state has an equation and a
species, every declared parameter appears in the model, every parameter and
target is cited.

The artifact is **optional**. Models without an ``extraction.yaml`` still run,
validate, and ship exactly as before; they simply are not fidelity-graded.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import yaml

EXTRACTION_FILENAME = "extraction.yaml"


class ExtractionError(ValueError):
    """Raised when an extraction.yaml is present but malformed."""


@dataclasses.dataclass(frozen=True)
class StateVar:
    id: str
    meaning: str = ""
    units: str = ""


@dataclasses.dataclass(frozen=True)
class Equation:
    """One state variable's right-hand side, transcribed from the paper."""

    state: str
    rhs: str
    source: str = ""


@dataclasses.dataclass(frozen=True)
class Parameter:
    id: str
    value: float | None = None
    units: str = ""
    source: str = ""

    @property
    def cited(self) -> bool:
        return bool(self.source.strip())


@dataclasses.dataclass(frozen=True)
class InitialCondition:
    state: str
    value: float | None = None
    source: str = ""

    @property
    def cited(self) -> bool:
        return bool(self.source.strip())


@dataclasses.dataclass(frozen=True)
class Target:
    """A published result the card's validation asserts, cited to the paper."""

    id: str
    describes: str = ""
    source: str = ""

    @property
    def cited(self) -> bool:
        return bool(self.source.strip())


@dataclasses.dataclass(frozen=True)
class Extraction:
    slug: str
    state_variables: list[StateVar]
    equations: list[Equation]
    parameters: list[Parameter]
    initial_conditions: list[InitialCondition]
    targets: list[Target]
    source: dict[str, Any]
    notes: str
    path: Path
    raw: dict[str, Any]

    # --- accessors ---------------------------------------------------------
    @property
    def state_ids(self) -> list[str]:
        return [s.id for s in self.state_variables]

    @property
    def param_ids(self) -> list[str]:
        return [p.id for p in self.parameters]

    def equation_for(self, state: str) -> Equation | None:
        for eq in self.equations:
            if eq.state == state:
                return eq
        return None

    def ic_for(self, state: str) -> InitialCondition | None:
        for ic in self.initial_conditions:
            if ic.state == state:
                return ic
        return None


def _as_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_extraction(path: str | Path) -> Extraction:
    """Parse and lightly validate an ``extraction.yaml``."""
    path = Path(path)
    raw = yaml.safe_load(path.read_text()) or {}
    slug = raw.get("slug", path.parent.name)

    def _list(key: str) -> list[dict]:
        val = raw.get(key, []) or []
        if not isinstance(val, list):
            raise ExtractionError(f"{slug}: extraction.{key} must be a list")
        return val

    state_variables = [
        StateVar(id=_req(d, "id", slug, "state_variables"),
                 meaning=d.get("meaning", ""), units=str(d.get("units", "")))
        for d in _list("state_variables")
    ]
    equations = [
        Equation(state=_req(d, "state", slug, "equations"),
                 rhs=str(_req(d, "rhs", slug, "equations")),
                 source=str(d.get("source", "")))
        for d in _list("equations")
    ]
    parameters = [
        Parameter(id=_req(d, "id", slug, "parameters"),
                  value=_as_float(d.get("value")),
                  units=str(d.get("units", "")),
                  source=str(d.get("source", "")))
        for d in _list("parameters")
    ]
    initial_conditions = [
        InitialCondition(state=_req(d, "state", slug, "initial_conditions"),
                         value=_as_float(d.get("value")),
                         source=str(d.get("source", "")))
        for d in _list("initial_conditions")
    ]
    targets = [
        Target(id=_req(d, "id", slug, "targets"),
               describes=d.get("describes", ""),
               source=str(d.get("source", "")))
        for d in _list("targets")
    ]
    if not state_variables:
        raise ExtractionError(f"{slug}: extraction.state_variables is empty")

    return Extraction(
        slug=slug,
        state_variables=state_variables,
        equations=equations,
        parameters=parameters,
        initial_conditions=initial_conditions,
        targets=targets,
        source=raw.get("source", {}) or {},
        notes=str(raw.get("notes", "")),
        path=path.parent,
        raw=raw,
    )


def _req(d: dict, key: str, slug: str, section: str) -> Any:
    if key not in d:
        raise ExtractionError(
            f"{slug}: each extraction.{section} entry needs {key!r} (got {sorted(d)})"
        )
    return d[key]


def extraction_for(card) -> Extraction | None:
    """Load the extraction artifact next to a model card, or ``None`` if the
    model has not been given one (it remains fully usable without it)."""
    path = card.path / EXTRACTION_FILENAME
    if not path.is_file():
        return None
    return load_extraction(path)
