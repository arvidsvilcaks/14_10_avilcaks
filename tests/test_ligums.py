"""CRM galapunkti līgumā docs/openapi.yaml atbilst lietotnei un kursa noteikumiem."""

import importlib.util
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
IESNIEGUMU_API = {"/health", "/submissions", "/submissions/{id}"}  # A1 uzdevums, nav CRM daļa
HTTP_METODES = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def _ligums() -> dict:
    with (ROOT / "docs" / "openapi.yaml").open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def _lint_modulis():
    spec = importlib.util.spec_from_file_location("lint_contract", ROOT / "tools" / "lint_contract.py")
    modulis = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulis)
    return modulis


def _veidne(cels: str) -> str:
    """Parametru nosaukumi neietekmē salīdzināšanu: /a/{id} == /a/{a_id}."""
    return re.sub(r"\{[^}]+\}", "{}", cels)


def _crm_operacijas(ligums: dict) -> set[tuple[str, str]]:
    return {
        (metode.upper(), _veidne(cels))
        for cels, operacijas in ligums["paths"].items()
        if cels not in IESNIEGUMU_API
        for metode in operacijas
        if metode in HTTP_METODES
    }


def test_crm_operacijas_atbilst_kursa_noteikumiem():
    kludas = _lint_modulis().course_rule_errors(_ligums())
    crm_kludas = [k for k in kludas if k.split(":")[0].split(" ")[1] not in IESNIEGUMU_API]
    assert crm_kludas == []


def test_katra_liguma_operacija_ir_lietotne(lietotne):
    marsruti = {
        (metode.upper(), _veidne(cels))
        for cels, operacijas in lietotne.openapi()["paths"].items()
        for metode in operacijas
    }
    trukst = _crm_operacijas(_ligums()) - marsruti
    assert not trukst, f"Līgumā ir, lietotnē nav: {sorted(trukst)}"
