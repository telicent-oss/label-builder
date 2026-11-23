import unittest
from datetime import datetime, timezone
from uuid import UUID

from pydantic import ValidationError

from telicent_labels import (
    IDHModel,
    TelicentModel,
    build_idh_dict,
    build_telicent_dict,
)


class BuildIDHDictTestCase(unittest.TestCase):
    def test_minimal_dict_is_valid_and_shaped(self):
        label = build_idh_dict(
            uuid="doc-123",
            classification="O",
            allowed_orgs=["Telicent"],
            allowed_nats=["GBR"],
            originating_org="Telicent",
        )

        self.assertEqual(label["uuid"], "doc-123")
        self.assertEqual(label["apiVersion"], "v1alpha")
        self.assertFalse(label["containsPii"])
        self.assertEqual(label["access"]["classification"], "O")
        self.assertEqual(label["access"]["allowedOrgs"], ["Telicent"])
        self.assertEqual(label["access"]["allowedNats"], ["GBR"])
        self.assertEqual(label["access"]["groups"], [])
        self.assertEqual(label["access"]["oneOfGroups"], [])
        self.assertEqual(label["ownership"], {"originatingOrg": "Telicent"})

    def test_output_feeds_directly_into_model(self):
        label = build_idh_dict(
            uuid="doc-123",
            classification="O",
            allowed_orgs=["Telicent"],
            allowed_nats=["GBR"],
            originating_org="Telicent",
            groups=["urn:telicent:groups:developer"],
        )

        security_label = IDHModel(**label).build_security_labels()

        self.assertEqual(
            security_label,
            "(classification=O&(permitted_organisations=Telicent)&"
            "(permitted_nationalities=GBR)&urn:telicent:groups:developer)",
        )

    def test_optional_fields_included_when_supplied(self):
        label = build_idh_dict(
            uuid="doc-123",
            classification="O",
            allowed_orgs=["Telicent"],
            allowed_nats=["GBR"],
            originating_org="Telicent",
            contains_pii=True,
            data_source="Example Source",
            user="alice",
            one_of_groups=["urn:telicent:groups:analyst"],
            creation_date=datetime(2024, 9, 27, tzinfo=timezone.utc),
        )

        self.assertTrue(label["containsPii"])
        self.assertEqual(label["dataSource"], "Example Source")
        self.assertEqual(label["ownership"]["user"], "alice")
        self.assertEqual(label["access"]["oneOfGroups"], ["urn:telicent:groups:analyst"])
        self.assertEqual(label["creationDate"], "2024-09-27T00:00:00+00:00")

    def test_optional_fields_omitted_when_absent(self):
        label = build_idh_dict(
            uuid="doc-123",
            classification="O",
            allowed_orgs=["Telicent"],
            allowed_nats=["GBR"],
            originating_org="Telicent",
        )

        self.assertNotIn("dataSource", label)
        self.assertNotIn("user", label["ownership"])

    def test_creation_date_defaults_to_now(self):
        before = datetime.now(timezone.utc)
        label = build_idh_dict(
            uuid="doc-123",
            classification="O",
            allowed_orgs=["Telicent"],
            allowed_nats=["GBR"],
            originating_org="Telicent",
        )
        after = datetime.now(timezone.utc)

        parsed = datetime.fromisoformat(label["creationDate"])
        self.assertIsNotNone(parsed.tzinfo)
        self.assertGreaterEqual(parsed, before)
        self.assertLessEqual(parsed, after)

    def test_creation_date_accepts_string(self):
        label = build_idh_dict(
            uuid="doc-123",
            classification="O",
            allowed_orgs=["Telicent"],
            allowed_nats=["GBR"],
            originating_org="Telicent",
            creation_date="2024-09-27 00:00:00+00:00",
        )

        self.assertEqual(label["creationDate"], "2024-09-27 00:00:00+00:00")

    def test_validate_true_raises_on_bad_classification(self):
        with self.assertRaises(ValidationError):
            build_idh_dict(
                uuid="doc-123",
                classification="P",
                allowed_orgs=["Telicent"],
                allowed_nats=["GBR"],
                originating_org="Telicent",
            )

    def test_validate_false_skips_validation(self):
        label = build_idh_dict(
            uuid="doc-123",
            classification="P",
            allowed_orgs=["Telicent"],
            allowed_nats=["GBR"],
            originating_org="Telicent",
            validate=False,
        )

        self.assertEqual(label["access"]["classification"], "P")

    def test_uuid_generated_when_not_provided(self):
        label = build_idh_dict(
            classification="O",
            allowed_orgs=["Telicent"],
            allowed_nats=["GBR"],
            originating_org="Telicent",
        )

        # Parses as a UUID and is unique per call.
        UUID(label["uuid"])
        other = build_idh_dict(
            classification="O",
            allowed_orgs=["Telicent"],
            allowed_nats=["GBR"],
            originating_org="Telicent",
        )
        self.assertNotEqual(label["uuid"], other["uuid"])

    def test_supplied_uuid_is_preserved(self):
        label = build_idh_dict(
            uuid="doc-123",
            classification="O",
            allowed_orgs=["Telicent"],
            allowed_nats=["GBR"],
            originating_org="Telicent",
        )

        self.assertEqual(label["uuid"], "doc-123")

    def test_inputs_are_copied_not_referenced(self):
        orgs = ["Telicent"]
        label = build_idh_dict(
            uuid="doc-123",
            classification="O",
            allowed_orgs=orgs,
            allowed_nats=["GBR"],
            originating_org="Telicent",
        )
        orgs.append("NHS")

        self.assertEqual(label["access"]["allowedOrgs"], ["Telicent"])


