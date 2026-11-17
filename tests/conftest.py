"""Shared fixtures: parametrize over every curated model."""

import pytest

from inflect_models_db.registry import all_cards, list_models


def pytest_generate_tests(metafunc):
    """Parametrize any test asking for ``card`` / ``slug`` over all models."""
    if "card" in metafunc.fixturenames:
        cards = all_cards()
        metafunc.parametrize("card", cards, ids=[c.slug for c in cards])
    elif "slug" in metafunc.fixturenames:
        slugs = list_models()
        metafunc.parametrize("slug", slugs, ids=slugs)


@pytest.fixture(scope="session")
def core():
    from inflect_models_db.run import build_core

    return build_core()
