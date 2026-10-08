from app.services.dedupe import content_hash, normalized_company_name


def test_normalized_company_name_strips_suffixes_and_punctuation() -> None:
    assert normalized_company_name("Acme, Inc.") == "acme"
    assert normalized_company_name("Acme Pvt. Ltd.") == "acme"
    assert normalized_company_name(None) == ""


def test_content_hash_ignores_company_suffix_and_case() -> None:
    assert content_hash("Data Engineer", "Acme Inc", "Bengaluru") == content_hash(
        "data engineer", "Acme", "bengaluru"
    )


def test_content_hash_differs_by_location() -> None:
    assert content_hash("DE", "Acme", "Remote") != content_hash("DE", "Acme", "Bengaluru")
