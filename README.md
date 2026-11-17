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

## Adding a model

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
