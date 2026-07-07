"""Unit tests for OIDC group → role mapping."""

import os

import pytest

from app.services.oidc_roles import (
    email_domain_allowed,
    extract_claim_values,
    parse_oidc_role_map,
    resolve_role_from_claims,
)


def test_parse_oidc_role_map_valid():
    raw = '{"Securi-Admins": "admin", "Securi-Analysts": "analyst", "Bad": "superuser"}'
    assert parse_oidc_role_map(raw) == {
        "Securi-Admins": "admin",
        "Securi-Analysts": "analyst",
    }


def test_parse_oidc_role_map_invalid_json():
    assert parse_oidc_role_map("{not json") == {}


def test_extract_claim_values_list_and_string():
    assert extract_claim_values({"groups": ["A", "B"]}, "groups") == ["A", "B"]
    assert extract_claim_values({"roles": "Admin"}, "roles") == ["Admin"]
    assert extract_claim_values({}, "groups") == []


def test_resolve_role_picks_highest_privilege(monkeypatch):
    monkeypatch.setenv(
        "OIDC_ROLE_MAP",
        '{"Securi-Admins":"admin","Securi-Analysts":"analyst","Securi-Viewers":"viewer"}',
    )
    from app.config import settings

    settings.oidc_role_map = os.environ["OIDC_ROLE_MAP"]
    settings.oidc_groups_claim = "groups"
    settings.oidc_default_role = "viewer"

    role = resolve_role_from_claims({"groups": ["Securi-Analysts", "Securi-Admins"]})
    assert role == "admin"


def test_resolve_role_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("OIDC_ROLE_MAP", '{"Known":"analyst"}')
    from app.config import settings

    settings.oidc_role_map = os.environ["OIDC_ROLE_MAP"]
    settings.oidc_groups_claim = "groups"
    settings.oidc_default_role = "viewer"

    assert resolve_role_from_claims({"groups": ["Unknown"]}) == "viewer"


def test_email_domain_allowed_empty_means_all(monkeypatch):
    from app.config import settings

    settings.oidc_allowed_email_domains = ""
    assert email_domain_allowed("user@anywhere.com") is True


def test_email_domain_allowed_restricts(monkeypatch):
    from app.config import settings

    settings.oidc_allowed_email_domains = "company.com, partner.org"
    assert email_domain_allowed("user@company.com") is True
    assert email_domain_allowed("user@evil.com") is False
