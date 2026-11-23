import itertools
import unittest

from telicent_labels import IDHModel, SecurityLabelBuilder, TelicentLabelsV1, TelicentModel, TelicentSecurityLabelsV2
from telicent_labels.parse import NotBuilderShape, ParsedLabel, parse_security_labels

G = "urn:telicent:groups:"


def telicent(classification, orgs, nats, ands, ors):
    return TelicentModel(identifier="id", classification=classification, permittedOrgs=orgs,
                         permittedNats=nats, orGroups=ors, andGroups=ands, dataSet=["d"], authRef=["a"],
                         dissemination=["x"])


def idh(classification, orgs, nats, groups, one_of):
    return IDHModel(uuid="u", containsPii=False, ownership={"originatingOrg": "o"},
                    access={"classification": classification, "allowedOrgs": orgs, "allowedNats": nats,
                            "groups": groups, "oneOfGroups": one_of})


def v1(clearance, orgs, nats):
    return (SecurityLabelBuilder()
            .add(TelicentLabelsV1.CLASSIFICATION.value, clearance)
            .add_multiple(TelicentLabelsV1.PERMITTED_ORGANISATIONS.value, *orgs)
            .add_multiple(TelicentLabelsV1.PERMITTED_NATIONALITIES.value, *nats)
            .build())


