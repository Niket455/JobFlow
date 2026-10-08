from app.services.url_canonicalizer import canonicalize


def test_lowercases_host_drops_tracking_and_fragment() -> None:
    url = "https://Jobs.Example.com/Roles/1/?utm_source=x&gclid=y&a=1#frag"
    assert canonicalize(url) == "https://jobs.example.com/Roles/1?a=1"


def test_sorts_query_parameters() -> None:
    assert canonicalize("https://e.com/x?b=2&a=1") == "https://e.com/x?a=1&b=2"


def test_drops_default_ports() -> None:
    assert canonicalize("https://e.com:443/x") == "https://e.com/x"
    assert canonicalize("http://e.com:80/x") == "http://e.com/x"


def test_keeps_non_default_port() -> None:
    assert canonicalize("https://e.com:8443/x") == "https://e.com:8443/x"


def test_strips_trailing_slash_but_keeps_root() -> None:
    assert canonicalize("https://e.com/a/b/") == "https://e.com/a/b"
    assert canonicalize("https://e.com/") == "https://e.com/"
