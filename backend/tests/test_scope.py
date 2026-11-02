from app.services.scope import check_scope


def test_no_scope_definition_denies_by_default():
    assert check_scope(None, "example.com").allowed is False
    assert check_scope({}, "example.com").allowed is False


def test_exact_domain_match_allowed():
    decision = check_scope({"in_scope": ["acme-portal.example"]}, "acme-portal.example")
    assert decision.allowed is True


def test_wildcard_subdomain_match():
    scope = {"in_scope": ["*.acme.example"]}
    assert check_scope(scope, "api.acme.example").allowed is True
    assert check_scope(scope, "acme.example").allowed is False  # kök alan ayrı eşleşmeli
    assert check_scope(scope, "api.evil.example").allowed is False


def test_cidr_match():
    scope = {"in_scope": ["203.0.113.0/24"]}
    assert check_scope(scope, "203.0.113.42").allowed is True
    assert check_scope(scope, "198.51.100.1").allowed is False


def test_out_of_scope_overrides_in_scope():
    scope = {"in_scope": ["*.acme.example"], "out_of_scope": ["staging.acme.example"]}
    decision = check_scope(scope, "staging.acme.example")
    assert decision.allowed is False
    assert "kapsam dışı" in decision.reason


def test_unmatched_identifier_denied():
    scope = {"in_scope": ["acme-portal.example"]}
    assert check_scope(scope, "unrelated.example").allowed is False


def test_empty_identifier_denied():
    assert check_scope({"in_scope": ["acme.example"]}, "  ").allowed is False
