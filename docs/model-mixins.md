### Using the `TelicentMixin` Models

`telicent_labels` ships three ready-to-use models that all derive from a single
`TelicentMixin` base. Each one validates an incoming data header and emits a
Security Label expression that downstream services can attach to a record.

| Model | Module | Header shape |
| --- | --- | --- |
| `TelicentModel` | `telicent_model.py` | Original flat EDH (External Data Header) shape. |
| `IDHModel` | `idh_model.py` | IDH (Information Data Header) — access fields nested under `access`, ownership under `ownership`. |
| `PolicyInformationModel` | `policy_information_model.py` | A wrapper carrying **exactly one** of an `IDH` or an `EDH` and delegating to it. |

In every case the workflow is the same:

1. Build a `dict` (typically from JSON).
2. Instantiate the model — Pydantic raises `ValidationError` if required
   fields are missing or invalid.
3. Call `build_security_labels()` to get the Security Label string.

All three are importable from the package root:

```python
from telicent_labels import IDHModel, TelicentModel, PolicyInformationModel
```

---

#### The `TelicentMixin` contract

`TelicentMixin` (in `telicent_model.py`) is a Pydantic `BaseModel` **and** an
`ABC` with a single abstract method:

```python
class TelicentMixin(BaseModel, ABC):
    @abstractmethod
    def build_security_labels(self):
        ...
```

Because it is abstract, `TelicentMixin` cannot be instantiated directly — every
concrete model (`TelicentModel`, `IDHModel`, `PolicyInformationModel`, or your
own) must implement `build_security_labels()`. This is the single, canonical
mixin: there is one `TelicentMixin`, and all three shipped models subclass it.

---

#### `TelicentModel` (`telicent_model.py`)

`TelicentModel` is the flat EDH shape. It exposes v2 access controls
(`permittedOrgs`, `permittedNats`, `orGroups`, `andGroups`) alongside metadata
fields (`originator`, `custodian`, `policyRef`, `dataSet`, `authRef`,
`dispositionDate`, `dispositionProcess`, `dissemination`).

Validation rules:

- `classification` must be a non-empty string.
- `permittedOrgs` and `permittedNats` must each contain at least one entry.
- `orGroups`, `andGroups`, `dataSet`, `authRef` and `dissemination` are
  **required keys** but may be empty lists — empty group lists simply drop out
  of the expression (no stray `&&` or `()`).

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

security_label = TelicentModel(**data_header).build_security_labels()

# (classification=S
#  &(permitted_organisations=Telicent|permitted_organisations=NHS)
#  &(permitted_nationalities=GBR|permitted_nationalities=USA)
#  &urn:telicent:groups:developer
#  &(urn:telicent:groups:analyst))
print(security_label)
```

Minimum valid payload — `permittedOrgs`/`permittedNats` must be populated, the
remaining lists may be empty:

```python
TelicentModel(
    identifier="doc-002",
    classification="O",
    permittedOrgs=["Telicent"],
    permittedNats=["GBR"],
    orGroups=[],
    andGroups=[],
    dataSet=[],
    authRef=[],
    dissemination=[],
).build_security_labels()
# -> "(classification=O&(permitted_organisations=Telicent)&(permitted_nationalities=GBR))"
```

Validation failures you can expect:

```python
# classification cannot be blank
TelicentModel(..., classification="")
# -> ValidationError: The classification field cannot be an empty string.

# permittedOrgs / permittedNats cannot be empty or contain only blanks
TelicentModel(..., permittedOrgs=[])
# -> ValidationError: The permittedOrgs field cannot be an empty list.
```

---

#### `IDHModel` (`idh_model.py`)

`IDHModel` nests access fields under `access` and ownership under `ownership`.

Validation rules:

- `access.classification` is restricted to `"O"`, `"OS"`, `"S"`, or `"TS"`.
- `access.allowedOrgs` and `access.allowedNats` must each contain at least one
  entry.
- `access.groups` and `access.oneOfGroups` are **required keys** but may be
  empty — only populated group lists appear in the output expression.
- Each entry in `access.groups` and `access.oneOfGroups` is normalised to a
  URN. You do **not** have to pass a full URN — a bare group name is accepted
  and expanded to `urn:telicent:groups:<name>` (see
  [Group names and URN coercion](#group-names-and-urn-coercion) below).
- `ownership.originatingOrg` is required; `ownership.user` is optional.

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
        "oneOfGroups": ["urn:telicent:groups:analyst"],
    },
    "ownership": {
        "originatingOrg": "Telicent",
    },
}

security_label = IDHModel(**data_header).build_security_labels()

# (classification=O
#  &(permitted_organisations=Telicent|permitted_organisations=NHS)
#  &(permitted_nationalities=GBR|permitted_nationalities=FRA)
#  &urn:telicent:groups:developer
#  &urn:telicent:groups:africa
#  &(urn:telicent:groups:analyst))
print(security_label)
```

Minimum valid payload — `groups` and `oneOfGroups` may be empty and are dropped
from the expression, but they (and `allowedOrgs`/`allowedNats`) must still be
present:

```python
IDHModel(
    uuid="doc-124",
    containsPii=False,
    access={
        "classification": "O",
        "allowedOrgs": ["Telicent"],
        "allowedNats": ["GBR"],
        "groups": [],
        "oneOfGroups": [],
    },
    ownership={"originatingOrg": "Telicent"},
).build_security_labels()
# -> "(classification=O&(permitted_organisations=Telicent)&(permitted_nationalities=GBR))"
```

Validation failures you can expect:

