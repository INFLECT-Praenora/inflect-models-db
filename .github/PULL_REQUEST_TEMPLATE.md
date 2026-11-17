<!-- Adding a model? See CONTRIBUTING.md. A model PR merges only when CI is green. -->

## Model

- **Slug:** `<firstauthor>-<year>-<topic>`
- **Source:** <authors, year, journal> · DOI/PubMed/BioModels: <id>

## Stage

- [ ] **Paper submitted** — `models/<slug>/paper/CITATION.md` present (PDF only if its licence permits redistribution)
- [ ] **Extracted** — `model.ant` + `card.yaml` authored via the `extract-model` skill
- [ ] **Validated** — `python scripts/check_models.py` prints `gate: PASS` and `pytest -q` is green

## Validation checklist (for an extracted model)

- [ ] Every scenario matches the published steady states within tolerance
- [ ] Scenarios reach steady state (convergence guard passes)
- [ ] Declared threshold / bifurcation reproduces (if any)
- [ ] Independent oracle agrees (if a deposited SBML is available)
- [ ] Tolerances were **not** widened to force a pass

<!-- Paper-only PRs are expected to show CI red ("pending extraction") until step 2 is done. -->
