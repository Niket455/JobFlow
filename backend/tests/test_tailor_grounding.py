from app.services.tailor_grounding import (
    AppliedChange,
    apply_changes,
    get_text,
    is_grounded,
    path_exists,
)


def test_is_grounded_ignores_case_and_punctuation() -> None:
    assert is_grounded("Python, SQL", "Jane Doe python sql") is True


def test_is_grounded_false_for_missing_empty_or_short() -> None:
    assert is_grounded("Kubernetes", "Jane Doe Python SQL") is False
    assert is_grounded(None, "anything") is False
    assert is_grounded("", "anything") is False
    assert is_grounded("a", "a b c") is False


def test_get_text_navigates_nested_paths() -> None:
    profile = {"summary": "x", "work_history": [{"description": "y"}], "skills": ["Python"]}
    assert get_text(profile, "summary") == "x"
    assert get_text(profile, "work_history.0.description") == "y"
    assert get_text(profile, "skills.0") == "Python"
    assert get_text(profile, "skills.3") is None
    assert get_text(profile, "missing") is None


def test_apply_changes_sets_paths_and_skips_unknown() -> None:
    profile = {"summary": "old", "skills": ["a", "b"]}
    result = apply_changes(
        profile,
        [
            AppliedChange("summary", "new"),
            AppliedChange("skills.1", "c"),
            AppliedChange("nope", "x"),
        ],
    )
    assert result["summary"] == "new"
    assert result["skills"] == ["a", "c"]
    assert profile["summary"] == "old"


def test_path_exists() -> None:
    assert path_exists({"a": {"b": 1}}, "a.b") is True
    assert path_exists({"a": {}}, "a.b") is False
