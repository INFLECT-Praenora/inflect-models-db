"""Extraction-fidelity grade: *did the Antimony faithfully encode the paper?*

The numeric validation (:mod:`inflect_models_db.validate`) answers a different
question — does the model reproduce the published *numbers*. A model can pass
that while encoding the wrong mechanism (a compensating pair of errors, a
parameter transcribed wrong but masked by the fit). The fidelity grade is the
structural complement: it reconciles the structured reading
(``extraction.yaml``) against the Antimony that was actually written and the
card that drives validation.

The grade is **deterministic** and CI-gating for any model that ships an
``extraction.yaml``:

* **state coverage** — every declared state variable is a species in the model
  and has a transcribed equation; the model has no undeclared species.
* **parameter coverage** — the model's parameters and the declared parameters
  are the same set (auxiliary ``:=`` assignment rules excluded).
* **parameter citation** — every declared parameter cites where in the paper its
  value came from.
* **initial-condition citation** — every state has a cited initial condition.
* **target citation** — every declared validation target cites the paper.

An optional, **non-gating** LLM-reviewer pass (paper2code's ``eval.py`` idea)
can add a 1–5 faithfulness score; it is wired through the ``INFLECT_LLM_REVIEW_CMD``
environment variable and is skipped — never failed — when unconfigured.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import subprocess
from statistics import mean

from inflect_models_db.extraction import Extraction, extraction_for

# ----------------------------------------------------------------------------
# Antimony symbol table
# ----------------------------------------------------------------------------

_ASSIGN_RULE = re.compile(r"(?m)^\s*(\w+)\s*:=")


def assignment_rule_ids(antimony: str) -> set[str]:
    """Ids defined by an Antimony assignment rule (``name := expr``).

    libroadrunner reports these alongside true parameters in
    ``getGlobalParameterIds``; they are derived quantities, not published
    parameters, so the grade excludes them from parameter reconciliation.
    """
    return set(_ASSIGN_RULE.findall(antimony))


def antimony_symbols(antimony: str) -> tuple[list[str], list[str]]:
    """Return ``(floating_species_ids, parameter_ids)`` for an Antimony model,
    as the model actually compiles — parameters exclude ``:=`` aux variables."""
    import tellurium as te

    model = te.loadAntimonyModel(antimony)
    species = list(model.getFloatingSpeciesIds())
    aux = assignment_rule_ids(antimony)
    params = [p for p in model.getGlobalParameterIds() if p not in aux]
    return species, params


# ----------------------------------------------------------------------------
# Grade data types
# ----------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class GradeComponent:
    name: str
    score: float  # 0..1
    ok: bool
    gating: bool
    detail: str

    def __str__(self) -> str:
        mark = "PASS" if self.ok else ("WARN" if not self.gating else "FAIL")
        gate = "" if self.gating else " (non-gating)"
        return f"[{mark}] {self.name}: {self.score:.0%}{gate} — {self.detail}"


@dataclasses.dataclass(frozen=True)
class LLMReview:
    configured: bool
    score: float | None = None  # 1..5
    notes: str = ""

    def __str__(self) -> str:
        if not self.configured:
            return "[SKIP] llm-review: not configured (set INFLECT_LLM_REVIEW_CMD)"
        s = f"{self.score:.2f}/5" if self.score is not None else "n/a"
        return f"[INFO] llm-review (non-gating): {s} — {self.notes}"


@dataclasses.dataclass(frozen=True)
class FidelityReport:
    slug: str
    components: list[GradeComponent]
    llm: LLMReview | None = None

    @property
    def ok(self) -> bool:
        """Only *gating* components decide pass/fail."""
        return all(c.ok for c in self.components if c.gating)

    @property
    def score(self) -> float:
        return mean(c.score for c in self.components) if self.components else 0.0

    def summary(self) -> str:
        head = f"{self.slug}: fidelity {'OK' if self.ok else 'FAILED'} " \
               f"(score {self.score:.0%})"
        lines = [head] + [f"  {c}" for c in self.components]
        if self.llm is not None:
            lines.append(f"  {self.llm}")
        return "\n".join(lines)


# ----------------------------------------------------------------------------
# Deterministic grading (pure — testable without tellurium)
# ----------------------------------------------------------------------------


def _frac(num: int, den: int) -> float:
    return 1.0 if den == 0 else num / den


def _state_coverage(ex: Extraction, species_ids: list[str]) -> GradeComponent:
    declared = set(ex.state_ids)
    model = set(species_ids)
    with_eq = {s for s in declared if ex.equation_for(s) is not None}
    good = {s for s in declared if s in model and s in with_eq}
    universe = declared | model
    missing_in_model = sorted(declared - model)
    undeclared = sorted(model - declared)
    missing_eq = sorted(declared - with_eq)
    score = _frac(len(good), len(universe))
    problems = []
    if missing_in_model:
        problems.append(f"declared but not a species: {missing_in_model}")
    if undeclared:
        problems.append(f"species not declared: {undeclared}")
    if missing_eq:
        problems.append(f"no equation: {missing_eq}")
    detail = "; ".join(problems) if problems else (
        f"all {len(declared)} states have a species + equation"
    )
    return GradeComponent("state-coverage", score, not problems, True, detail)


def _parameter_coverage(ex: Extraction, param_ids: list[str]) -> GradeComponent:
    declared = set(ex.param_ids)
    model = set(param_ids)
    inter = declared & model
    universe = declared | model
    score = _frac(len(inter), len(universe))
    missing_in_extraction = sorted(model - declared)
    missing_in_model = sorted(declared - model)
    problems = []
    if missing_in_extraction:
        problems.append(f"in model, not extracted: {missing_in_extraction}")
    if missing_in_model:
        problems.append(f"extracted, not in model: {missing_in_model}")
    detail = "; ".join(problems) if problems else (
        f"all {len(model)} parameters reconcile"
    )
    return GradeComponent("param-coverage", score, not problems, True, detail)


def _parameter_citation(ex: Extraction) -> GradeComponent:
    total = len(ex.parameters)
    cited = sum(1 for p in ex.parameters if p.cited)
    score = _frac(cited, total)
    uncited = [p.id for p in ex.parameters if not p.cited]
    detail = (f"uncited: {uncited}" if uncited
              else f"all {total} parameters cite the paper")
    return GradeComponent("param-citation", score, not uncited, True, detail)


def _initials_citation(ex: Extraction) -> GradeComponent:
    states = ex.state_ids
    cited = 0
    missing = []
    for s in states:
        ic = ex.ic_for(s)
        if ic is not None and ic.cited:
            cited += 1
        else:
            missing.append(s)
    score = _frac(cited, len(states))
    detail = (f"missing/uncited IC: {missing}" if missing
              else f"all {len(states)} states have a cited initial condition")
    return GradeComponent("initials-citation", score, not missing, True, detail)


def _target_citation(ex: Extraction) -> GradeComponent:
    total = len(ex.targets)
    if total == 0:
        return GradeComponent(
            "target-citation", 0.0, False, True,
            "no validation targets declared in extraction.yaml",
        )
    cited = sum(1 for t in ex.targets if t.cited)
    score = _frac(cited, total)
    uncited = [t.id for t in ex.targets if not t.cited]
    detail = (f"uncited: {uncited}" if uncited
              else f"all {total} targets cite the paper")
    return GradeComponent("target-citation", score, not uncited, True, detail)


def grade_components(
    ex: Extraction, species_ids: list[str], param_ids: list[str]
) -> list[GradeComponent]:
    """The deterministic components, given the model's resolved symbol table.

    Pure: no simulation, no tellurium — the symbol table is passed in, so this
    is unit-testable with synthetic inputs.
    """
    return [
        _state_coverage(ex, species_ids),
        _parameter_coverage(ex, param_ids),
        _parameter_citation(ex),
        _initials_citation(ex),
        _target_citation(ex),
    ]


# ----------------------------------------------------------------------------
# Optional LLM reviewer (non-gating)
# ----------------------------------------------------------------------------


def build_review_package(card, ex: Extraction) -> dict:
    """The inputs an external reviewer (human or LLM) needs to judge whether the
    Antimony faithfully encodes the paper."""
    return {
        "slug": card.slug,
        "source": card.source,
        "rubric": {
            "scale": "1-5",
            "5": "every equation term and parameter matches the paper exactly",
            "3": "minor transcription issues that do not change the dynamics",
            "1": "the model encodes a materially different mechanism",
            "report": "severity-tagged issues + a single 1-5 score",
        },
        "extraction": ex.raw,
        "antimony": card.antimony(),
    }


def run_llm_review(card, ex: Extraction) -> LLMReview:
    """Run the optional LLM reviewer if ``INFLECT_LLM_REVIEW_CMD`` is set.

    The command receives the review package as JSON on stdin and must print
    JSON ``{"score": <1-5>, "notes": "<text>"}`` on stdout. Always non-gating:
    any failure (unset, bad output, non-zero exit) yields an unconfigured/empty
    review rather than failing the grade.
    """
    cmd = os.environ.get("INFLECT_LLM_REVIEW_CMD")
    if not cmd:
        return LLMReview(configured=False)
    try:
        proc = subprocess.run(
            cmd, shell=True, input=json.dumps(build_review_package(card, ex)),
            capture_output=True, text=True, timeout=300, check=False,
        )
        data = json.loads(proc.stdout)
        score = float(data["score"])
        return LLMReview(configured=True, score=score, notes=str(data.get("notes", "")))
    except Exception as exc:  # noqa: BLE001 — reviewer is non-gating by design
        return LLMReview(configured=True, score=None, notes=f"review failed: {exc}")


# ----------------------------------------------------------------------------
# Top-level entry
# ----------------------------------------------------------------------------


def grade_model(card, *, llm: bool = False) -> FidelityReport | None:
    """Grade one model's extraction fidelity, or ``None`` if it has no
    ``extraction.yaml`` (such models are skipped, not failed)."""
    ex = extraction_for(card)
    if ex is None:
        return None
    species_ids, param_ids = antimony_symbols(card.antimony())
    components = grade_components(ex, species_ids, param_ids)
    review = run_llm_review(card, ex) if llm else None
    return FidelityReport(slug=card.slug, components=components, llm=review)
