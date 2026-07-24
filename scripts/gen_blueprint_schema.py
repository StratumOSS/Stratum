# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Vamshi Krishna Santhapuri
"""Generate the published JSON Schema for the `HardeningBlueprint` YAML format.

The schema is derived from the Pydantic model that BakeX actually validates
against (`bakex.core.blueprint.ComplianceProfile`), so it can never drift from
the real acceptance criteria. The committed copy at
`docs/schema/hardening-blueprint.schema.json` is what agents, editors, and CI in
other repos reference.

Usage:
    python scripts/gen_blueprint_schema.py           # write the schema file
    python scripts/gen_blueprint_schema.py --check   # fail if the file is stale
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from bakex.core.blueprint import ComplianceProfile

_SCHEMA_PATH = Path("docs/schema/hardening-blueprint.schema.json")
_SCHEMA_ID = "https://raw.githubusercontent.com/invicton/bakex/main/docs/schema/hardening-blueprint.schema.json"


def build_schema() -> dict:
    schema = ComplianceProfile.model_json_schema()
    # Present it under the public name and as a referenceable published schema.
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": _SCHEMA_ID,
        "title": "HardeningBlueprint",
        **{k: v for k, v in schema.items() if k not in ("title",)},
    }
    return schema


def render() -> str:
    return json.dumps(build_schema(), indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    rendered = render()

    if "--check" in argv:
        if not _SCHEMA_PATH.is_file() or _SCHEMA_PATH.read_text() != rendered:
            print(
                f"{_SCHEMA_PATH} is out of date. Regenerate it with:\n    python scripts/gen_blueprint_schema.py",
                file=sys.stderr,
            )
            return 1
        print(f"{_SCHEMA_PATH} is up to date.")
        return 0

    _SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SCHEMA_PATH.write_text(rendered)
    print(f"Wrote {_SCHEMA_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
