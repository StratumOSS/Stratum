# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Vamshi Krishna Santhapuri
"""The published blueprint JSON Schema stays in lock-step with the model.

SCHEMA-01  the committed schema matches what the generator produces

That the real blueprints conform to the schema is guaranteed transitively and
does not need a separate check here: CI's "Validate community blueprints" job
validates every blueprint against the Pydantic model, and this test plus the
`gen_blueprint_schema.py --check` CI step pin the schema to that same model.
"""

from __future__ import annotations

from pathlib import Path

from scripts import gen_blueprint_schema

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCHEMA = _REPO_ROOT / "docs" / "schema" / "hardening-blueprint.schema.json"


def test_committed_schema_is_current():
    assert _SCHEMA.is_file(), "published schema is missing — run gen_blueprint_schema.py"
    assert _SCHEMA.read_text() == gen_blueprint_schema.render(), (
        "docs/schema/hardening-blueprint.schema.json is stale — regenerate it with "
        "`python scripts/gen_blueprint_schema.py`"
    )
