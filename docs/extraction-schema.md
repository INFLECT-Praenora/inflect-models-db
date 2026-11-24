# `extraction.yaml` schema

The **structured reading of the paper**, authored *before* `model.ant`. It
records how the model was read out of the source — state variables, equations,
parameters, initial conditions, and the published targets — each with a pointer
to where in the paper it came from. The loader is
`inflect_models_db.extraction.load_extraction`; the fidelity grade
(`inflect-models grade`, `inflect_models_db.grade`) reconciles it against the
Antimony that was ultimately written.

It is the stage paper2code calls an *analysis artifact*: an auditable,
diffable intermediate that a reviewer can check against the paper independently
of the equations.

**Optional.** A model without an `extraction.yaml` still runs, validates, and
ships exactly as before — it is simply not fidelity-graded. When present, the
grade is CI-gating.

```yaml
slug: <firstauthor>-<year>-<topic>     # matches the folder name

source:                                 # minimal pointer; full citation in card.yaml
  authors: "<names>"
  year: <int>
  doi: <doi>

state_variables:                        # >= 1 required
  - id: P                               # must match a floating species in model.ant
    meaning: Pathogen load
    units: <units or "model units">

equations:                              # one per state variable, transcribed from the paper
  - state: P                            # the state_variable id this is the RHS for
    rhs: "k_pg*P*(1 - P/p_inf) - ..."   # every term, faithful to the paper
    source: "Eq. (1), §2"               # where in the paper

parameters:                             # every published parameter
  - id: k_pg                            # must match a parameter in model.ant
    value: 0.3
    units: "1/h"
    source: "Table 2"                   # REQUIRED — the grade fails on any uncited parameter

initial_conditions:                     # one per state variable
  - state: P
    value: 1.0
    source: "baseline; scenarios override"   # REQUIRED

targets:                                # the published results card.yaml asserts
  - id: healthy-steady-state
    describes: "<what this outcome is>"
    source: "Fig. 2 / §3"               # REQUIRED

notes: >                                # anything a reviewer should know
  <e.g. which model.ant symbols are assignment-rule auxiliaries, not parameters>
```

## What the grade checks

`inflect-models grade <slug>` loads `model.ant`'s compiled symbol table (via
tellurium) and reconciles it against the extraction. All components are
deterministic and gating:

| Component | Passes when |
|---|---|
| `state-coverage` | every declared state is a model species **and** has an equation; the model has no undeclared species |
| `param-coverage` | the model's parameters and the declared parameters are the **same set** (`:=` assignment-rule auxiliaries excluded) |
| `param-citation` | every declared parameter has a `source` |
| `initials-citation` | every state has a cited initial condition |
| `target-citation` | every declared target has a `source` (and at least one target exists) |

Assignment-rule auxiliaries in the Antimony (e.g. `f_Nstar := ...`) are derived
quantities, not published parameters; the grade excludes them automatically, so
you do **not** list them under `parameters`.

## Optional LLM reviewer (non-gating)

`inflect-models grade <slug> --llm` additionally runs an external reviewer when
`INFLECT_LLM_REVIEW_CMD` is set: the command receives the review package as JSON
on stdin and prints `{"score": <1-5>, "notes": "..."}`. It adds a faithfulness
score but never blocks a model and never replaces the numeric validation. When
the env var is unset the reviewer is skipped (not failed).
