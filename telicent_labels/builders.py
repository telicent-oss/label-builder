import logging
from datetime import datetime, timezone
from uuid import uuid4

from telicent_labels.idh_model import IDHModel
from telicent_labels.telicent_model import TelicentModel

__license__ = """
Copyright (c) Telicent Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

log = logging.getLogger(__name__)


def _as_iso(value: datetime | str | None) -> str | None:
    """Normalise a datetime (or already-formatted string) to an ISO string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def build_idh_dict(
    *,
    uuid: str | None = None,
    classification: str,
    allowed_orgs: list[str],
    allowed_nats: list[str],
    originating_org: str,
    contains_pii: bool = False,
    groups: list[str] | None = None,
    one_of_groups: list[str] | None = None,
    user: str | None = None,
    data_source: str | None = None,
    creation_date: datetime | str | None = None,
    validate: bool = True,
) -> dict:
    """Build a JSON object shaped for :class:`IDHModel`.

    Flattens the nested ``access``/``ownership`` structure into keyword
    arguments and returns a plain ``dict`` ready to serialise or to pass to
    ``IDHModel(**result)``.

    ``uuid`` defaults to a freshly generated UUID4 when not provided.
    ``groups`` and ``one_of_groups`` default to empty lists (required keys that
    the model permits to be empty). ``creation_date`` defaults to the current
    UTC time when not provided. Other optional scalar fields are only included
    when supplied.

    When ``validate`` is True (the default) the assembled object is passed
    through ``IDHModel`` so that a malformed payload raises ``ValidationError``
    up front rather than later at use time.
    """
    label: dict = {
        "apiVersion": "v1alpha",
        "uuid": uuid or str(uuid4()),
        "containsPii": contains_pii,
        "access": {
            "classification": classification,
            "allowedOrgs": list(allowed_orgs),
            "allowedNats": list(allowed_nats),
            "groups": list(groups) if groups is not None else [],
            "oneOfGroups": list(one_of_groups) if one_of_groups is not None else [],
        },
        "ownership": {
            "originatingOrg": originating_org,
        },
    }

    if data_source is not None:
        label["dataSource"] = data_source
    label["creationDate"] = _as_iso(creation_date) or datetime.now(timezone.utc).isoformat()
    if user is not None:
        label["ownership"]["user"] = user

    if validate:
        IDHModel(**label)

    return label


def build_telicent_dict(
    *,
    identifier: str | None = None,
    classification: str,
    permitted_orgs: list[str],
    permitted_nats: list[str],
    or_groups: list[str] | None = None,
    and_groups: list[str] | None = None,
    data_set: list[str] | None = None,
    auth_ref: list[str] | None = None,
    dissemination: list[str] | None = None,
    created_date_time: datetime | str | None = None,
    originator: str | None = None,
    custodian: str | None = None,
    policy_ref: str | None = None,
    disposition_date: datetime | str | None = None,
    disposition_process: str | None = None,
    specification: str | None = None,
    validate: bool = True,
) -> dict:
    """Build a JSON object shaped for :class:`TelicentModel` (flat EDH).

    Returns a plain ``dict`` ready to serialise or to pass to
    ``TelicentModel(**result)``.

    ``identifier`` defaults to a freshly generated UUID4 when not provided.
    ``or_groups``, ``and_groups``, ``data_set``, ``auth_ref`` and
    ``dissemination`` are required keys that may be empty; they default to empty
    lists. ``created_date_time`` defaults to the current UTC time when not
    provided. Other optional scalar fields are only included when supplied.

    When ``validate`` is True (the default) the assembled object is passed
    through ``TelicentModel`` so that a malformed payload raises
    ``ValidationError`` up front rather than later at use time.
    """
    label: dict = {
        "apiVersion": "v1alpha",
        "identifier": identifier or str(uuid4()),
        "classification": classification,
        "permittedOrgs": list(permitted_orgs),
        "permittedNats": list(permitted_nats),
        "orGroups": list(or_groups) if or_groups is not None else [],
        "andGroups": list(and_groups) if and_groups is not None else [],
        "dataSet": list(data_set) if data_set is not None else [],
        "authRef": list(auth_ref) if auth_ref is not None else [],
        "dissemination": list(dissemination) if dissemination is not None else [],
    }

    if specification is not None:
        label["specification"] = specification
    if originator is not None:
        label["originator"] = originator
    if custodian is not None:
        label["custodian"] = custodian
    if policy_ref is not None:
        label["policyRef"] = policy_ref
    if disposition_process is not None:
        label["dispositionProcess"] = disposition_process
    label["createdDateTime"] = _as_iso(created_date_time) or datetime.now(timezone.utc).isoformat()
    disposition = _as_iso(disposition_date)
    if disposition is not None:
        label["dispositionDate"] = disposition

    if validate:
        TelicentModel(**label)

    return label
