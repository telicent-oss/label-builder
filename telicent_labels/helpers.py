import logging
import re

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

TELICENT_URN_BASE = "urn:telicent:groups:"

# The permitted characters are a deliberate *strict subset* of RFC 8141 `pchar`
# (`unreserved / pct-encoded / sub-delims / ":" / "@"`). The unreserved `~` and
# the sub-delim `&`, plus the NSS separator `/`, are intentionally excluded as
# they are not expected in group names — so every URN this module produces is
# guaranteed RFC 8141 compliant. See test_helpers for the compliance guard.
URN_REGEX = re.compile(
    r"([a-zA-Z0-9()+,\-.:=@;$_!*']|%[0-9a-fA-F]{2})+$",
    re.IGNORECASE,
)

def _is_valid_urn_segment(segment: str) -> bool:
    return bool(segment) and URN_REGEX.fullmatch(segment) is not None

def is_valid_urn(urn: str) -> bool:
    return bool(urn) and urn.startswith(TELICENT_URN_BASE) \
        and _is_valid_urn_segment(urn[len(TELICENT_URN_BASE):])


def generate_urn(name: str) -> str:
    if name is None or not name.strip():
        raise ValueError("Group name cannot be empty")
    cleaned_name = re.sub(r"\s", "-", name.strip())
    urn = TELICENT_URN_BASE + cleaned_name
    if not is_valid_urn(urn):
        raise ValueError(f"Group name '{name}' contains invalid characters")
    return urn
