"""Load settings.toml."""
import tomllib, pathlib

_CFG_PATH = pathlib.Path(__file__).parent.parent / "config" / "settings.toml"

def load() -> dict:
    with open(_CFG_PATH, "rb") as f:
        return tomllib.load(f)

CFG = load()
