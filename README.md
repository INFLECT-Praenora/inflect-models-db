# inflect-models-db

[![CI](https://github.com/INFLECT-Praenora/inflect-models-db/actions/workflows/ci.yml/badge.svg)](https://github.com/INFLECT-Praenora/inflect-models-db/actions/workflows/ci.yml)
[![license](https://img.shields.io/badge/license-Apache%202.0-blue)](./LICENSE)

A curated database of **published dynamical models extracted from papers into
[Antimony](https://tellurium.analogmachine.org/)**, each one run through
[`viva-tellurium`](https://github.com/vivarium-collective/viva-tellurium) and
**validated against the results reported in its source paper**. Built for the
INFLECT (ARPA-H CIRCLE) project, with a bias toward sepsis / acute-inflammation
and physiological models.

Every model ships with:

- `model.ant` — the Antimony, faithful to the paper's equations and parameters;
- `card.yaml` — the source citation plus **quantitative validation targets**;
- `reference/` — the published numbers those targets come from;
- `figures/` — a machine-generated reproduction to compare against the paper;
- a test (parametrized, automatic) asserting the model reproduces the targets.

## Why run through viva-tellurium?

Models are executed by wrapping their Antimony as a `viva_tellurium`
`TelluriumUTCStep` — the same `process-bigraph` bridge the rest of the ecosystem
composes with. A model validated here drops straight into a bigraph document as
a Process; it is not a throwaway reproduction script.

## Running a model in the simulation-core

Every curated model also exposes a **process-bigraph composite**, so it drops
directly into [`inflect-sim-core`](https://github.com/INFLECT-Praenora/inflect-sim-core)
(or any bigraph document) with no per-model wiring — the `card.yaml` *is* the run
spec (model, named scenarios, observable species, time window).

```bash
inflect-models composites        # the composite + scenarios each model exposes
```

```python
from inflect_models_db import bigraph, registry

bigraph.register_all()           # register every model as a composite generator
card = registry.get_model("reynolds-2006-acute-inflammation")
req = bigraph.scenario_request(card, "aseptic-death")   # {antimony, initials, observables, duration, interval, ...}
```

The composite generator is named `modelsdb_<slug>`, takes a `scenario` knob (the
card's named scenarios), and emits the card's observable species. simulation-core
discovers these at catalog-build time, so every database model appears in its
workbench and resolves by slug through `simulate("<slug>")`. See
[`docs/superpowers/specs/2026-11-24-sim-core-integration-design.md`](docs/superpowers/specs/2026-11-24-sim-core-integration-design.md).

## Install

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"      # pulls viva-tellurium + tellurium/libroadrunner
```

## Demo

One command walks the whole pipeline — **PDF → Antimony → validation → vivarium
module** — on the Reynolds 2006 example: it reads the source PDF, shows the
extracted Antimony, validates it against the published steady states through
viva-tellurium (with a `P(0)` sweep + bifurcation figure), and finally runs the
same model as a composed `process-bigraph` module.

```bash
python demo/demo.py        # or: uv run python demo/demo.py
```

See [`demo/`](./demo).

## Use

```bash
inflect-models list                                    # what's in the database
inflect-models validate                                # check all models vs published results
inflect-models validate reynolds-2006-acute-inflammation
inflect-models reproduce reynolds-2006-acute-inflammation   # regenerate figures
pytest -q                                              # the validation suite
```

```python
from inflect_models_db import get_model, validate_model, reproduce_figures

card = get_model("reynolds-2006-acute-inflammation")
print(validate_model(card).summary())
reproduce_figures(card)
```

## Repository layout

```
models/<slug>/
  model.ant            Antimony model extracted from the paper
  card.yaml            citation + validation targets (see docs/model-card-schema.md)
  paper/CITATION.md    DOI/links (PDF only if its licence permits redistribution)
  reference/*.csv      published numbers the targets assert against
  figures/*.png        generated reproduction
  README.md            the model card
inflect_models_db/     the library: registry · run (viva-tellurium) · validate
tests/                 parametrized over every model — new entries tested automatically
docs/                  workflow.md · model-card-schema.md
.claude/skills/extract-model/   the extraction skill (see below)
```

## Validation

Each model is held to more than a single endpoint. A model passes only when
**every** built-in check holds (all driven off `card.yaml`):

- **Published steady states** — each scenario settles within tolerance of the
  values reported in the paper.
- **Convergence guard** — the run actually reached steady state, so targets
  aren't read mid-transient.
- **Threshold / bifurcation** — a declared qualitative boundary reproduces.
- **Independent oracle** — when the model is deposited elsewhere (e.g. a curated
  BioModels SBML, CC0), validation simulates *that* encoding through a separate
  code path and checks the extracted Antimony reproduces its **full trajectory**
  by NRMSE — corroboration, not a tautology.

```
inflect-models validate     # prints every check, PASS/FAIL
```

## Contributing a model — papers in, validated models out

Models are added by **pull request**, and a PR merges into `main` **only when the
Antimony has been created and validated** — CI (`scripts/check_models.py`) stays
red while a model is just a paper.

```
  open a PR with      run the extract-model          CI gate passes →
  the paper (PDF/  ─► skill on the PR branch:     ─►  maintainer merges
  CITATION.md)        model.ant + card.yaml,           to main
                      validated vs the paper
```

1. **Open a PR** adding `models/<slug>/paper/CITATION.md` (+ the PDF only if its
   licence permits). CI reports the model as *pending extraction* — this is what
   blocks the merge.
2. **Run `/extract-model`** on the PR branch (any Claude Code user): it authors a
   faithful `model.ant` + `card.yaml`, runs it through viva-tellurium, and
   iterates until it reproduces the published results. Commit to the same PR.
3. **Merge when green** — `python scripts/check_models.py` must print `gate: PASS`.

Full details: **[CONTRIBUTING.md](./CONTRIBUTING.md)**. Tolerances are never
widened to force a pass — a failing check means the model or the target is wrong.

## Adding a model (as a maintainer)

Invoke the **`extract-model`** skill — it walks the full procedure: read the
paper, author faithful Antimony, pick validation targets from the paper's
figures/tables, write `card.yaml`, run through viva-tellurium, and iterate until
`pytest -k <slug>` is green. See [`docs/workflow.md`](./docs/workflow.md).

## Models

| Slug | Source | Reproduces |
|------|--------|------------|
| [`reynolds-2006-acute-inflammation`](./models/reynolds-2006-acute-inflammation) | Reynolds et al., *J. Theor. Biol.* 2006 | Healthy ↔ aseptic-death bistability in initial pathogen load |

## License

Apache 2.0 — see [`LICENSE`](./LICENSE). Source papers are the property of their
publishers; see each model's `paper/CITATION.md`.
