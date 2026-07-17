### `TelicentModel` and `IDHModel` schema reference

This page documents the field-level schema of the two concrete data-header
models — `TelicentModel` (the flat EDH shape) and `IDHModel` (the nested IDH
shape) — including the **cardinality** of every field.

Both models are Pydantic `BaseModel`s. "Cardinality" here describes two things
at once:

| Notation | Meaning |
| --- | --- |
| `1..1` | Required scalar — the key must be present and non-null. |
| `0..1` | Optional scalar — the key may be omitted; a default (often `None`) is used. |
| `1..*` | List key that **must be present** and contain **at least one** non-empty element. |
| `0..*` | List key that **must be present** but **may be empty** (`[]`). |

> **Required key vs. non-empty list.** A `0..*` field is still a *required key*:
> omitting it raises `ValidationError`. It differs from `1..*` only in that an
> empty list `[]` is accepted. The only truly optional fields (key may be
> omitted entirely) are the `0..1` scalars, which carry defaults.

The two shared datetime defaults referenced below come from the model modules:

- `DEFAULT_OPTIONAL_DT` = `2023-12-14T00:00:00+00:00`
- Datetime fields are `AwareDatetime` (a timezone must be present) and serialise
  to ISO-8601 strings via `.isoformat()`.

---

#### `TelicentModel` (`telicent_model.py`)

A single flat object. Access controls, metadata and disposition fields sit at
the top level.

| Field | Type | Cardinality | Default | Notes |
| --- | --- | --- | --- | --- |
| `apiVersion` | `str` | `1` | `"v1alpha"` | |
| `specification` | `str` | `1` | `"IHM"` | |
| `identifier` | `str` | `1` | — | |
| `classification` | `str` | `1` | — | Must be a non-empty string (after stripping). |
| `permittedOrgs` | `list[str]` | `1..*` | — | At least one non-empty entry; blank entries are stripped before the emptiness check. |
| `permittedNats` | `list[str]` | `1..*` | — | At least one non-empty entry; blank entries are stripped before the emptiness check. |
| `orGroups` | `list[str]` | `0..*` | — | Required key; may be `[]`. Empty ⇒ dropped from the label expression. |
| `andGroups` | `list[str]` | `0..*` | — | Required key; may be `[]`. Empty ⇒ dropped from the label expression. |
| `createdDateTime` | `datetime` | `1` | `DEFAULT_OPTIONAL_DT` | Timezone-aware; serialises to ISO-8601. |
| `originator` | `str` | `0..1` | `None` | |
| `custodian` | `str` | `0..1` | `None` | |
| `policyRef` | `str` | `0..1` | `None` | |
| `dataSet` | `list[str]` | `0..*` | — | Required key; may be `[]`. |
| `authRef` | `list[str]` | `0..*` | — | Required key; may be `[]`. |
| `dispositionDate` | `datetime` | `0..1` | `DEFAULT_OPTIONAL_DT` | Timezone-aware; serialises to ISO-8601. |
| `dispositionProcess` | `str` | `0..1` | `None` | |
| `dissemination` | `list[str]` | `0..*` | — | Required key; may be `[]`. |

**Only these fields feed the Security Label expression:** `classification`,
`permittedOrgs`, `permittedNats`, `andGroups`, `orGroups`. The remaining fields
are metadata carried on the header but not reflected in the label.

Minimum valid payload (every `1..1`/`1..*` field plus the required-but-emptyable
`0..*` keys):

```python
TelicentModel(
    identifier="doc-002",
    classification="O",
    permittedOrgs=["Telicent"],   # 1..*
    permittedNats=["GBR"],        # 1..*
    orGroups=[],                  # 0..* (key required)
    andGroups=[],                 # 0..* (key required)
    dataSet=[],                   # 0..* (key required)
    authRef=[],                   # 0..* (key required)
    dissemination=[],             # 0..* (key required)
)
```

---

#### `IDHModel` (`idh_model.py`)

A nested object: access controls live under `access` (an `AccessModel`) and
ownership under `ownership` (an `OwnershipModel`).

##### Top level

| Field | Type | Cardinality | Default | Notes |
| --- | --- | --- | --- | --- |
| `apiVersion` | `str` | `1` | `"v1alpha"` | |
| `uuid` | `str` | `1` | — | |
| `creationDate` | `datetime` | `1` | `DEFAULT_OPTIONAL_DT` | Timezone-aware; serialises to ISO-8601. |
| `containsPii` | `bool` | `1` | — | Required; no default. |
| `dataSource` | `str` | `0..1` | `None` | |
| `ownership` | `OwnershipModel` | `1` | — | Required nested object (see below). |
| `access` | `AccessModel` | `1` | — | Required nested object (see below). |

##### `access` (`AccessModel`)

| Field | Type | Cardinality | Default | Notes |
| --- | --- | --- | --- | --- |
| `classification` | `str` | `1` | — | Must be one of `"O"`, `"OS"`, `"S"`, `"TS"`. |
| `allowedOrgs` | `list[str]` | `1..*` | — | At least one non-empty entry. |
| `allowedNats` | `list[str]` | `1..*` | — | At least one non-empty entry. |
| `groups` | `list[str]` | `0..*` | — | Required key; may be `[]`. Empty ⇒ dropped from the label expression. Each entry is normalised to a URN (see note below). |
| `oneOfGroups` | `list[str]` | `0..*` | — | Required key; may be `[]`. Empty ⇒ dropped from the label expression. Each entry is normalised to a URN (see note below). |

> **Group names are coerced to Telicent URNs.** Entries in `access.groups` and
> `access.oneOfGroups` need not be full URNs. A value that is already a valid
> Telicent group URN (`urn:telicent:groups:<name>`) is kept as-is; any other
> value — including a URN from a different namespace — is treated as a bare
> group name and expanded to `urn:telicent:groups:<name>` (whitespace trimmed,
> internal whitespace hyphenated). A name that cannot form a valid URN raises
> `ValidationError`. See
> [model-mixins.md](./model-mixins.md#group-names-and-urn-coercion).

##### `ownership` (`OwnershipModel`)

| Field | Type | Cardinality | Default | Notes |
| --- | --- | --- | --- | --- |
| `originatingOrg` | `str` | `1` | — | |
| `user` | `str` | `0..1` | `None` | |

**Access-control mapping.** `IDHModel` produces the same label vocabulary as
`TelicentModel`, via these field correspondences:

| `IDHModel` (`access.*`) | `TelicentModel` | Label term |
| --- | --- | --- |
| `classification` | `classification` | `classification=…` |
| `allowedOrgs` | `permittedOrgs` | `permitted_organisations=…` |
| `allowedNats` | `permittedNats` | `permitted_nationalities=…` |
| `groups` | `andGroups` | `urn…` (AND: bare URNs joined with `&`) |
| `oneOfGroups` | `orGroups` | `(urn…\|urn…)` (OR: bracketed, joined with `\|`) |

Minimum valid payload:

```python
IDHModel(
    uuid="doc-124",
    containsPii=False,
    access={
        "classification": "O",
        "allowedOrgs": ["Telicent"],   # 1..*
        "allowedNats": ["GBR"],        # 1..*
        "groups": [],                  # 0..* (key required)
        "oneOfGroups": [],             # 0..* (key required)
    },
    ownership={"originatingOrg": "Telicent"},  # 1..1, user optional
)
```

---

See [model-mixins.md](./model-mixins.md) for worked examples, validation
behaviour and the resulting Security Label expressions, and
[telicent-enums.md](./telicent-enums.md) for the label vocabulary itself.
