from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str, version: str = "v1") -> str:
    """Load a versioned prompt file (prompts are files, never inline strings)."""
    return (_PROMPTS_DIR / name / f"{version}.txt").read_text(encoding="utf-8")
