# Contributing a model

Models enter the database as pull requests. A PR merges into `main` only once its
model is extracted to Antimony and passes both checks: it reproduces the paper's
published results, and its Antimony matches its `extraction.yaml`. CI is the gate.
`scripts/check_models.py` fails while any model directory is still just a paper.

There are three roles. You can play all three, or hand off the middle step to
Claude.

```
  contributor            Claude (extract-model skill)        CI / maintainer
  ───────────            ───────────────────────────        ───────────────
  open a PR with   ──►   run /extract-model on the PR:  ──►  CI runs the gate;
  the paper +            write extraction, Antimony,         merge to main only
  CITATION.md            and card; make it pass              when it's green
```

## 1. Open a PR with the paper

Create `inflect_models_db/models/<slug>/` (slug is `<firstauthor>-<year>-<short-topic>`,
e.g. `reynolds-2006-acute-inflammation`) containing:

- `paper/CITATION.md`: authors, title, journal, and a DOI / PubMed / BioModels id.
- `paper/<name>.pdf`: only if the paper's licence allows redistribution (open
  access / CC). Paywalled PDFs are git-ignored by default (`models/**/paper/*.pdf`);
  keep them local and rely on the citation.

CI is now red. The model is pending extraction, which is what blocks the merge:

```
[PENDING] <slug>: pending extraction — PDF present but no card.yaml/model.ant yet
gate: FAIL — not mergeable until every model above is green
```

## 2. Run the extraction skill on the PR

Anyone with Claude Code checks out the PR branch and runs the
[`extract-model`](./.claude/skills/extract-model/SKILL.md) skill:

```
/extract-model
```

It reads the paper into `extraction.yaml`, writes a faithful `model.ant` and
`card.yaml`, runs the model through viva-tellurium, and iterates until validation
and the fidelity grade both pass. Commit the resulting `extraction.yaml`,
`model.ant`, `card.yaml`, `reference/`, `figures/`, and model `README.md` to the
same PR.

## 3. Merge only when the gate is green

Run the gate locally before pushing:

```bash
uv run python scripts/check_models.py     # must print "gate: PASS"
uv run pytest -q
```

The gate passes only when all of a model's checks hold. Validation (see
[`docs/model-card-schema.md`](./docs/model-card-schema.md)):

- every scenario settles within tolerance of the published steady states;
- the run actually reached steady state (convergence guard);
- any declared threshold or bifurcation reproduces;
- if an oracle is declared (e.g. a curated BioModels SBML), the full trajectory
  agrees with it by NRMSE.

Fidelity grade (see [`docs/extraction-schema.md`](./docs/extraction-schema.md)),
for any model with an `extraction.yaml`:

- every state has a species and an equation, with no undeclared species;
- the model's parameters and the extracted parameters are the same set;
- every parameter, initial condition, and target cites the paper.

When CI is green, a maintainer merges to `main`. Never widen a tolerance to get a
pass. A failing check means the Antimony or the target is wrong; fix the model,
or report the divergence in the PR.

## What makes a good target

Assert what the paper actually claims and what the model can reproduce
deterministically: steady states, thresholds/bifurcations, an oscillation period,
a characteristic trajectory. Put the published numbers in `reference/` with a note
saying which figure or table they came from. Prefer an oracle (a deposited SBML)
when one exists; it checks the whole curve, not just a few points.
