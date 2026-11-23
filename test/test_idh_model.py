import unittest

from telicent_labels import IDHModel


class IDHModelTestCase(unittest.TestCase):
    def test_simple_label(self):
        label = {
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
                "oneOfGroups": []
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }

        security_label = IDHModel(**label).build_security_labels()
        self.assertEqual(security_label, "(classification=O&(permitted_organisations=Telicent)&"
                                         "(permitted_nationalities=GBR)&urn:telicent:groups:developer)")
    def test_simple_label_multi_group(self):
        label = {
            "apiVersion": "v1alpha",
            "uuid": "test_Abc_123",
            "creationDate": "2024-09-27 00:00:00+00:00",
            "containsPii": False,
            "dataSource": "Tom Test",
            "access": {
                "classification": "O",
                "allowedOrgs": ["Telicent"],
                "allowedNats": ["GBR"],
                "groups": ["urn:telicent:groups:developer", "urn:telicent:groups:africa"],
                "oneOfGroups": []
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }

        security_label = IDHModel(**label).build_security_labels()
        self.assertEqual(security_label, "(classification=O&(permitted_organisations=Telicent)&"
                                         "(permitted_nationalities=GBR)&urn:telicent:groups:developer&"
                                         "urn:telicent:groups:africa)")
    def test_simple_label_multi_nationality(self):
        label = {
            "apiVersion": "v1alpha",
            "uuid": "test_Abc_123",
            "creationDate": "2024-09-27 00:00:00+00:00",
            "containsPii": False,
            "dataSource": "Tom Test",
            "access": {
                "classification": "O",
                "allowedOrgs": ["Telicent"],
                "allowedNats": ["GBR", "FRA"],
                "groups": ["urn:telicent:groups:developer", "urn:telicent:groups:africa"],
                "oneOfGroups": []
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }

        security_label = IDHModel(**label).build_security_labels()
        self.assertEqual(security_label, "(classification=O&(permitted_organisations=Telicent)&"
                                         "(permitted_nationalities=GBR|permitted_nationalities=FRA)&"
                                         "urn:telicent:groups:developer&urn:telicent:groups:africa)")
    def test_simple_label_multi_organisation(self):
        label = {
            "apiVersion": "v1alpha",
            "uuid": "test_Abc_123",
            "creationDate": "2024-09-27 00:00:00+00:00",
            "containsPii": False,
            "dataSource": "Tom Test",
            "access": {
                "classification": "O",
                "allowedOrgs": ["Telicent", "NHS"],
                "allowedNats": ["GBR", "FRA"],
                "groups": ["urn:telicent:groups:developer", "urn:telicent:groups:africa"],
                "oneOfGroups": []
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }

        security_label = IDHModel(**label).build_security_labels()
        self.assertEqual(security_label, "(classification=O&"
                                         "(permitted_organisations=Telicent|permitted_organisations=NHS)&"
                                         "(permitted_nationalities=GBR|permitted_nationalities=FRA)&"
                                         "urn:telicent:groups:developer&urn:telicent:groups:africa)")

    def test_simple_label_single_one_of_group(self):
        label = {
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
                "oneOfGroups": ["urn:telicent:groups:analyst"]
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }

        security_label = IDHModel(**label).build_security_labels()
        self.assertEqual(security_label, "(classification=O&(permitted_organisations=Telicent)&"
                                         "(permitted_nationalities=GBR)&urn:telicent:groups:developer&"
                                         "(urn:telicent:groups:analyst))")

    def test_simple_label_multi_one_of_group(self):
        label = {
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
                "oneOfGroups": ["urn:telicent:groups:analyst", "urn:telicent:groups:africa"]
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }

        security_label = IDHModel(**label).build_security_labels()
        self.assertEqual(security_label, "(classification=O&(permitted_organisations=Telicent)&"
                                         "(permitted_nationalities=GBR)&urn:telicent:groups:developer&"
                                         "(urn:telicent:groups:analyst|urn:telicent:groups:africa))")

    def test_simple_label_only_one_of_groups(self):
        label = {
            "apiVersion": "v1alpha",
            "uuid": "test_Abc_123",
            "creationDate": "2024-09-27 00:00:00+00:00",
            "containsPii": False,
            "dataSource": "Tom Test",
            "access": {
                "classification": "O",
                "allowedOrgs": ["Telicent"],
                "allowedNats": ["GBR"],
                "groups": [],
                "oneOfGroups": ["urn:telicent:groups:analyst"]
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }

        security_label = IDHModel(**label).build_security_labels()
        self.assertEqual(security_label, "(classification=O&(permitted_organisations=Telicent)&"
                                         "(permitted_nationalities=GBR)&(urn:telicent:groups:analyst))")

    def test_error_label_no_classification(self):
        label = {
            "apiVersion": "v1alpha",
            "uuid": "test_Abc_123",
            "creationDate": "2024-09-27 00:00:00+00:00",
            "containsPii": False,
            "dataSource": "Tom Test",
            "access": {
                "classification": "",
                "allowedOrgs": ["Telicent", "NHS"],
                "allowedNats": ["GBR", "FRA"],
                "groups": ["urn:telicent:groups:developer", "urn:telicent:groups:africa"],
                "oneOfGroups": []
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }
        with self.assertRaises(ValueError) as context:
            IDHModel(**label)
        self.assertTrue("The classification field cannot be an empty string" in str(context.exception) )

    def test_error_label_wrong_classification(self):
        label = {
            "apiVersion": "v1alpha",
            "uuid": "test_Abc_123",
            "creationDate": "2024-09-27 00:00:00+00:00",
            "containsPii": False,
            "dataSource": "Tom Test",
            "access": {
                "classification": "P",
                "allowedOrgs": ["Telicent", "NHS"],
                "allowedNats": ["GBR", "FRA"],
                "groups": ["urn:telicent:groups:developer", "urn:telicent:groups:africa"],
                "oneOfGroups": []
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }
        with self.assertRaises(ValueError) as context:
            IDHModel(**label)
        self.assertTrue("The classification field must be 'O', 'OS', 'S' or 'TS'." in str(context.exception) )

    def test_simple_label_empty_groups_and_one_of_groups(self):
        label = {
            "apiVersion": "v1alpha",
            "uuid": "test_Abc_123",
            "creationDate": "2024-09-27 00:00:00+00:00",
            "containsPii": False,
            "dataSource": "Tom Test",
            "access": {
                "classification": "O",
                "allowedOrgs": ["Telicent"],
                "allowedNats": ["GBR"],
                "groups": [],
                "oneOfGroups": []
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }

        security_label = IDHModel(**label).build_security_labels()
        self.assertEqual(security_label, "(classification=O&(permitted_organisations=Telicent)&"
                                         "(permitted_nationalities=GBR))")
        self.assertNotIn("&&", security_label)
        self.assertNotIn("()", security_label)

    def test_error_label_empty_allowed_orgs(self):
        label = {
            "apiVersion": "v1alpha",
            "uuid": "test_Abc_123",
            "creationDate": "2024-09-27 00:00:00+00:00",
            "containsPii": False,
            "dataSource": "Tom Test",
            "access": {
                "classification": "O",
                "allowedOrgs": [],
                "allowedNats": ["GBR"],
                "groups": [],
                "oneOfGroups": []
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }
        with self.assertRaises(ValueError) as context:
            IDHModel(**label)
        self.assertTrue("The allowedOrgs field cannot be an empty list" in str(context.exception))

    def test_error_label_empty_allowed_nats(self):
        label = {
            "apiVersion": "v1alpha",
            "uuid": "test_Abc_123",
            "creationDate": "2024-09-27 00:00:00+00:00",
            "containsPii": False,
            "dataSource": "Tom Test",
            "access": {
                "classification": "O",
                "allowedOrgs": ["Telicent"],
                "allowedNats": [],
                "groups": [],
                "oneOfGroups": []
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }
        with self.assertRaises(ValueError) as context:
            IDHModel(**label)
        self.assertTrue("The allowedNats field cannot be an empty list" in str(context.exception))

    def test_error_label_missing_fields(self):
        label = {
            "apiVersion": "v1alpha",
            "uuid": "test_Abc_123",
            "creationDate": "2024-09-27 00:00:00+00:00",
            "containsPii": False,
            "dataSource": "Tom Test",
            "access": {
                "classification": "O",

            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }

        with self.assertRaises(ValueError) as context:
            IDHModel(**label)

        self.assertTrue("access.allowedNats" in str(context.exception) )
        self.assertTrue("access.allowedOrgs" in str(context.exception) )
        self.assertTrue("access.groups" in str(context.exception) )
        self.assertTrue("access.oneOfGroups" in str(context.exception) )
