import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, PlainSerializer, field_validator

from telicent_labels.security_labels import _SecurityLabelBuilder
from telicent_labels.telicentv2 import TelicentSecurityLabelsV2
from telicent_labels.helpers import generate_urn, is_valid_urn

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


class TelicentMixin(BaseModel, ABC):
    @abstractmethod
    def build_security_labels(self):
        pass


class TelicentModel(TelicentMixin):
    apiVersion: str = "v1alpha"
    specification: str = "IHM"
    identifier: str
    classification: str
    permittedOrgs: list[str]
    permittedNats: list[str]
    orGroups: list[str]
    andGroups: list[str]

    createdDateTime: SerialisableDt = DEFAULT_OPTIONAL_DT
    originator: str | None = None
    custodian: str | None = None
    policyRef: str | None = None
    dataSet: list[str]
    authRef: list[str]
    dispositionDate: SerialisableDt | None = DEFAULT_OPTIONAL_DT
    dispositionProcess: str | None = None
    dissemination: list[str]

    @field_validator('classification')
    def non_empty_string(cls, value: str, info):
        if value.strip() == "":
            raise ValueError(f"The {info.field_name} field cannot be an empty string.")
        return value

    @field_validator('permittedOrgs', 'permittedNats', mode='before')
    def non_empty_list(cls, value: list[str], info):
        clean_list = [x for x in value if x]
        if not clean_list or len(clean_list) == 0:
            raise ValueError(f"The {info.field_name} field cannot be an empty list.")
        return value
    
    @field_validator('andGroups', 'orGroups', mode="before")
    def ensure_urns(cls, value: list[str], info):
        clean_list = [group if is_valid_urn(group) else generate_urn(group) for group in value]
        return clean_list

    def build_security_labels(self):
        builder = _SecurityLabelBuilder()

        builder.add(TelicentSecurityLabelsV2.CLASSIFICATION.value, self.classification)
        builder.add_multiple(TelicentSecurityLabelsV2.PERMITTED_ORGANISATIONS.value, *self.permittedOrgs)
        builder.add_multiple(TelicentSecurityLabelsV2.PERMITTED_NATIONALITIES.value, *self.permittedNats)
        builder.add_multiple(TelicentSecurityLabelsV2.AND_GROUPS.value, *self.andGroups)
        builder.add_multiple(TelicentSecurityLabelsV2.OR_GROUPS.value, *self.orGroups)

        return builder.build()
