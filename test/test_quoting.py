import unittest

from telicent_labels import SecurityLabelBuilder, TelicentSecurityLabelsV2
from telicent_labels.security_labels import is_word, quote, quote_if_needed


class QuotingTestCase(unittest.TestCase):
    """Values that are not rdf-abac words are quoted; words are written exactly as before."""

    def test_words_are_unchanged(self):
        for word in ("telicent", "GBR", "Org_A", "org.b", "acme-corp", "nhs+trust", "x:y",
                     "urn:telicent:groups:role:doctor", "S", "_x", "a9c", "org1", "A9", "Société", "東京",
                     "urn:telicent:groups:g1"):
            self.assertTrue(is_word(word), word)
            self.assertEqual(quote_if_needed(word), word)

    def test_non_words_are_quoted(self):
        cases = {
            "Org Name": '"Org Name"',
            "a|b": '"a|b"',
            "a&b": '"a&b"',
            "org(1)": '"org(1)"',
            "k=v": '"k=v"',
            "a,b": '"a,b"',
            "1org": '"1org"',          # starts with a digit: read as a number then a word
            "a-": '"a-"',              # ends with a middle character
            "urn:x:": '"urn:x:"',
            "": '""',
            "org#1": '"org#1"',
            "a/b": '"a/b"',
            "*": '"*"',
            "!": '"!"',
            "true": '"true"',          # keywords are not words
            "false": '"false"',
            'a"b': '"a\\"b"',
            "a\\b": '"a\\\\b"',
            "a\nb": '"a\\nb"',
            "a\tb": '"a\\tb"',
            " org": '" org"',
        }
        for value, expected in cases.items():
            self.assertFalse(is_word(value), value)
            self.assertEqual(quote_if_needed(value), expected)
            self.assertEqual(quote(value), expected)

    def test_labels_quote_only_what_needs_it(self):
        orgs = TelicentSecurityLabelsV2.PERMITTED_ORGANISATIONS.value
        self.assertEqual(orgs.create_label("telicent"), "permitted_organisations=telicent")
        self.assertEqual(orgs.create_label("a|b"), 'permitted_organisations="a|b"')
        self.assertEqual(
            orgs.construct("telicent", "Org Name"),
            '(permitted_organisations=telicent|permitted_organisations="Org Name")',
        )
        cls = TelicentSecurityLabelsV2.CLASSIFICATION.value
        self.assertEqual(cls.construct("Top Secret"), 'classification="Top Secret"')

    def test_groups_are_quoted_when_not_words(self):
        ands = TelicentSecurityLabelsV2.AND_GROUPS.value
        ors = TelicentSecurityLabelsV2.OR_GROUPS.value
        self.assertEqual(ands.construct("urn:telicent:groups:g1"), "urn:telicent:groups:g1")
        # The URN grammar allows characters rdf-abac does not read in a bare word, such as = and ( ):
        # quoted, they are one attribute name.
        self.assertEqual(
            ands.construct("urn:telicent:groups:g1", "urn:telicent:groups:a=b"),
            'urn:telicent:groups:g1&"urn:telicent:groups:a=b"',
        )
        self.assertEqual(ors.construct("urn:telicent:groups:g1", "urn:telicent:groups:(x)"),
                         '(urn:telicent:groups:g1|"urn:telicent:groups:(x)")')

    def test_builder_output_for_an_existing_label_is_unchanged(self):
        built = (
            SecurityLabelBuilder()
            .add(TelicentSecurityLabelsV2.CLASSIFICATION.value, "S")
            .add_multiple(TelicentSecurityLabelsV2.PERMITTED_ORGANISATIONS.value, "telicent", "nhs")
            .add_multiple(TelicentSecurityLabelsV2.AND_GROUPS.value, "urn:x:g1")
            .build()
        )
        self.assertEqual(
            built, "(classification=S&(permitted_organisations=telicent|permitted_organisations=nhs)&urn:x:g1)"
        )

    def test_a_value_with_a_bar_is_one_value(self):
        built = (
            SecurityLabelBuilder()
            .add(TelicentSecurityLabelsV2.CLASSIFICATION.value, "S")
            .add_multiple(TelicentSecurityLabelsV2.PERMITTED_ORGANISATIONS.value, "a|b")
            .build()
        )
        # Before: (classification=S&(permitted_organisations=a|b)), which rdf-abac reads as
        # "organisation a, or any user holding attribute b".
        self.assertEqual(built, '(classification=S&(permitted_organisations="a|b"))')