class BuildTelicentDictTestCase(unittest.TestCase):
    def test_minimal_dict_is_valid_and_shaped(self):
        label = build_telicent_dict(
            identifier="doc-001",
            classification="S",
            permitted_orgs=["orgA"],
            permitted_nats=["natA"],
        )

        self.assertEqual(label["identifier"], "doc-001")
        self.assertEqual(label["apiVersion"], "v1alpha")
        self.assertEqual(label["permittedOrgs"], ["orgA"])
        self.assertEqual(label["permittedNats"], ["natA"])
        for key in ("orGroups", "andGroups", "dataSet", "authRef", "dissemination"):
            self.assertEqual(label[key], [], key)

    def test_identifier_generated_when_not_provided(self):
        label = build_telicent_dict(
            classification="S",
            permitted_orgs=["orgA"],
            permitted_nats=["natA"],
        )

        # Parses as a UUID and is unique per call.
        UUID(label["identifier"])
        other = build_telicent_dict(
            classification="S",
            permitted_orgs=["orgA"],
            permitted_nats=["natA"],
        )
        self.assertNotEqual(label["identifier"], other["identifier"])

    def test_supplied_identifier_is_preserved(self):
        label = build_telicent_dict(
            identifier="doc-001",
            classification="S",
            permitted_orgs=["orgA"],
            permitted_nats=["natA"],
        )

        self.assertEqual(label["identifier"], "doc-001")

    def test_output_feeds_directly_into_model(self):
        label = build_telicent_dict(
            identifier="doc-001",
            classification="S",
            permitted_orgs=["Telicent", "NHS"],
            permitted_nats=["GBR", "USA"],
            or_groups=["urn:telicent:groups:analyst"],
            and_groups=["urn:telicent:groups:developer"],
        )

        security_label = TelicentModel(**label).build_security_labels()

        self.assertEqual(
            security_label,
            "(classification=S&"
            "(permitted_organisations=Telicent|permitted_organisations=NHS)&"
            "(permitted_nationalities=GBR|permitted_nationalities=USA)&"
            "urn:telicent:groups:developer&(urn:telicent:groups:analyst))",
        )

    def test_optional_fields_included_when_supplied(self):
        label = build_telicent_dict(
            identifier="doc-001",
            classification="S",
            permitted_orgs=["orgA"],
            permitted_nats=["natA"],
            originator="Alice",
            custodian="Bob",
            policy_ref="pol-1",
            disposition_process="review",
            data_set=["ds1"],
            auth_ref=["ar1"],
            dissemination=["internal"],
            specification="spec-1",
            created_date_time=datetime(2024, 9, 27, tzinfo=timezone.utc),
            disposition_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(label["originator"], "Alice")
        self.assertEqual(label["custodian"], "Bob")
        self.assertEqual(label["policyRef"], "pol-1")
        self.assertEqual(label["dispositionProcess"], "review")
        self.assertEqual(label["specification"], "spec-1")
        self.assertEqual(label["createdDateTime"], "2024-09-27T00:00:00+00:00")
        self.assertEqual(label["dispositionDate"], "2025-01-01T00:00:00+00:00")

    def test_optional_fields_omitted_when_absent(self):
        label = build_telicent_dict(
            identifier="doc-001",
            classification="S",
            permitted_orgs=["orgA"],
            permitted_nats=["natA"],
        )

        for key in (
            "originator",
            "custodian",
            "policyRef",
            "dispositionProcess",
            "specification",
            "dispositionDate",
        ):
            self.assertNotIn(key, label)

    def test_created_date_time_defaults_to_now(self):
        before = datetime.now(timezone.utc)
        label = build_telicent_dict(
            identifier="doc-001",
            classification="S",
            permitted_orgs=["orgA"],
            permitted_nats=["natA"],
        )
        after = datetime.now(timezone.utc)

        parsed = datetime.fromisoformat(label["createdDateTime"])
        self.assertIsNotNone(parsed.tzinfo)
        self.assertGreaterEqual(parsed, before)
        self.assertLessEqual(parsed, after)

    def test_validate_true_raises_on_empty_permitted_orgs(self):
        with self.assertRaises(ValidationError):
            build_telicent_dict(
                identifier="doc-001",
                classification="S",
                permitted_orgs=[],
                permitted_nats=["natA"],
            )

    def test_validate_false_skips_validation(self):
        label = build_telicent_dict(
            identifier="doc-001",
            classification="",
            permitted_orgs=[],
            permitted_nats=["natA"],
            validate=False,
        )

        self.assertEqual(label["permittedOrgs"], [])


if __name__ == "__main__":
    unittest.main()
