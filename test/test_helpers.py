import re
import unittest

from telicent_labels.helpers import TELICENT_URN_BASE, generate_urn, is_valid_urn

# An independent RFC 8141 `assigned-name` grammar, transcribed directly from the
# spec, used to assert that generated URNs are compliant. Kept separate from the
# implementation's own regex on purpose — it validates the *whole* URN structure
# (scheme / NID / NSS), not just the group-name segment.
#   assigned-name = "urn" ":" NID ":" NSS
#   NID           = alphanum 0*30(ldh) alphanum          ; 2-32 chars
#   NSS           = pchar *(pchar / "/")
#   pchar         = unreserved / pct-encoded / sub-delims / ":" / "@"
#   unreserved    = ALPHA / DIGIT / "-" / "." / "_" / "~"
#   sub-delims    = "!" / "$" / "&" / "'" / "(" / ")" / "*" / "+" / "," / ";" / "="
_ALPHANUM = r"[A-Za-z0-9]"
_NID = rf"{_ALPHANUM}[A-Za-z0-9-]{{0,30}}{_ALPHANUM}"
_PCT = r"%[0-9A-Fa-f]{2}"
_PCHAR = rf"(?:[A-Za-z0-9\-._~!$&'()*+,;=:@]|{_PCT})"
_NSS = rf"{_PCHAR}(?:{_PCHAR}|/)*"
_RFC_8141_RE = re.compile(rf"^urn:{_NID}:{_NSS}$", re.IGNORECASE)


def is_rfc_8141_compliant(urn: str) -> bool:
    match = _RFC_8141_RE.fullmatch(urn)
    # "urn" is a reserved NID and not permitted.
    return match is not None and urn.split(":", 2)[1].lower() != "urn"


class IsValidUrnTestCase(unittest.TestCase):
    """`is_valid_urn` recognises Telicent group URNs only: the exact
    `urn:telicent:groups:` prefix followed by a non-empty, URN-safe segment."""

    def test_accepts_telicent_group_urns(self):
        valid = [
            "urn:telicent:groups:developer",
            "urn:telicent:groups:ab",
            "urn:telicent:groups:a-b_c.d",   # unreserved punctuation
            "urn:telicent:groups:role@team",  # ':@' style pchar
            "urn:telicent:groups:a%2Fb",      # percent-encoded octet
        ]
        for urn in valid:
            with self.subTest(urn=urn):
                self.assertTrue(is_valid_urn(urn))

    def test_rejects_urns_from_other_namespaces(self):
        invalid = [
            "urn:example:foo:bar",
            "urn:telicent:datasets:x",  # right authority, wrong collection
            "urn:ab:x",
            "urn:urn:foo",
            "telicent:groups:x",  # missing scheme
        ]
        for urn in invalid:
            with self.subTest(urn=urn):
                self.assertFalse(is_valid_urn(urn))

    def test_base_prefix_is_case_sensitive(self):
        self.assertFalse(is_valid_urn("URN:TELICENT:GROUPS:Dev"))

    def test_rejects_empty_segment(self):
        self.assertFalse(is_valid_urn("urn:telicent:groups:"))

    def test_rejects_segment_with_disallowed_characters(self):
        invalid = [
            "urn:telicent:groups:a~b",       # tilde is not permitted
            "urn:telicent:groups:dev?+r",    # RFC r-component not permitted
            "urn:telicent:groups:dev#frag",  # RFC f-component not permitted
            "urn:telicent:groups:bad<>name",
            "urn:telicent:groups:has space",
        ]
        for urn in invalid:
            with self.subTest(urn=urn):
                self.assertFalse(is_valid_urn(urn))

    def test_rejects_empty_string(self):
        self.assertFalse(is_valid_urn(""))

    def test_none_is_not_valid(self):
        self.assertFalse(is_valid_urn(None))


