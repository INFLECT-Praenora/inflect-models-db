"""The database is discoverable and every card is well-formed and loadable."""

from pathlib import Path

import inflect_models_db
from inflect_models_db.registry import list_models, models_root


def test_database_is_nonempty():
    assert list_models(), "no models found under models/"


def test_models_live_inside_the_package_so_they_ship_in_the_wheel():
    """The curated models must sit under the installed package
    (``inflect_models_db/models/``), not at the repo root — otherwise a plain
    ``pip install`` / ``pip install git+<repo>`` would import the code but find no
    models (only an editable/source checkout would work). Guards the packaging
    that ships the database in the wheel."""
    pkg_dir = Path(inflect_models_db.__file__).resolve().parent
    assert models_root() == pkg_dir / "models", (
        "models_root() must resolve inside the package so the database ships in the wheel"
    )
    assert (pkg_dir / "models").is_dir()
    # Every discovered model's card really lives under the package dir.
    for slug in list_models():
        card = (pkg_dir / "models" / slug / "card.yaml")
        assert card.is_file(), f"{slug}: card not under the package ({card})"


def test_card_parses_and_model_file_exists(card):
    assert card.slug
    assert card.model_path.exists()
    assert card.scenarios, f"{card.slug}: no scenarios declared"


def test_source_is_cited(card):
    src = card.source
    # Every curated model must be traceable to a publication.
    assert src.get("doi") or src.get("pubmed") or src.get("biomodels"), (
        f"{card.slug}: card.source needs a doi / pubmed / biomodels id"
    )


def test_antimony_loads_and_exposes_declared_species(card, core):
    """The Antimony parses through viva-tellurium and the floating species
    match the species the card declares."""
    from inflect_models_db.run import run_model

    t = card.time
    traj = run_model(
        card.antimony(),
        start=t["start"],
        end=t["start"] + 1.0,  # short run: just confirm it loads + integrates
        n_points=2,
        core=core,
    )
    for sp in card.species:
        assert sp in traj.species, f"{card.slug}: species {sp!r} not emitted"
