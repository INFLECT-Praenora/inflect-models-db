# inflect-models-db

[![CI](https://github.com/INFLECT-Praenora/inflect-models-db/actions/workflows/ci.yml/badge.svg)](https://github.com/INFLECT-Praenora/inflect-models-db/actions/workflows/ci.yml)
[![license](https://img.shields.io/badge/license-Apache%202.0-blue)](./LICENSE)

Published dynamical models from the literature, extracted into
[Antimony](https://tellurium.analogmachine.org/) and checked against the numbers
their papers report. Each model runs through
[`viva-tellurium`](https://github.com/vivarium-collective/viva-tellurium), so it
also works as a process-bigraph module in the wider ecosystem. Built for INFLECT
(ARPA-H CIRCLE), focused on sepsis, acute inflammation, and physiology.

Every model is a folder under `inflect_models_db/models/<slug>/`:

| File | What it is |
|------|------------|
| `extraction.yaml` | The paper read into structured form: state variables, equations, parameters, and targets, each cited to where it came from. Written before the Antimony. |
| `model.ant` | The Antimony, matching the paper's equations and parameters. |
| `card.yaml` | Citation plus the quantitative targets the model must reproduce. |
| `reference/` | The published numbers those targets come from. |
| `figures/` | A generated reproduction to compare against the paper. |
| `paper/CITATION.md` | DOI and links. The PDF only if its licence allows redistribution. |
| `README.md` | The model's own page. |

A model is accepted only when it passes two checks: it reproduces the published
numbers (validation), and its Antimony matches its `extraction.yaml` (the
fidelity grade). Both run in CI.

## Install

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"      # pulls viva-tellurium + tellurium/libroadrunner
```

## Use

```bash
inflect-models list                                         # what's in the database
inflect-models validate                                     # every model vs its published results
inflect-models validate reynolds-2006-acute-inflammation    # one model
inflect-models grade                                        # Antimony vs extraction.yaml
inflect-models reproduce reynolds-2006-acute-inflammation   # regenerate figures
pytest -q                                                   # the full suite
```

```python
from inflect_models_db import get_model, validate_model, reproduce_figures

card = get_model("reynolds-2006-acute-inflammation")
print(validate_model(card).summary())
reproduce_figures(card)
```

Point `INFLECT_MODELS_DB_ROOT` at any `.../models` directory to use a different
set than the one packaged in the wheel.

## The two checks

**Validation** checks that the model reproduces the paper's numbers. Everything
is driven off `card.yaml`:

- Each scenario settles within tolerance of the published steady state.
- A convergence guard confirms the run actually reached steady state, so a target
  isn't read mid-transient.
- Any declared threshold or bifurcation reproduces.
- If the model is deposited elsewhere (for example a curated BioModels SBML), an
  oracle simulates that encoding through a separate code path and checks the full
  trajectory agrees by NRMSE.

```bash
inflect-models validate     # prints every check, PASS/FAIL
```

**The fidelity grade** checks that the Antimony actually encodes the paper.
Matching the numbers isn't enough on its own: a parameter can be transcribed
wrong and still land on the targets by luck. The grade reconciles the compiled
Antimony against `extraction.yaml`:

- Every state variable has a species and an equation, and there are no undeclared
  species.
- The model's parameters and the extracted parameters are the same set
  (assignment-rule helpers like `f(N*)` are excluded).
- Every parameter, initial condition, and target cites the paper.

It's deterministic and gates CI for any model that ships an `extraction.yaml`.
An optional LLM reviewer (`--llm`, via `INFLECT_LLM_REVIEW_CMD`) can add a 1–5
faithfulness score; it never gates.

```bash
inflect-models grade        # prints every fidelity component, PASS/FAIL
```

See [`docs/extraction-schema.md`](docs/extraction-schema.md) and
[`docs/model-card-schema.md`](docs/model-card-schema.md) for the file formats,
and [`docs/workflow.md`](docs/workflow.md) for how extraction works end to end.

## Running a model as a process-bigraph module

Models run through viva-tellurium, so each one is a composable process-bigraph
module, not a standalone script. Each also exposes a composite generator named
`modelsdb_<slug>`, built straight from its `card.yaml` (model, scenarios,
observables, time window). It takes a `scenario` knob and emits the card's
observable species.

```bash
inflect-models composites        # the composite and scenarios each model exposes
```

```python
from inflect_models_db import bigraph, registry

bigraph.register_all()           # register every model as a composite generator
card = registry.get_model("reynolds-2006-acute-inflammation")
req = bigraph.scenario_request(card, "aseptic-death")
```

[`inflect-sim-core`](https://github.com/INFLECT-Praenora/inflect-sim-core)
discovers these generators at catalog-build time, so every model shows up in its
workbench and resolves by slug through `simulate("<slug>")`. Design notes:
[`docs/superpowers/specs/2026-11-24-sim-core-integration-design.md`](docs/superpowers/specs/2026-11-24-sim-core-integration-design.md).

## Demo

One command runs the whole pipeline on the Reynolds 2006 example: read the PDF,
show the extracted Antimony, validate it against the published steady states
(with a `P(0)` sweep and bifurcation figure), then run the same model as a
composed process-bigraph module.

```bash
python demo/demo.py        # or: uv run python demo/demo.py
```

See [`demo/`](./demo).

## Add a model

Models are added by pull request. A PR merges only when its model is extracted
and passes both checks; CI stays red while a model is still just a paper.

1. Open a PR adding `inflect_models_db/models/<slug>/paper/CITATION.md` (and the
   PDF if its licence allows). CI reports the model as pending extraction, which
   blocks the merge.
2. On the PR branch, run `/extract-model` in Claude Code. It reads the paper,
   writes `extraction.yaml`, `model.ant`, and `card.yaml`, runs the model through
   viva-tellurium, and iterates until validation and the grade both pass. Commit
   to the same PR.
3. Merge when green: `python scripts/check_models.py` must print `gate: PASS`.

Tolerances are never widened to force a pass. A failing check means the model or
the target is wrong. Full details in [`CONTRIBUTING.md`](./CONTRIBUTING.md); the
step-by-step procedure is the [`extract-model`](./.claude/skills/extract-model/SKILL.md)
skill.

## Repository layout

```
inflect_models_db/     the library: registry, run (viva-tellurium), validate, grade, bigraph
  models/<slug>/       models live inside the package, so a plain pip install ships them
tests/                 parametrized over every model; new entries are tested automatically
docs/                  workflow.md, model-card-schema.md, extraction-schema.md
scripts/               check_models.py (the merge gate), reproduce.py
demo/                  the end-to-end PDF-to-module demo
.claude/skills/extract-model/   the extraction procedure
```

## Models

| Slug | Source | Reproduces |
|------|--------|------------|
| [`reynolds-2006-acute-inflammation`](./inflect_models_db/models/reynolds-2006-acute-inflammation) | Reynolds et al., *J. Theor. Biol.* 2006 | Healthy / aseptic-death bistability in initial pathogen load |

## License

Apache 2.0, see [`LICENSE`](./LICENSE). Source papers belong to their publishers;
see each model's `paper/CITATION.md`.