class GenerateUrnTestCase(unittest.TestCase):
    def test_prefixes_with_telicent_base(self):
        self.assertEqual(generate_urn("developer"), f"{TELICENT_URN_BASE}developer")
        self.assertEqual(generate_urn("developer"), "urn:telicent:groups:developer")

    def test_whitespace_is_replaced_with_hyphens(self):
        self.assertEqual(
            generate_urn("data science"), "urn:telicent:groups:data-science"
        )

    def test_leading_and_trailing_whitespace_is_stripped(self):
        self.assertEqual(generate_urn("  dev  "), "urn:telicent:groups:dev")

    def test_each_internal_whitespace_char_becomes_a_hyphen(self):
        self.assertEqual(generate_urn("a  b"), "urn:telicent:groups:a--b")
        self.assertEqual(generate_urn("a\tb"), "urn:telicent:groups:a-b")

    def test_unreserved_punctuation_is_preserved(self):
        self.assertEqual(generate_urn("under_score"), "urn:telicent:groups:under_score")
        self.assertEqual(generate_urn("dot.name"), "urn:telicent:groups:dot.name")

    def test_output_is_always_a_valid_telicent_urn(self):
        for name in ("developer", "data science", "team.alpha", "role_1"):
            with self.subTest(name=name):
                self.assertTrue(is_valid_urn(generate_urn(name)))

    def test_none_raises(self):
        with self.assertRaises(ValueError) as ctx:
            generate_urn(None)
        self.assertIn("cannot be empty", str(ctx.exception))

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError) as ctx:
            generate_urn("")
        self.assertIn("cannot be empty", str(ctx.exception))

    def test_whitespace_only_raises(self):
        with self.assertRaises(ValueError) as ctx:
            generate_urn("   ")
        self.assertIn("cannot be empty", str(ctx.exception))

    def test_invalid_characters_raise_with_original_name(self):
        with self.assertRaises(ValueError) as ctx:
            generate_urn("bad<>name")
        self.assertIn("bad<>name", str(ctx.exception))
        self.assertIn("invalid characters", str(ctx.exception))

    def test_disallowed_punctuation_raises(self):
        # Characters outside the URN-safe set (e.g. tilde) are now rejected.
        with self.assertRaises(ValueError):
            generate_urn("team~x")


class Rfc8141ComplianceTestCase(unittest.TestCase):
    """Guard: every URN this module produces must satisfy RFC 8141. The
    implementation restricts its charset to a strict subset of RFC 8141
    `pchar`, so this should hold — and will fail loudly if that subset is ever
    widened past the spec."""

    def test_self_check_of_the_rfc_matcher(self):
        # Sanity-check the reference matcher itself before relying on it.
        self.assertTrue(is_rfc_8141_compliant("urn:telicent:groups:developer"))
        self.assertTrue(is_rfc_8141_compliant("urn:example:a:b"))
        self.assertFalse(is_rfc_8141_compliant("urn:urn:foo"))       # reserved NID
        self.assertFalse(is_rfc_8141_compliant("urn:a:x"))           # NID too short
        self.assertFalse(is_rfc_8141_compliant("telicent:groups:x"))  # no scheme
        self.assertFalse(is_rfc_8141_compliant("urn:telicent:"))     # empty NSS

    def test_base_prefix_is_rfc_8141_compliant(self):
        # `urn:telicent:groups:X` has NID "telicent" and NSS "groups:X".
        self.assertTrue(is_rfc_8141_compliant(f"{TELICENT_URN_BASE}x"))

    def test_generated_urns_are_rfc_8141_compliant(self):
        names = [
            "developer",
            "data science",
            "team.alpha",
            "role_1",
            "a-b",
            "grp(1)",
            "a+b,c;d=e",
            "user@team",
            "quote's",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertTrue(is_rfc_8141_compliant(generate_urn(name)))

    def test_anything_is_valid_urn_accepts_is_also_rfc_8141_compliant(self):
        accepted = [
            "urn:telicent:groups:developer",
            "urn:telicent:groups:role@team",
            "urn:telicent:groups:a%2Fb",
            "urn:telicent:groups:a-b_c.d",
        ]
        for urn in accepted:
            with self.subTest(urn=urn):
                self.assertTrue(is_valid_urn(urn))
                self.assertTrue(is_rfc_8141_compliant(urn))


if __name__ == "__main__":
    unittest.main()
