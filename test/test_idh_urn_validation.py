import unittest

from pydantic import ValidationError

from telicent_labels import IDHModel, build_idh_dict
from telicent_labels.idh_model import AccessModel


def _access(**overrides):
    kwargs = {
        "classification": "O",
        "allowedOrgs": ["Telicent"],
        "allowedNats": ["GBR"],
        "groups": [],
        "oneOfGroups": [],
    }
    kwargs.update(overrides)
    return AccessModel(**kwargs)


class EnsureUrnsTestCase(unittest.TestCase):
    """`AccessModel.ensure_urns` must leave valid URNs untouched and coerce
    non-URN group names into `urn:telicent:groups:<name>` — without dropping
    any entry."""

    def test_already_valid_urns_are_preserved(self):
        access = _access(
            groups=["urn:telicent:groups:developer"],
            oneOfGroups=["urn:telicent:groups:analyst"],
        )

        self.assertEqual(access.groups, ["urn:telicent:groups:developer"])
        self.assertEqual(access.oneOfGroups, ["urn:telicent:groups:analyst"])

    def test_plain_names_are_converted(self):
        access = _access(groups=["developer"], oneOfGroups=["analyst"])

        self.assertEqual(access.groups, ["urn:telicent:groups:developer"])
        self.assertEqual(access.oneOfGroups, ["urn:telicent:groups:analyst"])

    def test_names_with_spaces_are_hyphenated(self):
        access = _access(groups=["data science"])

        self.assertEqual(access.groups, ["urn:telicent:groups:data-science"])

    def test_mixed_valid_and_invalid_none_dropped(self):
        access = _access(
            groups=["urn:telicent:groups:developer", "analyst", "data science"],
        )

        self.assertEqual(
            access.groups,
            [
                "urn:telicent:groups:developer",
                "urn:telicent:groups:analyst",
                "urn:telicent:groups:data-science",
            ],
        )

    def test_order_is_preserved(self):
        access = _access(groups=["zulu", "urn:telicent:groups:alpha", "mike"])

        self.assertEqual(
            access.groups,
            [
                "urn:telicent:groups:zulu",
                "urn:telicent:groups:alpha",
                "urn:telicent:groups:mike",
            ],
        )

    def test_empty_lists_stay_empty(self):
        access = _access(groups=[], oneOfGroups=[])

        self.assertEqual(access.groups, [])
        self.assertEqual(access.oneOfGroups, [])

    def test_non_telicent_urn_is_treated_as_a_plain_name(self):
        # Only Telicent group URNs are recognised as already-valid. A URN from
        # another namespace is not, so it is coerced like any other bare name.
        access = _access(groups=["urn:example:foo:bar"])

        self.assertEqual(
            access.groups, ["urn:telicent:groups:urn:example:foo:bar"]
        )

    def test_invalid_characters_raise(self):
        with self.assertRaises(ValidationError):
            _access(groups=["bad<>name"])

    def test_blank_name_raises(self):
        with self.assertRaises(ValidationError):
            _access(groups=["   "])


class EnsureUrnsEndToEndTestCase(unittest.TestCase):
    """Coerced URNs must flow through to the built Security Label."""

    def test_builder_to_security_label_coerces_groups(self):
        label = build_idh_dict(
            classification="O",
            allowed_orgs=["Telicent"],
            allowed_nats=["GBR"],
            originating_org="Telicent",
            groups=["developer"],
            one_of_groups=["analyst"],
        )

        security_label = IDHModel(**label).build_security_labels()

        self.assertEqual(
            security_label,
            "(classification=O&(permitted_organisations=Telicent)&"
            "(permitted_nationalities=GBR)&urn:telicent:groups:developer&"
            "(urn:telicent:groups:analyst))",
        )


if __name__ == "__main__":
    unittest.main()
