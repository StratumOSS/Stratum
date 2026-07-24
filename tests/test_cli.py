# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Vamshi Krishna Santhapuri
"""`bakex` CLI — the unique command users type.

CLI-01  `bakex version` prints the package version
CLI-02  `bakex serve` invokes uvicorn with the parsed host/port
CLI-03  `bakex serve --port/--host/--reload` are passed through
CLI-04  no command (or bad command) prints help and exits non-zero
CLI-05  `bakex validate` passes a real blueprint and exits 0
CLI-06  `bakex validate` fails an invalid/missing blueprint and exits 1
CLI-07  `bakex validate --json` emits machine-readable results
CLI-08  `bakex build <file>` loads the blueprint and drives run_build
CLI-09  `bakex build <unknown>` exits 1 without calling run_build
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bakex import __version__, cli

_REPO_ROOT = Path(__file__).resolve().parent.parent
_VALID_BLUEPRINT = _REPO_ROOT / "profiles" / "templates" / "ubuntu22-cis-l1-aws.yaml"


def test_version_prints_version(capsys):
    rc = cli.main(["version"])
    assert rc == 0
    out = capsys.readouterr().out
    assert __version__ in out


def test_serve_invokes_uvicorn_defaults():
    fake_uvicorn = MagicMock()
    with patch.dict("sys.modules", {"uvicorn": fake_uvicorn}):
        rc = cli.main(["serve"])
    assert rc == 0
    fake_uvicorn.run.assert_called_once()
    args, kwargs = fake_uvicorn.run.call_args
    assert args[0] == "bakex.main:app"
    assert kwargs["host"] == "0.0.0.0"
    assert kwargs["port"] == 8000


def test_serve_passes_through_host_port_reload():
    fake_uvicorn = MagicMock()
    with patch.dict("sys.modules", {"uvicorn": fake_uvicorn}):
        rc = cli.main(["serve", "--host", "127.0.0.1", "--port", "9000", "--reload"])
    assert rc == 0
    _, kwargs = fake_uvicorn.run.call_args
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 9000
    assert kwargs["reload"] is True


def test_no_command_shows_help_nonzero(capsys):
    rc = cli.main([])
    assert rc != 0
    combined = capsys.readouterr()
    assert "bakex" in (combined.out + combined.err).lower()


def test_unknown_command_errors():
    with pytest.raises(SystemExit) as exc:
        cli.main(["frobnicate"])
    assert exc.value.code != 0


# --- validate ---------------------------------------------------------------


def test_validate_valid_blueprint_exits_zero(capsys):
    rc = cli.main(["validate", str(_VALID_BLUEPRINT)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out
    assert "1/1" in out


def test_validate_missing_file_exits_one(capsys):
    rc = cli.main(["validate", "/no/such/blueprint.yaml"])
    assert rc == 1
    assert "file not found" in capsys.readouterr().out


def test_validate_invalid_blueprint_exits_one(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("kind: HardeningBlueprint\nmetadata:\n  name: broken\n")
    rc = cli.main(["validate", str(bad)])
    assert rc == 1
    assert "ERROR" in capsys.readouterr().out


def test_validate_json_output(capsys):
    import json

    rc = cli.main(["validate", str(_VALID_BLUEPRINT), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["valid"] is True
    assert payload[0]["name"] == "ubuntu22-cis-l1-aws"


def test_validate_mixed_batch_exits_one(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("not: a blueprint\n")
    rc = cli.main(["validate", str(_VALID_BLUEPRINT), str(bad)])
    assert rc == 1


# --- build ------------------------------------------------------------------


def test_build_drives_run_build_and_maps_status(tmp_path):
    """`bakex build <file>` loads the blueprint and calls run_build; a COMPLETE
    job maps to exit 0. run_build is mocked — no real provisioning."""
    from bakex.core import builder as build_service

    def fake_run_build(profile, output_dir, job):
        job.status = build_service.BuildStatus.COMPLETE
        return job

    with patch.object(build_service, "run_build", new_callable=AsyncMock, side_effect=fake_run_build) as m:
        rc = cli.main(["build", str(_VALID_BLUEPRINT), "--output-dir", str(tmp_path)])

    assert rc == 0
    m.assert_called_once()
    called_profile = m.call_args.args[0]
    assert called_profile.metadata.name == "ubuntu22-cis-l1-aws"


def test_build_failed_job_exits_one(tmp_path):
    from bakex.core import builder as build_service

    def fake_run_build(profile, output_dir, job):
        job.status = build_service.BuildStatus.FAILED
        job.error = "provider boom"
        return job

    with patch.object(build_service, "run_build", new_callable=AsyncMock, side_effect=fake_run_build):
        rc = cli.main(["build", str(_VALID_BLUEPRINT), "--output-dir", str(tmp_path)])
    assert rc == 1


def test_build_unknown_blueprint_exits_one_without_building(capsys):
    from bakex.core import builder as build_service

    with patch.object(build_service, "run_build") as m:
        rc = cli.main(["build", "definitely-not-a-real-profile-name"])
    assert rc == 1
    m.assert_not_called()
    assert "not found" in capsys.readouterr().err
