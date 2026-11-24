# inflect-models-db ↔ simulation-core integration

Date: 2026-11-24
Status: approved (user said "dive in"; questions opted out)

## Intent / why

`inflect-models-db` curates paper-extracted Antimony models, each with a
`card.yaml` (citation + validation scenarios, observable species, time window,
quantitative targets, SBML oracle), validated by running through `viva-tellurium`.
`inflect-sim-core` is the simulation core: wrap any simulator behind one typed
contract, compose modules, swap engines.

Today the two are unconnected even though they already share an engine
(viva-tellurium) and sim-core's `simulate()` already accepts an Antimony/SBML
string, a file path, or a registered-composite id. The goal: **every model in
the database can easily run in sim-core** — appear in its catalog/dashboard,
resolve by slug through the contract, and carry its scenarios/observables/targets.

## Goals

- A curated model becomes a **first-class sim-core composite** with no per-model
  wiring — dropping `model.ant` + `card.yaml` is enough.
- `simulate("<slug>")` (and `simulate("<slug>", scenario=...)`) runs a model from
  the database through the sim-core contract, with the card's observables as
  defaults and its targets available for verification.
- Models show up in the workbench catalog (Repositories/Composites) and run from
  the dashboard "Run" button.

## Non-goals / anti-goals

- Not unifying `card.yaml` into sim-core's composite-spec schema (approach C) —
  premature with one model; keep the card the source of truth.
- Not moving model files into sim-core — the database stays the curation home.
- Not changing how models are *validated* in models-db (the paper-reproduction
  tests stay as they are).

## Constraints

- models-db must keep working stand-alone (its validation CI, `inflect-models`
  CLI, demo) with **zero** dependency on sim-core.
- A bare `import inflect_models_db` must not require an engine at module top
  level (mirror sim-core's lazy-engine discipline); the composite *builds* need
  viva-tellurium, importing the module does not.
- No model-specific code: the bridge is driven entirely off the card.

## Approaches considered

- **A — adapter in sim-core.** sim-core reads card internals and wraps each model.
  Rejected: pushes card knowledge into sim-core; the rework was asked of models-db.
- **B — the card emits a process-bigraph composite; sim-core discovers + registers.**
  **Chosen.** Realizes models-db's own stated promise ("a model that drops straight
  into a bigraph document"). Card→composite mapping stays with the cards; sim-core's
  side is a thin discover-and-register shim.
- **C — unify card.yaml into sim-core's catalog schema.** Rejected: largest rework,
  tight coupling, premature.

## Design (approach B)

### models-db side (this repo)

`inflect_models_db/bigraph.py`:

- `card_to_generator(card)` → builds and registers a `@composite_generator`
  (process-bigraph), name `modelsdb_<slug_with_underscores>`. Its one scientific
  knob is `scenario` (enum of the card's scenario names, default = first); a
  `scenario`'s `initials` become the viva-tellurium document's `species_overrides`.
  `interval` and `default_n_steps` are derived from the card's `time` block.
  Reuses `run.as_vivarium_document` (the existing TelluriumProcess document path),
  so a models-db composite is the same shape as any viva-tellurium composite.
- `card_observables(card)` → the observable species ids (card `model.species`,
  falling back to the union of scenario `expect` keys).
- `register_all(cards=None)` → register every curated model; one malformed card
  never breaks the rest. Returns the registered generator names.
- `scenario_request(card, scenario)` → a small dict `{antimony, initials,
  observables, duration, interval}` the contract side can consume without
  importing process-bigraph.

`process-bigraph` becomes an explicit dependency (already used by `run.py` and
pulled transitively via viva-tellurium).

### sim-core side (companion PR in inflect-sim-core)

- `viva_simulation_core/models_db.py`: lazily `import inflect_models_db.bigraph`
  and `register_all()` into the catalog; expose `list_models()` and
  `resolve(slug, scenario=...)` → a `SimulationRequest`-ready payload.
- `simulate()` slug resolution: a bare string that is a known models-db slug
  resolves to the card's Antimony + scenario initials (as parameter overrides) +
  species observables, run via the existing SBML engine path (named observables,
  cross-engine verification for free).
- `[models-db]` optional extra + a `mode: reference` import of inflect-models-db
  in `workspace.yaml`, so the catalog shows every curated model.

### Observable-shape note

A models-db model's observables are *floating species*, which land in the
viva-tellurium document's bulk `species` store (not the `parameters` store that
`sepsis_sbml` uses for SBML globals). The dashboard/native-gallery reads species
from any viva-tellurium composite already, so models run + visualize in the UI.
The **contract** `simulate("<slug>")` path uses the SBML engine runner (named
roadrunner selections), which returns species by name directly and avoids the
bulk-store mapping — the simplest robust path for named observables + verification.

## Left to the builder

- Whether to also teach sim-core's `_run_composite` to read the bulk `species`
  store so `simulate("<composite-id>")` works on models-db composites too (nice to
  have; the slug path already covers the user-facing case).
- Scenario → parameter name collisions if a future card overrides *parameters*
  (not just species initials); current cards only override species.
