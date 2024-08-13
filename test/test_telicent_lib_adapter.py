import json
import unittest
from datetime import datetime, timezone
from typing import Iterable, Any
from unittest.mock import patch

from telicent_lib import AutomaticAdapter, Record, RecordUtils
from telicent_lib.sinks.listSink import ListSink

from telicent_labels import TelicentModel


def custom_range_generator(**range_args) -> Iterable[Record]:
    for i in range(range_args["start"], range_args["stop"]):
        record = Record(headers=None, key=i, value=str(i), raw=None)
        if {'data_header_model', 'security_labels'}.issubset(range_args):
            headers = [('policyInformation', {'DH': range_args['data_header_model'].model_dump()}),
                       ('Security-Label', range_args['security_labels'])]
            record = RecordUtils.add_headers(record, headers)
        yield record

    if "raise_error" in range_args.keys():
        raise ValueError(range_args["raise_error"])


def datetime_encoder(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")


class TestTelicentLibAdapterTestCase(unittest.TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.test_data_header = {
            "apiVersion": "v1alpha",
            "specification": "v3.0",
            "identifier": "ItemA",
            "classification": "S",
            "permittedOrgs": [
                "ABC",
                "DEF",
                "HIJ"
            ],
            "permittedNats": [
                "GBR",
                "FRA",
                "IRL"
            ],
            "orGroups": [
                "Apple",
                "SOMETHING"
            ],
            "andGroups": [
                "doctor",
                "admin"
            ],
            "createdDateTime": datetime(2023, 2, 2, 23, 11, 11, 4892).astimezone(timezone.utc),
            "originator": "TestOriginator",
            "custodian": "TestCustodian",
            "policyRef": "TestPolicyRef",
            "dataSet": ["ds1", "ds2"],
            "authRef": ["ref1", "ref2"],
            "dispositionDate": datetime(2023, 1, 1, 23, 11, 11).astimezone(timezone.utc),
            "dispositionProcess": "disp-process-1",
            "dissemination": ["news", "articles"]
        }

        self.bytes_data_header = json.dumps({'DH': self.test_data_header}, default=datetime_encoder).encode('utf-8')
        self.default_headers_with_dh = [
            ('policyInformation', self.bytes_data_header),
            ('Security-Label', b'(classification=S&(permitted_organisations=ABC|'
                               b'permitted_organisations=DEF|permitted_organisations=HIJ)&'
                               b'(permitted_nationalities=GBR|permitted_nationalities=FRA|'
                               b'permitted_nationalities=IRL)&doctor:and&admin:and&(Apple:or|'
                               b'SOMETHING:or))'),
            ('Exec-Path', b'Automatic Adapter-to-In-Memory List'),
            ('Request-Id', b'List:uuid4'), ('traceparent', b'')
        ]

    def __validate_generated_range__(self, sink: ListSink, start: int = 0, stop: int = 10, headers=None):
        self.assertEqual(len(sink.get()), stop - start)

        for i in range(0, stop - start):
            actual = sink.get()[i]
            expected_key = start + i
            expected_value = str(expected_key)
            self.__validate_record__(record=actual, headers=headers, key=expected_key, value=expected_value)

    def __validate_record__(self, record: Record, headers: Any = None, key: Any = None, value: Any = None,
                            raw: Any = None) -> None:
        self.assertIsNotNone(record)
        self.assertEqual(record.headers, headers, "Record headers don't match")
        self.assertEqual(record.key, key, "Record keys don't match")
        self.assertEqual(record.value, value, "Record values don't match")
        self.assertEqual(record.raw, raw, "Raw Records don't match")

    @patch('telicent_lib.adapter.uuid.uuid4')
    def test_automatic_adapter_with_security_policy_01(self, patched_method):
        patched_method.return_value = 'uuid4'
        data_header_model = TelicentModel(**self.test_data_header)
        security_labels = data_header_model.build_security_labels()
        sink = ListSink()
        adapter = AutomaticAdapter(target=sink, adapter_function=custom_range_generator, has_reporter=False,
                                   has_error_handler=False, data_header_model=data_header_model,
                                   security_labels=security_labels, start=100, stop=200)
        adapter.run()
        self.__validate_generated_range__(sink, 100, 200, headers=self.default_headers_with_dh)
