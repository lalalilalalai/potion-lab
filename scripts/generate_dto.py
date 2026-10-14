"""Воспроизводимая генерация Pydantic v2 DTO из исходного OpenAPI."""

import argparse
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
FORMAT_CONFIG = """\
[tool.black]
line-length = 88
target-version = ["py312"]
[tool.isort]
profile = "black"
line_length = 88
py_version = 312
"""


def generate(contract: Path) -> bytes:
    """Генерировать во временном каталоге с постоянными именами файлов."""
    source = contract.read_bytes()
    with TemporaryDirectory(prefix="potion-lab-dto-") as directory:
        workspace = Path(directory)
        (workspace / "openapi.yaml").write_bytes(source)
        (workspace / "pyproject.toml").write_text(FORMAT_CONFIG, encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "datamodel_code_generator",
                "--input",
                "openapi.yaml",
                "--input-file-type",
                "openapi",
                "--output",
                "dto.py",
                "--output-model-type",
                "pydantic_v2.BaseModel",
                "--target-python-version",
                "3.12",
                "--disable-timestamp",
                "--use-standard-collections",
                "--use-union-operator",
                "--strict-types",
                "int",
                "--use-double-quotes",
                "--formatters",
                "black",
                "isort",
            ],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            reason = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"Генератор завершился с ошибкой: {reason}")
        return (workspace / "dto.py").read_bytes()


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Проверить DTO без изменения файлов"
    )
    args = parser.parse_args(argv)
    target = root / "generated" / "dto.py"
    try:
        content = generate(root / "openapi.yaml")
        if args.check:
            if not target.is_file() or target.read_bytes() != content:
                print(
                    "DTO отсутствуют или устарели. Выполните: "
                    "python scripts/generate_dto.py",
                    file=sys.stderr,
                )
                return 1
            print("DTO актуальны; файлы не изменены.")
            return 0
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    except (OSError, RuntimeError) as error:
        print(f"Не удалось сгенерировать DTO: {error}", file=sys.stderr)
        return 1
    print("DTO записаны в generated/dto.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
