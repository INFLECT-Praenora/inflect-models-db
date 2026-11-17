# `card.yaml` schema

Every model is driven by its card. The loader
(`inflect_models_db.card.load_card`) validates the required structure.

```yaml
slug: <firstauthor>-<year>-<topic>     # must match the folder name
title: <human title>

source:                                 # at least one id is required
  authors: "<names>"
  year: <int>
  title: <paper title>
  journal: <journal>
  doi: <doi>
  pubmed: "<id>"
  biomodels: <BIOMDxxxxxxxxxxx>

model:
  file: model.ant
  format: antimony                      # 'antimony' (text-loaded) — SBML also runs via viva-tellurium
  species: [P, Nstar, D, C_A]           # floating-species ids the card watches
  state_meaning: {P: Pathogen, ...}     # optional, documentation only
  provenance: >                         # where the equations/parameters came from

validation:
  description: >                        # what published result this reproduces
  time: {start: 0, end: 500, n_points: 501, units: hours}

  scenarios:                            # >= 1 required
    - name: <scenario>
      description: >
      initials: {P: 0.5, ...}           # initial-condition overrides for this run
      expect:                           # steady-state target per watched species
        P: {target: 0.0, tol: 0.01}
        ...

  threshold:                            # optional: a published bifurcation
    variable: P                         # control variable (swept via initials)
    between: [1.0, 1.2]                 # the boundary lies in this bracket
    classify_by: {variable: D, healthy_below: 1.0}

  steady_state:                         # optional convergence guard (recommended)
    rel_change_below: 1.0e-3            # max rel. change over the final 10% window

  oracle:                              # optional independent full-trajectory check
    kind: sbml                          # simulate this encoding via tellurium directly
    file: reference/BIOMD0000000714.xml # and compare the extracted model to it
    nrmse_below: 1.0e-3                 # per-species NRMSE must stay below this

figures:                                # optional; default is one 'outcomes' grid
  - name: outcomes
    kind: outcome-scenarios
    file: figures/outcomes.png
    caption: >
```

## Semantics

- **scenario / expect** — each scenario is run over `validation.time`; the final
  value of each `expect` species must be within `tol` of `target`. These are the
  published steady states.
- **threshold** — the model is run at `between[0]` and `between[1]` (overriding
  `variable`); the outcome is classified by `classify_by` (healthy iff the
  readout variable's final value is `< healthy_below`). The check passes when the
  low value is healthy and the high value is not — i.e. the boundary is bracketed.
- **steady_state** — after each scenario runs, the largest relative change of any
  species across the final 10% of the trajectory must be `< rel_change_below`.
  Guards against reading targets before the system has settled.
- **oracle** — an independent reference encoding (a deposited SBML). Validation
  simulates it directly with tellurium (a different path from the repo's
  Antimony) using each scenario's initials, and requires per-species
  `NRMSE < nrmse_below` over the whole trajectory. Use when the model is
  deposited in BioModels or similar.
- **figures** — `reproduce_figures` renders one panel per declared species, one
  line per scenario, to the given file.
