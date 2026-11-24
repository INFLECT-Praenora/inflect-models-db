# Contributing a model

Models enter the database as **pull requests**, and a PR is merged into `main`
only once the model has been **extracted to Antimony and validated against the
paper's published results**. CI is the gate: `scripts/check_models.py` fails
while any model directory is a paper with no validated model.

The flow has three roles — you may play all three, or hand off the middle step.

```
  contributor            Claude (extract-model skill)        CI / maintainer
  ───────────            ───────────────────────────        ───────────────
  open a PR with   ──►   run /extract-model on the PR:  ──►  CI runs the gate;
  the paper +            author model.ant + card.yaml,       merge to main only
  CITATION.md            make it validate                    when it's green
```

## 1. Open a PR with the paper

Create `inflect_models_db/models/<slug>/` (slug = `<firstauthor>-<year>-<short-topic>`, e.g.
`reynolds-2006-acute-inflammation`) containing:

- `paper/CITATION.md` — authors, title, journal, **DOI / PubMed / BioModels id**.
- `paper/<name>.pdf` — **only if the paper's licence permits redistribution**
  (open access / CC). Paywalled PDFs are git-ignored by default
  (`models/**/paper/*.pdf`); keep them local and rely on the citation.

At this point CI is **red** — the model is *pending extraction*. That's expected
and is exactly what blocks the merge:

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

It reads the paper, authors a faithful `model.ant`, picks validation targets
from the paper's figures/tables, writes `card.yaml`, runs the model **through
viva-tellurium**, and iterates until it reproduces the published results. Commit
the resulting `model.ant`, `card.yaml`, `reference/`, `figures/`, and model
`README.md` to the **same PR**.

## 3. Merge only when the gate is green

Run the gate locally before pushing:

```bash
uv run python scripts/check_models.py     # must print "gate: PASS"
uv run pytest -q
```

A model passes the gate only when **all** of its built-in checks hold (see
[`docs/model-card-schema.md`](./docs/model-card-schema.md)):

- every **scenario** settles within tolerance of the **published steady states**;
- the run has actually **reached steady state** (convergence guard);
- any declared **threshold / bifurcation** reproduces;
- if an **independent oracle** is declared (e.g. a curated BioModels SBML), the
  full trajectory agrees with it by NRMSE.

When CI is green, a maintainer merges to `main`. **Never widen a tolerance to get
a green** — a failing check means the Antimony or the target is wrong; fix the
model, or report the divergence in the PR.

## What makes a good target

Assert what the paper actually claims and that the model can reproduce
deterministically: steady states, thresholds/bifurcations, oscillation period, a
characteristic trajectory. Put the published numbers in `reference/` with a note
saying which figure/table they came from. Prefer an independent oracle (a
deposited SBML) when one exists — it validates the whole curve, not just points.
