"""The database is discoverable and every card is well-formed and loadable."""

from inflect_models_db.registry import list_models


def test_database_is_nonempty():
    assert list_models(), "no models found under models/"


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
