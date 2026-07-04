import importlib.metadata
import tomllib
from pathlib import Path
from typing import Final

APP_NAME: Final = "transical"

try:
    _version = importlib.metadata.version(APP_NAME)
except importlib.metadata.PackageNotFoundError:
    match tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"]:
        case str(version):
            _version = version
        case _:
            raise ValueError("Invalid project.version")

VERSION: Final = _version
ORG_DOMAIN: Final = "dandelion.computer"
APP_DOMAIN: Final = APP_NAME + "." + ORG_DOMAIN
APP_ID: Final = ".".join(reversed(APP_DOMAIN.split(".")))
