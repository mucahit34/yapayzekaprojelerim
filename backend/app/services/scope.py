"""Kapsam kontrolü: aktif test / dış hedefe trafik gerektiren her işlem,
bu modülden geçerek projenin `scope_definition` alanına karşı doğrulanmalıdır.

`scope_definition` beklenen biçim:
{
    "in_scope": ["acme-portal.example", "*.acme.example", "203.0.113.0/24"],
    "out_of_scope": ["staging-internal.acme.example"]
}

Kurallar:
- Açık dışlama (`out_of_scope`) her zaman kapsam dahiline önceliklidir.
- Domain girişleri tam eşleşme veya `*.` ile başlayan alt alan adı eşleşmesi
  destekler.
- IP/CIDR girişleri tek IP veya ağ aralığı olarak değerlendirilir.
- `in_scope` boşsa veya tanımsızsa, hiçbir hedef kapsamda sayılmaz
  (varsayılan: reddet — fail closed).
"""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass


@dataclass(frozen=True)
class ScopeDecision:
    allowed: bool
    reason: str


def _is_ip_like(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return "/" in value


def _domain_matches(pattern: str, identifier: str) -> bool:
    pattern = pattern.strip().lower()
    identifier = identifier.strip().lower()
    if pattern == identifier:
        return True
    if pattern.startswith("*."):
        suffix = pattern[1:]  # ".acme.example"
        return identifier.endswith(suffix) and identifier != suffix.lstrip(".")
    return False


def _ip_matches(pattern: str, identifier: str) -> bool:
    try:
        network = ipaddress.ip_network(pattern, strict=False)
        address = ipaddress.ip_address(identifier)
    except ValueError:
        return False
    return address in network


def _entry_matches(pattern: str, identifier: str) -> bool:
    if _is_ip_like(pattern) and _is_ip_like(identifier):
        return _ip_matches(pattern, identifier)
    return _domain_matches(pattern, identifier)


def check_scope(scope_definition: dict | None, identifier: str) -> ScopeDecision:
    """Bir hedefin (domain/IP/CIDR) proje kapsamında olup olmadığını belirler.

    Fail-closed: scope_definition boşsa veya in_scope tanımlı değilse
    her zaman reddedilir.
    """
    identifier = (identifier or "").strip()
    if not identifier:
        return ScopeDecision(False, "Hedef tanımlayıcı boş olamaz.")

    scope_definition = scope_definition or {}
    out_of_scope = scope_definition.get("out_of_scope") or []
    in_scope = scope_definition.get("in_scope") or []

    for pattern in out_of_scope:
        if _entry_matches(pattern, identifier):
            return ScopeDecision(
                False, f"'{identifier}' açıkça kapsam dışı olarak işaretlenmiş ({pattern})."
            )

    if not in_scope:
        return ScopeDecision(
            False, "Proje için izinli kapsam (in_scope) tanımlanmamış; varsayılan reddet."
        )

    for pattern in in_scope:
        if _entry_matches(pattern, identifier):
            return ScopeDecision(True, f"'{identifier}' kapsam kuralıyla eşleşti ({pattern}).")

    return ScopeDecision(False, f"'{identifier}' hiçbir izinli kapsam kuralıyla eşleşmedi.")
