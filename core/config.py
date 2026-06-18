"""Load settings.toml."""
import pathlib

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - older interpreters
    import tomli as tomllib

_CFG_PATH = pathlib.Path(__file__).parent.parent / "config" / "settings.toml"


def load() -> dict:
    with open(_CFG_PATH, "rb") as f:
        return tomllib.load(f)


CFG = load()
