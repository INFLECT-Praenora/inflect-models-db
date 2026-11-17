"""Model-card schema + loader.

A *model card* (``card.yaml``) is the contract for one curated model: where the
Antimony lives, what published work it was extracted from, and the quantitative
targets its output must reproduce. Everything downstream (running, validating,
reproducing figures, tests) is driven off the card, so adding a model is purely
a matter of dropping a ``model.ant`` + ``card.yaml`` into ``models/<slug>/``.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import yaml


class CardError(ValueError):
    """Raised when a card.yaml is missing required structure."""


@dataclasses.dataclass(frozen=True)
class Scenario:
    """One initial-condition scenario and its expected steady-state targets.

    ``initials`` maps species id -> initial value (overrides the model's own
    initial conditions). ``expect`` maps species id -> {'target', 'tol'}: the
    published steady-state value and the tolerance the run must fall within.
    """

    name: str
    initials: dict[str, float]
    expect: dict[str, dict[str, float]]
    description: str = ""


@dataclasses.dataclass(frozen=True)
class Threshold:
    """A published bifurcation/threshold the sweep must reproduce.

    ``variable`` is the control parameter swept (e.g. initial pathogen ``P``);
    ``between`` = [lo, hi] brackets the boundary; ``classify_by`` names the
    readout variable and the value below which the outcome is 'healthy'.
    """

    variable: str
    between: list[float]
    classify_by: dict[str, Any]


@dataclasses.dataclass(frozen=True)
class ModelCard:
    slug: str
    title: str
    source: dict[str, Any]
    model_file: str
    model_format: str
    species: list[str]
    time: dict[str, Any]
    scenarios: list[Scenario]
    threshold: Threshold | None
    figures: list[dict[str, Any]]
    path: Path  # the models/<slug>/ directory
    raw: dict[str, Any]

    # --- convenience accessors ---------------------------------------------
    @property
    def model_path(self) -> Path:
        return self.path / self.model_file

    def antimony(self) -> str:
        if self.model_format != "antimony":
            raise CardError(
                f"{self.slug}: only 'antimony' model_format is supported for "
                f"direct text load (got {self.model_format!r})"
            )
        return self.model_path.read_text()

    def scenario(self, name: str) -> Scenario:
        for sc in self.scenarios:
            if sc.name == name:
                return sc
        raise KeyError(f"{self.slug}: no scenario named {name!r}")

    @property
    def scenario_names(self) -> list[str]:
        return [sc.name for sc in self.scenarios]


def _require(d: dict, key: str, slug: str) -> Any:
    if key not in d:
        raise CardError(f"{slug}: card.yaml missing required key {key!r}")
    return d[key]


def load_card(card_yaml: str | Path) -> ModelCard:
    """Parse and lightly validate a ``card.yaml`` into a :class:`ModelCard`."""
    card_yaml = Path(card_yaml)
    raw = yaml.safe_load(card_yaml.read_text()) or {}
    slug = raw.get("slug", card_yaml.parent.name)

    model = _require(raw, "model", slug)
    model_file = _require(model, "file", slug)
    model_format = model.get("format", "antimony")
    species = list(model.get("species", []))

    time = _require(raw, "validation", slug).get("time", {})
    for k in ("start", "end", "n_points"):
        if k not in time:
            raise CardError(f"{slug}: validation.time missing {k!r}")

    scenarios: list[Scenario] = []
    for sc in raw["validation"].get("scenarios", []):
        if "name" not in sc or "initials" not in sc or "expect" not in sc:
            raise CardError(
                f"{slug}: each scenario needs name/initials/expect (got "
                f"{sorted(sc)})"
            )
        scenarios.append(
            Scenario(
                name=sc["name"],
                initials={k: float(v) for k, v in sc["initials"].items()},
                expect={
                    s: {"target": float(e["target"]), "tol": float(e["tol"])}
                    for s, e in sc["expect"].items()
                },
                description=sc.get("description", ""),
            )
        )
    if not scenarios:
        raise CardError(f"{slug}: validation.scenarios is empty")

    th_raw = raw["validation"].get("threshold")
    threshold = (
        Threshold(
            variable=th_raw["variable"],
            between=[float(x) for x in th_raw["between"]],
            classify_by=th_raw["classify_by"],
        )
        if th_raw
        else None
    )

    model_path = card_yaml.parent / model_file
    if not model_path.exists():
        raise CardError(f"{slug}: model file not found: {model_path}")

    return ModelCard(
        slug=slug,
        title=raw.get("title", slug),
        source=raw.get("source", {}),
        model_file=model_file,
        model_format=model_format,
        species=species,
        time=time,
        scenarios=scenarios,
        threshold=threshold,
        figures=list(raw.get("figures", [])),
        path=card_yaml.parent,
        raw=raw,
    )
