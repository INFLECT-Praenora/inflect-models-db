# Reference data

- **`outcomes.csv`** — the published steady-state outcomes the scenario targets
  assert against (read at t = 500 h).
- **`BIOMD0000000714.xml`** — the community-curated SBML encoding of this model
  from [BioModels](https://www.ebi.ac.uk/biomodels/BIOMD0000000714), used as an
  **independent oracle**: validation simulates it directly with tellurium and
  checks the repo's extracted Antimony reproduces its full trajectory
  (per-species NRMSE, see `card.yaml` → `validation.oracle`). BioModels content
  is released under **CC0 1.0** (public domain), so it is redistributed here.
