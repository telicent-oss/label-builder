import logging
from datetime import datetime, timezone
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, PlainSerializer, field_validator

from telicent_labels.helpers import generate_urn, is_valid_urn
from telicent_labels.security_labels import _SecurityLabelBuilder
from telicent_labels.telicent_model import TelicentMixin
from telicent_labels.telicentv2 import TelicentSecurityLabelsV2

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

DEFAULT_OPTIONAL_DT = datetime(2023, 12, 14, 0, 0, 0, tzinfo=timezone.utc)
SerialisableDt = Annotated[AwareDatetime, PlainSerializer(lambda x: x.isoformat(), return_type=str, when_used="always")]



class AccessModel(BaseModel):
    classification: str
    allowedOrgs: list[str]
    allowedNats: list[str]
    groups: list[str]
    oneOfGroups: list[str]

    @field_validator('classification')
    def non_empty_string(cls, value: str, info):
        if value.strip() == "":
            raise ValueError(f"The {info.field_name} field cannot be an empty string.")
        if value.strip() not in ("O", "OS", "S", "TS"):
            raise ValueError(f"The {info.field_name} field must be 'O', 'OS', 'S' or 'TS'.")
        return value

    @field_validator('allowedOrgs', 'allowedNats', mode='before')
    def non_empty_list(cls, value: list[str], info):
        clean_list = [x for x in value if x]
        if not clean_list or len(clean_list) == 0:
            raise ValueError(f"The {info.field_name} field cannot be an empty list.")
        return value

    @field_validator('groups', 'oneOfGroups', mode="before")
    def ensure_urns(cls, value: list[str], info):
        clean_list = [group if is_valid_urn(group) else generate_urn(group) for group in value]
        return clean_list


class OwnershipModel(BaseModel):
    originatingOrg: str
    user: str | None = None

class IDHModel(TelicentMixin):

    apiVersion: str = "v1alpha"
    uuid: str
    creationDate: SerialisableDt = DEFAULT_OPTIONAL_DT
    containsPii: bool
    dataSource: str | None = None
    ownership: OwnershipModel
    access: AccessModel

    def build_security_labels(self):
        builder = _SecurityLabelBuilder()

        builder.add(TelicentSecurityLabelsV2.CLASSIFICATION.value, self.access.classification)
        builder.add_multiple(TelicentSecurityLabelsV2.PERMITTED_ORGANISATIONS.value, *self.access.allowedOrgs)
        builder.add_multiple(TelicentSecurityLabelsV2.PERMITTED_NATIONALITIES.value, *self.access.allowedNats)
        builder.add_multiple(TelicentSecurityLabelsV2.AND_GROUPS.value, *self.access.groups)
        builder.add_multiple(TelicentSecurityLabelsV2.OR_GROUPS.value, *self.access.oneOfGroups)

        return builder.build()
