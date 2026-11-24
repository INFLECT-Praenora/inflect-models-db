# How extraction works

```
   paper (equations, parameters, figures)
        │   read by a human / agent (see the extract-model skill)
        ▼
   inflect_models_db/models/<slug>/extraction.yaml    ← structured reading (states, eqs, params, targets — each cited)
        │   authored FIRST; auditable against the paper on its own
        ▼
   inflect_models_db/models/<slug>/model.ant          ← faithful Antimony (translated from the extraction)
   inflect_models_db/models/<slug>/card.yaml          ← published validation targets
        │
        │   inflect_models_db.run.run_scenario(...)
        ▼
   viva_tellurium.TelluriumUTCStep  ← one-shot time course over libroadrunner/CVODE
        │
        ├──► validate_model ──► PASS/FAIL vs published steady states + threshold   (does it reproduce the NUMBERS)
        ├──► grade_model    ──► fidelity OK/FAIL: model ↔ extraction.yaml reconciled (does it encode the PAPER)
        └──► reproduce_figures ──► inflect_models_db/models/<slug>/figures/*.png
```

Two independent checks gate a model: **validation** (the published numbers) and
the **fidelity grade** (the Antimony faithfully encodes the paper, reconciled
against `extraction.yaml`). See [`extraction-schema.md`](extraction-schema.md).

The design choice that matters: models run **through viva-tellurium**, the same
process-bigraph bridge the rest of the ecosystem composes with. A model
validated here is immediately usable as a `process-bigraph` Process in a larger
bigraph document — not a throwaway reproduction script.

## Adding a model

Use the `extract-model` skill — it walks the full procedure. In short:

1. `inflect_models_db/models/<slug>/` with `extraction.yaml` (authored first),
   then `model.ant` + `card.yaml`.
2. `python -m inflect_models_db.cli validate <slug>` until green (the numbers).
3. `python -m inflect_models_db.cli grade <slug>` until green (fidelity vs the
   extraction).
4. `python -m inflect_models_db.cli reproduce <slug>` to regenerate figures.
5. `pytest -k <slug>`.

Tests are parametrized over every model in `models/`, so a new entry is tested
automatically with no new test code.

## Library surface

```python
from inflect_models_db import (
    list_models, get_model,            # registry
    run_model, run_scenario,           # execution (one-shot UTC Step)
    run_as_module, as_vivarium_document,  # execution (composed bigraph module)
    validate_model, validate_scenario, # published-result checks
    check_threshold, reproduce_figures,
)

card = get_model("reynolds-2006-acute-inflammation")
print(validate_model(card).summary())
reproduce_figures(card)
```

## Two ways to run a model

Both go through viva-tellurium:

- **`run_model` / `run_scenario`** wrap the Antimony as a one-shot
  `TelluriumUTCStep` and return a dense trajectory. This is what validation uses.
- **`run_as_module` / `as_vivarium_document`** wrap it as a *time-coupled*
  `TelluriumProcess` inside a `process-bigraph` `Composite` with an emitter —
  the form the model takes when composed with other simulators in a bigraph
  document. `as_vivarium_document` returns the document dict to drop into a
  bigger composite; `run_as_module` runs it and returns a `Trajectory`.

See the [demo](../demo) for both, plus the PDF→Antimony extraction stages.
