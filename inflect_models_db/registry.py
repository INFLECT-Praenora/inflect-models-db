"""Discover curated models under ``inflect_models_db/models/``.

A model lives in ``inflect_models_db/models/<slug>/`` and is recognised by the
presence of a ``card.yaml``. The models live **inside the package** so they ship
in the wheel — a plain ``pip install`` (or ``pip install git+<repo>``) exposes the
curated database, not just an editable/source checkout. Override the root with the
``INFLECT_MODELS_DB_ROOT`` environment variable to point at a copy elsewhere.
"""

from __future__ import annotations

import os
from pathlib import Path

from inflect_models_db.card import ModelCard, load_card

# Inside the package (ships in the wheel). Resolve both the installed location and
# the source checkout, since they are the same path relative to this file.
_DEFAULT_ROOT = Path(__file__).resolve().parent / "models"


def models_root() -> Path:
    env = os.environ.get("INFLECT_MODELS_DB_ROOT")
    return Path(env).expanduser().resolve() if env else _DEFAULT_ROOT


def list_models() -> list[str]:
    """Return the sorted slugs of every model that has a ``card.yaml``."""
    root = models_root()
    if not root.exists():
        return []
    return sorted(
        p.name for p in root.iterdir() if (p / "card.yaml").is_file()
    )


def get_model(slug: str) -> ModelCard:
    """Load the :class:`ModelCard` for ``slug``."""
    card = models_root() / slug / "card.yaml"
    if not card.is_file():
        raise FileNotFoundError(
            f"no model {slug!r} under {models_root()} "
            f"(have: {', '.join(list_models()) or 'none'})"
        )
    return load_card(card)


def all_cards() -> list[ModelCard]:
    return [get_model(s) for s in list_models()]
