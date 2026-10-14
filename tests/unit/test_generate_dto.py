"""Проверки генерации используют реальный закреплённый генератор."""

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from scripts.generate_dto import ROOT, generate, main

pytestmark = pytest.mark.unit


def test_generation_is_reproducible_across_paths(tmp_path: Path) -> None:
    source = (ROOT / "openapi.yaml").read_bytes()
    results = []
    for name in ("first-project", "другой проект"):
        project = tmp_path / name
        project.mkdir()
        contract = project / "openapi.yaml"
        contract.write_bytes(source)
        results.append(generate(contract))
    assert results[0] == results[1] == generate(ROOT / "openapi.yaml")
    assert str(tmp_path).encode() not in results[0]
    assert str(ROOT).encode() not in results[0]
    assert b"timestamp:" not in results[0]
    assert b"from pydantic import" in results[0]


def test_check_never_changes_project_files(tmp_path: Path) -> None:
    source = (ROOT / "openapi.yaml").read_bytes()
    (tmp_path / "openapi.yaml").write_bytes(source)
    target = tmp_path / "generated" / "dto.py"
    assert main(["--check"], root=tmp_path) == 1
    assert not target.parent.exists()
    assert main([], root=tmp_path) == 0
    original = target.read_bytes()
    modified_at = target.stat().st_mtime_ns
    assert main(["--check"], root=tmp_path) == 0
    assert target.read_bytes() == original
    assert target.stat().st_mtime_ns == modified_at
    target.write_bytes(original + b"\n# outdated\n")
    outdated = target.read_bytes()
    modified_at = target.stat().st_mtime_ns
    assert main(["--check"], root=tmp_path) == 1
    assert target.read_bytes() == outdated
    assert target.stat().st_mtime_ns == modified_at
    assert (tmp_path / "openapi.yaml").read_bytes() == source


def test_generation_failure_preserves_saved_dto(tmp_path: Path) -> None:
    target = tmp_path / "generated" / "dto.py"
    target.parent.mkdir()
    target.write_bytes(b"# previously generated DTO\n")
    original = target.read_bytes()
    modified_at = target.stat().st_mtime_ns
    # Отсутствующий контракт и неверный YAML не затирают DTO.
    assert main([], root=tmp_path) == 1
    (tmp_path / "openapi.yaml").write_text("openapi: [\n", encoding="utf-8")
    assert main([], root=tmp_path) == 1
    assert main(["--check"], root=tmp_path) == 1
    assert target.read_bytes() == original
    assert target.stat().st_mtime_ns == modified_at


def test_generated_numeric_constraints_match_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "dto.py"
    target.write_bytes(generate(ROOT / "openapi.yaml"))
    spec = importlib.util.spec_from_file_location("dto_regression", target)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    contract = yaml.safe_load((ROOT / "openapi.yaml").read_text(encoding="utf-8"))
    for name, schema in contract["components"]["schemas"].items():
        for field, source in schema.get("properties", {}).items():
            if source.get("type") != "integer":
                continue
            generated = getattr(module, name).model_json_schema()["properties"][field]
            for bound in ("minimum", "maximum"):
                if bound in source:
                    assert generated[bound] == source[bound], (name, field, bound)
    portion = module.IngredientPortion
    for quantity in (0, 11, True, "1", 1.5, float("inf"), float("nan")):
        with pytest.raises(ValidationError):
            portion(ingredient_id="moon_dust", quantity=quantity)
    for quantity in (1, 10):
        assert (
            portion(ingredient_id="moon_dust", quantity=quantity).quantity == quantity
        )
