import copy
import unittest

from telicent_labels import IDHModel, PolicyInformationModel, TelicentModel

# A valid IDH (internal data header) payload and the security label it produces.
_IDH_LABEL = {
    "apiVersion": "v1alpha",
    "uuid": "test_Abc_123",
    "creationDate": "2024-09-27 00:00:00+00:00",
    "containsPii": False,
    "dataSource": "Tom Test",
    "access": {
        "classification": "O",
        "allowedOrgs": ["Telicent"],
        "allowedNats": ["GBR"],
        "groups": ["urn:telicent:groups:developer"],
        "oneOfGroups": [],
    },
    "ownership": {"originatingOrg": "Telicent"},
}
_IDH_EXPECTED = (
    "(classification=O&(permitted_organisations=Telicent)&"
    "(permitted_nationalities=GBR)&urn:telicent:groups:developer)"
)

# A valid EDH (external data header / TelicentModel) payload and its label.
_EDH_LABEL = {
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
_EDH_EXPECTED = (
    "(classification=S&(permitted_organisations=orgA)&(permitted_nationalities=natA))"
)


def _idh_kwargs():
    return copy.deepcopy(_IDH_LABEL)


def _edh_kwargs():
    return copy.deepcopy(_EDH_LABEL)


class PolicyInformationModelDelegationTestCase(unittest.TestCase):
    """
    A PolicyInformationModel carries exactly one of an IDH or an EDH policy
    object and delegates label building to whichever was supplied.
    """

    def test_idh_builds_delegated_labels(self):
        model = PolicyInformationModel(IDH=IDHModel(**_idh_kwargs()))

        self.assertEqual(model.build_security_labels(), _IDH_EXPECTED)

    def test_edh_builds_delegated_labels(self):
        model = PolicyInformationModel(EDH=TelicentModel(**_edh_kwargs()))

        self.assertEqual(model.build_security_labels(), _EDH_EXPECTED)

    def test_idh_accepts_nested_dict(self):
        """Nested dicts are coerced to the underlying model by pydantic."""
        model = PolicyInformationModel(IDH=_idh_kwargs())

        self.assertIsInstance(model.IDH, IDHModel)
        self.assertEqual(model.build_security_labels(), _IDH_EXPECTED)

    def test_edh_accepts_nested_dict(self):
        model = PolicyInformationModel(EDH=_edh_kwargs())

        self.assertIsInstance(model.EDH, TelicentModel)
        self.assertEqual(model.build_security_labels(), _EDH_EXPECTED)

    def test_policy_object_is_the_supplied_idh(self):
        idh = IDHModel(**_idh_kwargs())
        model = PolicyInformationModel(IDH=idh)

        self.assertIs(model.policy_object, model.IDH)
        self.assertIsNone(model.EDH)

    def test_policy_object_is_the_supplied_edh(self):
        edh = TelicentModel(**_edh_kwargs())
        model = PolicyInformationModel(EDH=edh)

        self.assertIs(model.policy_object, model.EDH)
        self.assertIsNone(model.IDH)

    def test_delegates_to_underlying_build(self):
        """The policy label is exactly what the underlying model would build."""
        idh = IDHModel(**_idh_kwargs())
        model = PolicyInformationModel(IDH=idh)

        self.assertEqual(model.build_security_labels(), idh.build_security_labels())


class PolicyInformationModelMutualExclusivityTestCase(unittest.TestCase):
    """Exactly one of IDH / EDH must be supplied per CORE data packet."""

    def test_both_supplied_is_rejected(self):
        with self.assertRaises(ValueError) as context:
            PolicyInformationModel(
                IDH=IDHModel(**_idh_kwargs()), EDH=TelicentModel(**_edh_kwargs())
            )

        self.assertIn("Only one model can be used per CORE data packet", str(context.exception))

    def test_neither_supplied_is_rejected(self):
        with self.assertRaises(ValueError) as context:
            PolicyInformationModel()

        self.assertIn("Only one model can be used per CORE data packet", str(context.exception))

    def test_explicit_none_for_both_is_rejected(self):
        with self.assertRaises(ValueError) as context:
            PolicyInformationModel(IDH=None, EDH=None)

        self.assertIn("Only one model can be used per CORE data packet", str(context.exception))


class PolicyInformationModelIsolationTestCase(unittest.TestCase):
    """
    policy_object must live on the instance, never on the class - two models
    built from different policy objects must not interfere with one another.
    """

    def test_instances_do_not_share_policy_object(self):
        idh_model = PolicyInformationModel(IDH=IDHModel(**_idh_kwargs()))
        edh_model = PolicyInformationModel(EDH=TelicentModel(**_edh_kwargs()))

        # Building the EDH model must not have rebound the IDH model's object.
        self.assertIs(idh_model.policy_object, idh_model.IDH)
        self.assertIs(edh_model.policy_object, edh_model.EDH)
        self.assertEqual(idh_model.build_security_labels(), _IDH_EXPECTED)
        self.assertEqual(edh_model.build_security_labels(), _EDH_EXPECTED)

    def test_class_attribute_untouched_by_instances(self):
        PolicyInformationModel(IDH=IDHModel(**_idh_kwargs()))

        # The field default on the class must remain None after construction.
        self.assertIsNone(PolicyInformationModel.model_fields["policy_object"].default)


class PolicyInformationModelFallbackTestCase(unittest.TestCase):
    """When no policy object is present the model yields the open label '*'."""

    def test_no_policy_object_yields_wildcard(self):
        # model_construct bypasses validation, giving a model with no policy_object.
        model = PolicyInformationModel.model_construct()

        self.assertIsNone(model.policy_object)
        self.assertEqual(model.build_security_labels(), "*")


if __name__ == "__main__":
    unittest.main()
