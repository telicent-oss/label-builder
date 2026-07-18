import unittest

from telicent_labels import SecurityLabelBuilder, TelicentSecurityLabelsV2, TelicentModel


def _base_model_kwargs(**overrides):
    """Minimal set of valid fields for a TelicentModel, with group fields overridable."""
    kwargs = {
        "identifier": "id1",
        "classification": "S",
        "permittedOrgs": ["orgA"],
        "permittedNats": ["natA"],
        "orGroups": [],
        "andGroups": [],
        "dataSet": ["ds1"],
        "authRef": ["ar1"],
        "dissemination": ["dis1"],
    }
    kwargs.update(overrides)
    return kwargs


class TelicentModelEmptyGroupsTestCase(unittest.TestCase):
    """
    andGroups and orGroups are required fields but are allowed to be empty lists.
    When empty they must be omitted from the built expression entirely - i.e. no
    stray '&&' (empty andGroups) or empty '()' (empty orGroups).
    """

    def test_both_groups_empty(self):
        model = TelicentModel(**_base_model_kwargs(orGroups=[], andGroups=[]))

        security_label = model.build_security_labels()

        self.assertEqual(
            security_label,
            "(classification=S&(permitted_organisations=orgA)&(permitted_nationalities=natA))",
        )

    def test_empty_or_groups_with_and_groups(self):
        # Bare group names are coerced to urn:telicent:groups:<name>.
        model = TelicentModel(**_base_model_kwargs(orGroups=[], andGroups=["developer"]))

        security_label = model.build_security_labels()

        self.assertEqual(
            security_label,
            "(classification=S&(permitted_organisations=orgA)&"
            "(permitted_nationalities=natA)&urn:telicent:groups:developer)",
        )

    def test_empty_and_groups_with_or_groups(self):
        # Bare group names are coerced to urn:telicent:groups:<name>.
        model = TelicentModel(**_base_model_kwargs(orGroups=["analyst"], andGroups=[]))

        security_label = model.build_security_labels()

        self.assertEqual(
            security_label,
            "(classification=S&(permitted_organisations=orgA)&"
            "(permitted_nationalities=natA)&(urn:telicent:groups:analyst))",
        )

    def test_both_groups_populated(self):
        # Bare group names are coerced to urn:telicent:groups:<name>.
        model = TelicentModel(
            **_base_model_kwargs(orGroups=["analyst"], andGroups=["developer"])
        )

        security_label = model.build_security_labels()

        self.assertEqual(
            security_label,
            "(classification=S&(permitted_organisations=orgA)&"
            "(permitted_nationalities=natA)&urn:telicent:groups:developer&"
            "(urn:telicent:groups:analyst))",
        )

    def test_empty_groups_produce_no_stray_operators(self):
        security_label = TelicentModel(
            **_base_model_kwargs(orGroups=[], andGroups=[])
        ).build_security_labels()

        self.assertNotIn("&&", security_label)
        self.assertNotIn("()", security_label)


class SecurityLabelBuilderEmptyValuesTestCase(unittest.TestCase):
    """add_multiple must be a no-op when called with no values."""

    def test_add_multiple_with_no_values_is_noop(self):
        builder = SecurityLabelBuilder()
        returned = builder.add_multiple(TelicentSecurityLabelsV2.AND_GROUPS.value)

        self.assertIs(returned, builder)
        self.assertEqual(builder.labels, [])
        self.assertEqual(builder.used_labels, [])

    def test_add_multiple_empty_then_build_is_empty(self):
        security_label = (
            SecurityLabelBuilder()
            .add_multiple(TelicentSecurityLabelsV2.AND_GROUPS.value)
            .add_multiple(TelicentSecurityLabelsV2.OR_GROUPS.value)
            .build()
        )

        self.assertEqual(security_label, "")


if __name__ == "__main__":
    unittest.main()
