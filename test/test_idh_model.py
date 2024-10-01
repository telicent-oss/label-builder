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
                "groups": ["urn:telicent:groups:developer"]
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }

        security_label = IDHModel(**label).build_security_labels()
        self.assertEqual(security_label, "(classification=O&(permitted_organisations=Telicent)&"
                                         "(permitted_nationalities=GBR)&urn:telicent:groups:developer:and)")
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
                "groups": ["urn:telicent:groups:developer", "urn:telicent:groups:africa"]
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }

        security_label = IDHModel(**label).build_security_labels()
        self.assertEqual(security_label, "(classification=O&(permitted_organisations=Telicent)&"
                                         "(permitted_nationalities=GBR)&urn:telicent:groups:developer:and&"
                                         "urn:telicent:groups:africa:and)")
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
                "groups": ["urn:telicent:groups:developer", "urn:telicent:groups:africa"]
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }

        security_label = IDHModel(**label).build_security_labels()
        self.assertEqual(security_label, "(classification=O&(permitted_organisations=Telicent)&"
                                         "(permitted_nationalities=GBR|permitted_nationalities=FRA)&"
                                         "urn:telicent:groups:developer:and&urn:telicent:groups:africa:and)")
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
                "groups": ["urn:telicent:groups:developer", "urn:telicent:groups:africa"]
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }

        security_label = IDHModel(**label).build_security_labels()
        self.assertEqual(security_label, "(classification=O&"
                                         "(permitted_organisations=Telicent|permitted_organisations=NHS)&"
                                         "(permitted_nationalities=GBR|permitted_nationalities=FRA)&"
                                         "urn:telicent:groups:developer:and&urn:telicent:groups:africa:and)")

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
                "groups": ["urn:telicent:groups:developer", "urn:telicent:groups:africa"]
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
                "groups": ["urn:telicent:groups:developer", "urn:telicent:groups:africa"]
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }
        with self.assertRaises(ValueError) as context:
            IDHModel(**label)
        self.assertTrue("The classification field must be 'O', 'OS', 'S' or 'TS'." in str(context.exception) )

    def test_simple_label_only_classification(self):
        label = {
            "apiVersion": "v1alpha",
            "uuid": "test_Abc_123",
            "creationDate": "2024-09-27 00:00:00+00:00",
            "containsPii": False,
            "dataSource": "Tom Test",
            "access": {
                "classification": "O",
                "allowedOrgs": [],
                "allowedNats": [],
                "groups": []
            },
            "ownership":{
                "originatingOrg": "Telicent"
            }
        }

        security_label = IDHModel(**label).build_security_labels()
        self.assertEqual(security_label, "(classification=O)")

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