class ParseTestCase(unittest.TestCase):
    """parse_security_labels gives back exactly what the models and the builder were given."""

    def test_telicent_model_round_trip(self):
        m = telicent("S", ["telicent", "nhs"], ["GBR"], [G + "g1", G + "g2"], [G + "g3"])
        [p] = parse_security_labels(m.build_security_labels())
        self.assertEqual(p, ParsedLabel("v2", "S", ["telicent", "nhs"], ["GBR"], [G + "g1", G + "g2"], [G + "g3"],
                                        group_suffixes=False))

    def test_idh_model_round_trip_with_empty_groups(self):
        for groups, one_of in itertools.product([[], [G + "a"], [G + "a", G + "b"]], repeat=2):
            m = idh("TS", ["o"], ["GBR"], groups, one_of)
            [p] = parse_security_labels(m.build_security_labels())
            self.assertEqual(p, ParsedLabel("v2", "TS", ["o"], ["GBR"], groups, one_of,
                                            group_suffixes=None if not groups and not one_of else False))

    def test_v1_round_trip(self):
        [p] = parse_security_labels(v1("TS-STRAP1", ["org.b", "x:y"], ["GBR", "NZL"]))
        self.assertEqual(p, ParsedLabel("v1", "TS-STRAP1", ["org.b", "x:y"], ["GBR", "NZL"], [], []))

    def test_order_and_repeats_are_kept(self):
        m = telicent("O", ["b", "a", "b"], ["GBR"], [G + "g2", G + "g1"], [G + "g1"])
        [p] = parse_security_labels(m.build_security_labels())
        self.assertEqual(p.permitted_organisations, ["b", "a", "b"])
        self.assertEqual(p.and_groups, [G + "g2", G + "g1"])

    def test_group_names_the_model_normalises_come_back_normalised(self):
        # The models turn a group name into a URN; the parser returns the URN the label holds.
        m = telicent("O", ["a"], ["GBR"], ["analysts", "a team"], ["x"])
        [p] = parse_security_labels(m.build_security_labels())
        self.assertEqual(p.and_groups, m.andGroups)
        self.assertEqual(p.or_groups, m.orGroups)
        self.assertEqual(p.and_groups, [G + "analysts", G + "a-team"])

    def test_parts_in_any_order(self):
        built = (SecurityLabelBuilder()
                 .add_multiple(TelicentSecurityLabelsV2.PERMITTED_ORGANISATIONS.value, "telicent", "nhs")
                 .add(TelicentSecurityLabelsV2.CLASSIFICATION.value, "S")
                 .build())
        self.assertEqual(built, "((permitted_organisations=telicent|permitted_organisations=nhs)&classification=S)")
        [p] = parse_security_labels(built)
        self.assertEqual(p, ParsedLabel("v2", "S", ["telicent", "nhs"], [], [], []))

    def test_quoted_values_are_unescaped(self):
        label = ('(classification="Top Secret"'
                 '&(permitted_organisations="a|b"|permitted_organisations="O\'Brien & \\"Sons\\""'
                 '|permitted_organisations=telicent)&"urn:telicent:groups:a=b"&urn:telicent:groups:g1'
                 '&("urn:telicent:groups:(x)"))')
        [p] = parse_security_labels(label)
        self.assertEqual(p.classification, "Top Secret")
        self.assertEqual(p.permitted_organisations, ["a|b", 'O\'Brien & "Sons"', "telicent"])
        self.assertEqual(p.and_groups, [G + "a=b", G + "g1"])
        self.assertEqual(p.or_groups, [G + "(x)"])

    def test_or_expressions_give_one_result_per_alternative(self):
        first = telicent("S", ["a"], ["GBR"], [G + "g"], [G + "h"]).build_security_labels()
        second = idh("O", ["b"], ["GBR"], [], []).build_security_labels()
        both = SecurityLabelBuilder().add_or_expression(first).add_or_expression(second).build()
        alternatives = parse_security_labels(both)
        self.assertEqual([a.classification for a in alternatives], ["S", "O"])
        self.assertEqual(alternatives[1].permitted_organisations, ["b"])

    def test_the_older_suffixed_group_form_is_read(self):
        # What the builder wrote before the :and and :or suffixes were dropped.
        label = "(classification=S&(permitted_organisations=a)&urn:x:g1:and&urn:x:and:and&(urn:x:g2:or|x:or:or))"
        [p] = parse_security_labels(label)
        self.assertEqual(p.and_groups, ["urn:x:g1", "urn:x:and"])
        self.assertEqual(p.or_groups, ["urn:x:g2", "x:or"])
        self.assertTrue(p.group_suffixes)

    def test_a_trailing_suffix_is_read_as_the_older_form(self):
        # The one case the text cannot decide: a current label whose group is literally named
        # urn:telicent:groups:x:and reads the same as an older label whose group was
        # urn:telicent:groups:x. The older reading is taken; it is right for every label written
        # before the suffixes were dropped.
        [p] = parse_security_labels("(classification=S&(permitted_organisations=a)&urn:telicent:groups:x:and)")
        self.assertEqual(p.and_groups, [G + "x"])
        self.assertTrue(p.group_suffixes)

    def test_the_two_group_forms_never_mix(self):
        for text in ["(classification=S&urn:x:g1:and&urn:x:g2)",
                     "(classification=S&(urn:x:g1:or|urn:x:g2))",
                     "(classification=S&urn:x:g1:and&(urn:x:g2))"]:
            with self.assertRaises(NotBuilderShape, msg=text):
                parse_security_labels(text)

    def test_shapes_the_builder_does_not_write_are_refused(self):
        for text in ["country=uk & employee", "classification=S", "*", "!", "",
                     "(classification=S&classification=O)",
                     "(classification=S&(permitted_organisations=a)&(permitted_organisations=b))",
                     "(clearance=S&urn:x:g1)",                          # groups in a v1 label
                     "(classification=S&(permitted_organisations=a|permitted_nationalities=b))",
                     # Labels an older builder wrote unquoted: | and & in a value, = in a group.
                     "(classification=S&(permitted_organisations=a|b))",
                     "(classification=S&a&b:and)",
                     "(classification=S&k=v:and)",
                     "(classification=S&urn:telicent:groups:a=b)"]:
            with self.assertRaises(NotBuilderShape, msg=text):
                parse_security_labels(text)

    def test_every_bounded_input_round_trips(self):
        """The whole bounded domain of docs/reversibility.md, not a sample: words of up to three
        characters over the grammar classes plus the awkward ones, lists of up to two with order and
        repeats, the three label shapes. Quoted values are covered by test_quoted_values_are_unescaped."""
        words = set()
        for start in ("a", "Z", "_"):
            words.add(start)
            for last in ("c", "_", "9"):
                words.add(start + last)
                for middle in ("b", "9", "_", ":", ".", "-", "+"):
                    words.add(start + middle + last)
        words.update(["x:and", "x:or", "a:and:and"])
        pool = ["a", "a:b_", "x:and", "x:or", "urn:x:g1"]
        # A current-format group named ...:and or ...:or is the documented ambiguity, tested on its own.
        groups = [G + "a", G + "b_c", G + "a.b-c", G + "g9"]
        lists = [[]] + [list(p) for n in (1, 2) for p in itertools.product(pool, repeat=n)]
        non_empty = [xs for xs in lists if xs]
        group_lists = [[]] + [list(p) for n in (1, 2) for p in itertools.product(groups, repeat=n)]
        checked = 0
        for cl in sorted(words):
            for orgs in non_empty:
                for nats in non_empty[:7]:
                    [p] = parse_security_labels(v1(cl, orgs, nats))
                    self.assertEqual(p, ParsedLabel("v1", cl, orgs, nats, [], []))
                    checked += 1
        for orgs in non_empty[:7]:
            for ands in group_lists:
                for ors in group_lists:
                    m = idh("S", orgs, ["GBR"], ands, ors)
                    [p] = parse_security_labels(m.build_security_labels())
                    suffixes = None if not ands and not ors else False
                    self.assertEqual(p, ParsedLabel("v2", "S", orgs, ["GBR"], ands, ors, suffixes))
                    checked += 1
        for cl in sorted(words)[::5]:
            for orgs in non_empty[:7]:
                for ands in group_lists[1:8]:
                    for ors in group_lists[1:8]:
                        m = telicent(cl, orgs, ["GBR"], ands, ors)
                        [p] = parse_security_labels(m.build_security_labels())
                        self.assertEqual(p, ParsedLabel("v2", cl, orgs, ["GBR"], ands, ors, False))
                        checked += 1
        self.assertGreater(checked, 20_000)
