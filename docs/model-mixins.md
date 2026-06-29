### Using the `TelicentMixin` Models

Both `telicent_labels.telicent_model` and `telicent_labels.idh_model` expose a
`TelicentMixin`-derived Pydantic model whose job is the same: validate an
incoming data header and emit a Security Label expression that downstream
services can attach to a record.

- `TelicentModel` (in `telicent_model.py`) is the original, flat header shape.
- `IDHModel` (in `idh_model.py`) is the IDH (Information Data Header) shape,
  which groups access fields under `access` and ownership fields under
  `ownership`, and restricts `classification` to `O`, `OS`, `S`, or `TS`.

In both cases the workflow is:

1. Build a `dict` (typically from JSON).
2. Instantiate the model — Pydantic raises `ValidationError` if required
   fields are missing or invalid.
3. Call `build_security_labels()` to get the Security Label string.

---

#### `TelicentModel` (`telicent_model.py`)

`TelicentModel` exposes both v2 access controls (`permittedOrgs`,
`permittedNats`, `orGroups`, `andGroups`) and metadata fields (`originator`,
`custodian`, `policyRef`, `dataSet`, `authRef`, `dispositionDate`,
`dispositionProcess`, `dissemination`). All list fields must be non-empty.

```python
from telicent_labels import TelicentModel

data_header = {
    "identifier": "doc-001",
    "classification": "S",
    "permittedOrgs": ["Telicent", "NHS"],
    "permittedNats": ["GBR", "USA"],
    "orGroups": ["urn:telicent:groups:analyst"],
    "andGroups": ["urn:telicent:groups:developer"],
    "dataSet": ["demo-dataset"],
    "authRef": ["auth-ref-1"],
    "dissemination": ["internal"],
}

model = TelicentModel(**data_header)
security_label = model.build_security_labels()

# (classification=S
#  &(permitted_organisations=Telicent|permitted_organisations=NHS)
#  &(permitted_nationalities=GBR|permitted_nationalities=USA)
#  &urn:telicent:groups:developer:and
#  &(urn:telicent:groups:analyst:or))
print(security_label)
```

Minimum valid payload — every list field must contain at least one entry:

```python
TelicentModel(
    identifier="doc-002",
    classification="O",
    permittedOrgs=["Telicent"],
    permittedNats=["GBR"],
    orGroups=["urn:telicent:groups:analyst"],
    andGroups=["urn:telicent:groups:developer"],
    dataSet=["demo"],
    authRef=["auth-1"],
    dissemination=["internal"],
).build_security_labels()
```

Validation failures you can expect:

```python
# classification cannot be blank
TelicentModel(..., classification="")
# -> ValidationError: The classification field cannot be an empty string.

# list fields cannot be empty or contain only blanks
TelicentModel(..., permittedOrgs=[])
# -> ValidationError: The permittedOrgs field cannot be an empty list.
```

---

#### `IDHModel` (`idh_model.py`)

`IDHModel` nests access fields under `access` and ownership under `ownership`.
`classification` is restricted to `"O"`, `"OS"`, `"S"`, or `"TS"`. The
`access.*` list fields are allowed to be empty — only the fields that are
populated end up in the output expression.

```python
from telicent_labels import IDHModel

data_header = {
    "apiVersion": "v1alpha",
    "uuid": "doc-123",
    "creationDate": "2024-09-27 00:00:00+00:00",
    "containsPii": False,
    "dataSource": "Example Source",
    "access": {
        "classification": "O",
        "allowedOrgs": ["Telicent", "NHS"],
        "allowedNats": ["GBR", "FRA"],
        "groups": [
            "urn:telicent:groups:developer",
            "urn:telicent:groups:africa",
        ],
    },
    "ownership": {
        "originatingOrg": "Telicent",
    },
}

security_label = IDHModel(**data_header).build_security_labels()

# (classification=O
#  &(permitted_organisations=Telicent|permitted_organisations=NHS)
#  &(permitted_nationalities=GBR|permitted_nationalities=FRA)
#  &urn:telicent:groups:developer:and
#  &urn:telicent:groups:africa:and)
print(security_label)
```

Classification-only payload — empty `access` lists are dropped from the
expression:

```python
IDHModel(
    uuid="doc-124",
    containsPii=False,
    access={
        "classification": "O",
        "allowedOrgs": [],
        "allowedNats": [],
        "groups": [],
    },
    ownership={"originatingOrg": "Telicent"},
).build_security_labels()
# -> "(classification=O)"
```

Validation failures you can expect:

```python
# classification must be one of O / OS / S / TS
IDHModel(..., access={"classification": "P", ...})
# -> ValidationError: The classification field must be 'O', 'OS', 'S' or 'TS'.

# access.allowedOrgs / allowedNats / groups are required keys
IDHModel(..., access={"classification": "O"}, ownership={"originatingOrg": "Telicent"})
# -> ValidationError mentioning access.allowedOrgs, access.allowedNats, access.groups
```

---

#### Defining your own `TelicentMixin` subclass

The mixin pattern lets you define the shape of your own header while reusing
the `SecurityLabelBuilder` machinery. Subclass `TelicentMixin` and implement
`build_security_labels()`:

```python
from telicent_labels import SecurityLabelBuilder, TelicentSecurityLabelsV2
from telicent_labels.telicent_model import TelicentMixin


class MyHeader(TelicentMixin):
    classification: str
    teams: list[str]

    def build_security_labels(self) -> str:
        return (
            SecurityLabelBuilder()
            .add(TelicentSecurityLabelsV2.CLASSIFICATION.value, self.classification)
            .add_multiple(TelicentSecurityLabelsV2.AND_GROUPS.value, *self.teams)
            .build()
        )


MyHeader(classification="O", teams=["urn:telicent:groups:dev"]).build_security_labels()
# -> "(classification=O&urn:telicent:groups:dev:and)"
```

Note that `telicent_model.TelicentMixin` is an `ABC` with
`build_security_labels` marked `@abstractmethod`, so subclasses must implement
it. `idh_model.TelicentMixin` provides a concrete implementation built around
an `access` attribute — subclass it directly if your header matches the IDH
access shape.

---

#### Attaching the label to a record

Once you have the string, attach it to the outgoing record (Kafka, in the
examples below) under whatever header your platform expects — typically
`Security-Label`:

```python
from telicent_lib.records import Record, RecordUtils

record = Record(headers=None, key=1, value=payload, raw=None)
record = RecordUtils.add_headers(record, [("Security-Label", security_label)])
```

See [telicent-header.md](./telicent-header.md) for end-to-end adapter
examples.