```python
# classification must be one of O / OS / S / TS
IDHModel(..., access={"classification": "P", ...})
# -> ValidationError: The classification field must be 'O', 'OS', 'S' or 'TS'.

# access.allowedOrgs / allowedNats / groups / oneOfGroups are required keys
IDHModel(..., access={"classification": "O"}, ownership={"originatingOrg": "Telicent"})
# -> ValidationError mentioning access.allowedOrgs, access.allowedNats,
#    access.groups, access.oneOfGroups
```

<a name="group-names-and-urn-coercion"></a>
##### Group names and URN coercion

Group membership in a Security Label is expressed as a URN (for example
`urn:telicent:groups:developer`). To make headers easier to author, `IDHModel`
normalises every entry in `access.groups` and `access.oneOfGroups` when the
model is created — **you do not need to construct the URN yourself**:

- If the entry is **already a valid Telicent group URN** — i.e. it has the exact
  `urn:telicent:groups:` prefix followed by a URN-safe name — it is kept
  exactly as-is.
- **Anything else is treated as a plain group name** and expanded to
  `urn:telicent:groups:<name>`. Surrounding whitespace is trimmed and any
  internal whitespace is replaced with hyphens (`"data science"` →
  `urn:telicent:groups:data-science`).

Only the `urn:telicent:groups:` namespace is recognised. A URN from any other
namespace (e.g. `urn:example:foo:bar`) is **not** treated as pre-formed — it is
coerced like a bare name and ends up prefixed
(`urn:telicent:groups:urn:example:foo:bar`), so pass group names rather than
foreign URNs.

Every supplied entry is preserved — nothing is dropped — and order is kept.

```python
from telicent_labels import IDHModel

model = IDHModel(
    uuid="doc-125",
    containsPii=False,
    access={
        "classification": "O",
        "allowedOrgs": ["Telicent"],
        "allowedNats": ["GBR"],
        # Mix bare names with a ready-made URN — all end up as URNs.
        "groups": ["developer", "data science", "urn:telicent:groups:africa"],
        "oneOfGroups": ["analyst"],
    },
    ownership={"originatingOrg": "Telicent"},
)

model.access.groups
# -> ['urn:telicent:groups:developer',
#     'urn:telicent:groups:data-science',
#     'urn:telicent:groups:africa']

model.build_security_labels()
# (classification=O
#  &(permitted_organisations=Telicent)
#  &(permitted_nationalities=GBR)
#  &urn:telicent:groups:developer
#  &urn:telicent:groups:data-science
#  &urn:telicent:groups:africa
#  &(urn:telicent:groups:analyst))
```

A group name that cannot form a valid URN raises a `ValidationError`:

```python
# empty / whitespace-only name
IDHModel(..., access={..., "groups": ["   "]})
# -> ValidationError: Group name cannot be empty

# name containing characters that are not URN-safe
IDHModel(..., access={..., "groups": ["bad<>name"]})
# -> ValidationError: Group name 'bad<>name' contains invalid characters
```

The same coercion applies when you build the header with `build_idh_dict`,
since it validates through `IDHModel` — passing `groups=["developer"]` yields a
header whose `access.groups` is `["urn:telicent:groups:developer"]`.

---

#### `PolicyInformationModel` (`policy_information_model.py`)

A CORE data packet carries its policy in **exactly one** of two forms: an IDH
or an EDH, never both. `PolicyInformationModel` models that rule directly. It
accepts an optional `IDH` (an `IDHModel`) and an optional `EDH` (a
`TelicentModel`), enforces that precisely one is supplied, and then delegates
`build_security_labels()` to whichever was provided.

```python
from telicent_labels import IDHModel, PolicyInformationModel, TelicentModel

# Wrap an IDH ...
policy = PolicyInformationModel(IDH=IDHModel(**idh_data_header))
policy.build_security_labels()   # == the wrapped IDHModel's own label

# ... or an EDH.
policy = PolicyInformationModel(EDH=TelicentModel(**edh_data_header))
policy.build_security_labels()   # == the wrapped TelicentModel's own label
```

Nested dicts are coerced to the underlying model, so you can pass raw JSON
straight through:

```python
policy = PolicyInformationModel(
    IDH={
        "uuid": "doc-123",
        "containsPii": False,
        "access": {
            "classification": "O",
            "allowedOrgs": ["Telicent"],
            "allowedNats": ["GBR"],
            "groups": [],
            "oneOfGroups": [],
        },
        "ownership": {"originatingOrg": "Telicent"},
    }
)
isinstance(policy.IDH, IDHModel)          # True
isinstance(policy.policy_object, IDHModel)  # True — points at the supplied model
```

`policy_object` is a convenience attribute set during validation to whichever
of `IDH`/`EDH` was supplied; you normally don't set it yourself.

**Mutual exclusivity.** Supplying both, or neither, raises a `ValidationError`:

```python
# both supplied
PolicyInformationModel(IDH=some_idh, EDH=some_edh)
# -> ValidationError: Only one model can be used per CORE data packet

# neither supplied
PolicyInformationModel()
# -> ValidationError: Only one model can be used per CORE data packet
```

**Open-label fallback.** If a model somehow reaches `build_security_labels()`
with no policy object (for example, one built via `model_construct()` that
bypasses validation), it returns the wildcard `"*"` rather than raising:

```python
PolicyInformationModel.model_construct().build_security_labels()
# -> "*"
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
# -> "(classification=O&urn:telicent:groups:dev)"
```

Because `TelicentMixin` is an `ABC` with `build_security_labels` marked
`@abstractmethod`, forgetting to implement it raises `TypeError` at
instantiation. If your header matches the IDH access/ownership shape, subclass
`IDHModel` instead and inherit its `build_security_labels()` for free.

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
