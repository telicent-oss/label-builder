import logging
from typing import Optional

from pydantic import model_validator

from telicent_labels.idh_model import IDHModel
from telicent_labels.telicent_model import TelicentModel, TelicentMixin
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

class PolicyInformationModel(TelicentMixin):
    IDH: Optional[IDHModel] = None
    EDH: Optional[TelicentModel] = None
    policy_object: TelicentMixin | None = None

    @model_validator(mode="after")
    def check_mutually_exclusive(self):
        if (self.IDH is None) == (self.EDH is None):
            raise ValueError("Only one model can be used per CORE data packet")
        self.policy_object = self.IDH or self.EDH
        log.debug("PolicyInformation using %s object", "IDH" if self.IDH else "EDH")
        return self

    def build_security_labels(self):
        if not self.policy_object:
            return "*"
        return self.policy_object.build_security_labels()

