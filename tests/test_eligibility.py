"""Tests for modules.eligibility — institutional email + country verification."""
from modules.eligibility import (
    AFRICAN_COUNTRIES,
    ELIGIBLE_COUNTRIES,
    country_choices,
    country_from_domain,
    country_is_eligible,
    email_domain,
    evaluate,
    is_institutional_email,
    resolve_country,
)


class TestDomainParsing:
    def test_extracts_the_domain(self):
        assert email_domain("Chris@Student.MAK.ac.ug") == "student.mak.ac.ug"

    def test_handles_missing_domain(self):
        assert email_domain("chris") == ""
        assert email_domain("") == ""
        assert email_domain(None) == ""


class TestInstitutionalEmail:
    def test_accepts_second_level_academic_domains(self):
        for email in (
            "a@student.mak.ac.ug",
            "b@unilag.edu.ng",
            "c@uct.ac.za",
            "d@iitb.ac.in",
        ):
            assert is_institutional_email(email), email

    def test_accepts_bare_edu(self):
        assert is_institutional_email("a@mit.edu")

    def test_rejects_free_mail_providers(self):
        for email in ("a@gmail.com", "b@yahoo.com", "c@outlook.com", "d@proton.me"):
            assert not is_institutional_email(email), email

    def test_rejects_ordinary_company_domains(self):
        assert not is_institutional_email("a@acme.com")
        assert not is_institutional_email("a@education.org")

    def test_rejects_lookalike_domains(self):
        assert not is_institutional_email("a@edu.email")
        assert not is_institutional_email("a@notreally-edu.com")

    def test_rejects_empty_input(self):
        assert not is_institutional_email("")


class TestCountryResolution:
    def test_infers_country_from_an_academic_domain(self):
        assert country_from_domain("a@student.mak.ac.ug") == "UG"
        assert country_from_domain("a@unilag.edu.ng") == "NG"

    def test_no_country_from_a_generic_tld(self):
        assert country_from_domain("a@mit.edu") is None

    def test_declared_country_wins(self):
        assert resolve_country("ke", {"CF-IPCountry": "US"}, "a@mak.ac.ug") == "KE"

    def test_headers_are_used_when_nothing_is_declared(self):
        assert resolve_country(None, {"CF-IPCountry": "za"}, None) == "ZA"

    def test_header_lookup_is_case_insensitive(self):
        assert resolve_country(None, {"cf-ipcountry": "NG"}, None) == "NG"

    def test_placeholder_headers_are_ignored(self):
        assert resolve_country(None, {"CF-IPCountry": "XX"}, "a@mak.ac.ug") == "UG"

    def test_falls_back_to_the_email_domain(self):
        assert resolve_country(None, None, "a@uct.ac.za") == "ZA"

    def test_returns_none_when_nothing_is_known(self):
        assert resolve_country(None, None, "a@gmail.com") is None

    def test_eligibility_list_covers_the_african_union(self):
        assert AFRICAN_COUNTRIES["UG"] == "Uganda"
        assert len(AFRICAN_COUNTRIES) >= 50
        assert all(code in ELIGIBLE_COUNTRIES for code in AFRICAN_COUNTRIES)

    def test_country_eligibility(self):
        assert country_is_eligible("UG")
        assert country_is_eligible("ng")
        assert not country_is_eligible("US")
        assert not country_is_eligible(None)


class TestEvaluate:
    def test_verified_student_is_eligible(self):
        result = evaluate("chris@student.mak.ac.ug")
        assert result
        assert result.country_code == "UG"
        assert result.country_name == "Uganda"
        assert result.institution_domain == "student.mak.ac.ug"
        assert "Standard tier" in result.reason

    def test_personal_email_is_rejected(self):
        result = evaluate("chris@gmail.com", "UG")
        assert not result
        assert "university email" in result.reason

    def test_ineligible_country_is_rejected(self):
        result = evaluate("chris@mit.edu", "US")
        assert not result
        assert "African Union" in result.reason

    def test_declared_country_can_supply_a_missing_one(self):
        assert evaluate("chris@mit.edu", "KE")

    def test_proxy_headers_can_supply_the_country(self):
        assert evaluate("chris@mit.edu", None, {"CF-IPCountry": "GH"})

    def test_empty_email_is_rejected(self):
        result = evaluate("")
        assert not result
        assert "valid email" in result.reason

    def test_result_is_falsey_when_ineligible(self):
        assert not bool(evaluate("chris@gmail.com"))


class TestCountryChoices:
    def test_choices_are_alphabetical_by_name(self):
        names = [name for _, name in country_choices()]
        assert names == sorted(names)

    def test_choices_cover_every_eligible_country(self):
        assert len(country_choices()) == len(ELIGIBLE_COUNTRIES)
