"""Student eligibility for the sponsored Standard tier.

Verification is by **institutional email domain plus country**, not by uploaded
identity documents. A national ID scan is biometric-grade personal data: storing
it creates obligations under the Uganda Data Protection and Privacy Act, the
Nigeria NDPA, POPIA and the GDPR, and a breach would expose the students this
tier exists to help. A domain that only a university can issue proves enrolment
just as well for granting a free tier, and the failure mode (a wrongly granted
subscription) is far cheaper than the failure mode of an ID database.

Country resolution is best-effort and never authoritative: it reads a
user-declared country first, then the ``CF-IPCountry`` / ``X-Forwarded-For``
style headers a proxy may add. Both are spoofable, which is acceptable because
the downside is a discounted subscription rather than access to someone's data.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Set, Tuple

# ─── Eligible regions ─────────────────────────────────────────────────
# African Union member states plus lower/lower-middle income countries in Asia,
# Latin America and Oceania (World Bank income classification).
AFRICAN_COUNTRIES: Dict[str, str] = {
    "DZ": "Algeria", "AO": "Angola", "BJ": "Benin", "BW": "Botswana",
    "BF": "Burkina Faso", "BI": "Burundi", "CV": "Cabo Verde", "CM": "Cameroon",
    "CF": "Central African Republic", "TD": "Chad", "KM": "Comoros",
    "CG": "Congo", "CD": "DR Congo", "CI": "Côte d'Ivoire", "DJ": "Djibouti",
    "EG": "Egypt", "GQ": "Equatorial Guinea", "ER": "Eritrea", "SZ": "Eswatini",
    "ET": "Ethiopia", "GA": "Gabon", "GM": "Gambia", "GH": "Ghana",
    "GN": "Guinea", "GW": "Guinea-Bissau", "KE": "Kenya", "LS": "Lesotho",
    "LR": "Liberia", "LY": "Libya", "MG": "Madagascar", "MW": "Malawi",
    "ML": "Mali", "MR": "Mauritania", "MU": "Mauritius", "MA": "Morocco",
    "MZ": "Mozambique", "NA": "Namibia", "NE": "Niger", "NG": "Nigeria",
    "RW": "Rwanda", "ST": "São Tomé and Príncipe", "SN": "Senegal",
    "SC": "Seychelles", "SL": "Sierra Leone", "SO": "Somalia",
    "ZA": "South Africa", "SS": "South Sudan", "SD": "Sudan", "TZ": "Tanzania",
    "TG": "Togo", "TN": "Tunisia", "UG": "Uganda", "ZM": "Zambia",
    "ZW": "Zimbabwe",
}

OTHER_ELIGIBLE_COUNTRIES: Dict[str, str] = {
    "AF": "Afghanistan", "BD": "Bangladesh", "BT": "Bhutan", "BO": "Bolivia",
    "KH": "Cambodia", "HT": "Haiti", "HN": "Honduras", "ID": "Indonesia",
    "IN": "India", "KG": "Kyrgyzstan", "LA": "Laos", "MM": "Myanmar",
    "NP": "Nepal", "NI": "Nicaragua", "PK": "Pakistan", "PG": "Papua New Guinea",
    "PH": "Philippines", "LK": "Sri Lanka", "SB": "Solomon Islands",
    "TJ": "Tajikistan", "TL": "Timor-Leste", "UZ": "Uzbekistan",
    "VN": "Vietnam", "VU": "Vanuatu", "YE": "Yemen",
}

ELIGIBLE_COUNTRIES: Dict[str, str] = {**AFRICAN_COUNTRIES, **OTHER_ELIGIBLE_COUNTRIES}

# ─── Academic domains ─────────────────────────────────────────────────
# Second-level academic suffixes (…​.ac.ug, …​.edu.ng) plus the bare TLDs that
# are restricted to accredited institutions.
ACADEMIC_SUFFIX_PATTERN = re.compile(
    r"\.(?:ac|edu|edu-ac|sch)\.[a-z]{2}$|\.(?:edu|ac)$|\.edu\.[a-z]{2,3}$"
)

# Domains that look academic but are open to anyone.
NON_INSTITUTIONAL_DOMAINS: Set[str] = {
    "gmail.com", "googlemail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "live.com", "icloud.com", "proton.me", "protonmail.com", "aol.com",
    "mail.com", "zoho.com", "yandex.com", "edu.email",
}

COUNTRY_HEADERS = ("CF-IPCountry", "X-Vercel-IP-Country", "X-Country-Code", "X-Geo-Country")


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    reason: str
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    institution_domain: Optional[str] = None

    def __bool__(self) -> bool:
        return self.eligible


def email_domain(email: str) -> str:
    local, at, domain = (email or "").strip().lower().rpartition("@")
    return domain if at and local else ""


def is_institutional_email(email: str) -> bool:
    """True for a domain only an accredited institution can issue."""
    domain = email_domain(email)
    if not domain or domain in NON_INSTITUTIONAL_DOMAINS:
        return False
    return bool(ACADEMIC_SUFFIX_PATTERN.search(domain))


def country_from_domain(email: str) -> Optional[str]:
    """ISO code implied by an academic domain (``mak.ac.ug`` → ``UG``)."""
    domain = email_domain(email)
    if not domain or "." not in domain:
        return None
    tld = domain.rpartition(".")[2].upper()
    return tld if len(tld) == 2 else None


def resolve_country(
    declared: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    email: Optional[str] = None,
) -> Optional[str]:
    """Best-effort ISO-3166 alpha-2 code, preferring what the user declared."""
    if declared and len(declared.strip()) == 2:
        return declared.strip().upper()

    for key, value in (headers or {}).items():
        if key.lower() in {header.lower() for header in COUNTRY_HEADERS} and value:
            code = value.strip().upper()
            if len(code) == 2 and code != "XX":
                return code

    return country_from_domain(email or "")


def country_is_eligible(code: Optional[str]) -> bool:
    return bool(code) and code.upper() in ELIGIBLE_COUNTRIES


def evaluate(
    email: str,
    declared_country: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> EligibilityResult:
    """Decide whether an account qualifies for the sponsored Standard tier."""
    domain = email_domain(email)
    country = resolve_country(declared_country, headers, email)
    country_name = ELIGIBLE_COUNTRIES.get((country or "").upper())

    if not domain:
        return EligibilityResult(False, "Enter a valid email address.")

    if not is_institutional_email(email):
        return EligibilityResult(
            False,
            "Use your university email (for example name@student.mak.ac.ug). "
            "Personal addresses can't be verified.",
            country_code=country,
            country_name=country_name,
            institution_domain=domain,
        )

    if not country_is_eligible(country):
        return EligibilityResult(
            False,
            "Sponsored access currently covers African Union member states and "
            "qualifying developing countries. Your institution's country was "
            f"detected as {country or 'unknown'}.",
            country_code=country,
            country_name=country_name,
            institution_domain=domain,
        )

    return EligibilityResult(
        True,
        f"Verified {domain} in {country_name} — Standard tier granted free of charge.",
        country_code=country,
        country_name=country_name,
        institution_domain=domain,
    )


def country_choices() -> Tuple[Tuple[str, str], ...]:
    """``(code, name)`` pairs for a country selector, alphabetical by name."""
    return tuple(sorted(((code, name) for code, name in ELIGIBLE_COUNTRIES.items()), key=lambda x: x[1]))
