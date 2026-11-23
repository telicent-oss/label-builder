### Why `parse_security_labels` is exact

`parse_security_labels` is the reverse of `build_security_labels`. This page is the argument that
it recovers the fields exactly, for every label the builder writes, rather than a claim resting on
examples; the examples are in `test/test_parse.py`, including a bounded exhaustive check.

#### What the builder writes

For fields `(c, O, N, A, R)` (classification, permitted organisations, permitted nationalities,
and-groups, one-of groups) the models write, in the order of their `add` calls:

```
"(" c-label "=" c
    [ "&(" org-label "=" o1 "|" org-label "=" o2 ... ")" ]      if O is given
    [ "&(" nat-label "=" n1 "|" ... ")" ]                      if N is given
    [ "&" a1 "&" a2 ... ]                                      if A is given: the group URNs, bare
    [ "&(" r1 "|" r2 ... ")" ]                                  if R is given
")"
```

Empty parts are omitted. The v1 labels use `clearance`, `deployed_organisation` and `nationality`
and have no groups. A label built by hand with the builder may put the parts in any order;
`add_or_expression` joins whole bracketed expressions with `|` at the top level.

Older versions of the builder wrote each and-group as `a1:and` and each one-of group as `r1:or`.
Labels in that form exist in stored data and are read too; `ParsedLabel.group_suffixes` reports
which form a label used.

Values that are rdf-abac words are written bare; any other value, and any group URN that is not a
word, is written as an rdf-abac quoted string with escapes.

#### The domain

rdf-abac reads a bare value only if it is a *word*: a letter or underscore, then letters, digits and
`_ : . - +`, ending with a letter, digit or underscore, and not `true` or `false` (rdf-abac
specification, "Attribute Expressions", as its parser implements it). Every delimiter the builder
uses, `(`, `)`, `&`, `|` and `=`, is outside that alphabet. A quoted string may contain anything,
but it starts and ends with `"` and its inner quotes are escaped, so where a quoted string starts
and ends is unambiguous.

#### The claim

On that domain the builder's function is injective, and the procedure below is its inverse.

#### The procedure

1. Split the text on `|` at bracket depth zero, outside quoted strings: one piece per alternative.
2. For each alternative, strip its outer `(` and `)`, which must enclose the whole of it, and split on
   `&` at depth zero outside quoted strings.
3. Classify each piece by how it starts. A piece starting `(` is a list: split its inside on `|` at
   depth zero; if every alternative is `label=value` with one label name throughout, it is the
   organisations or nationalities list of that name; if every alternative is a bare or quoted
   attribute, it is the one-of groups list. A piece containing `=` and not starting with a quote is
   `label=value`, the classification. Any other piece is a bare or quoted attribute, one and-group.
4. Unquote a quoted value. For groups, if every group in the label ends with its older suffix
   (`:and` for and-groups, `:or` for one-of groups), strip exactly that suffix; if none does, the
   groups are as written; a label that mixes the two is refused.

#### Why each step is unambiguous

- Step 1 and 2: `|`, `&`, `(` and `)` never occur in a bare value, and inside a quoted string they are
  skipped, so every delimiter found is one the builder wrote, and bracket depth is well defined.
- Step 3: the kinds of piece start differently (`(`, a label name followed by `=`, a bare word, a
  quote), a bare value cannot start with `(`, and the label names are fixed text. Within a list the
  label name is repeated for every alternative by `MultiValueLabel.construct`, so a list of one kind
  cannot be mistaken for another. Each model calls `add_multiple` once per label, so a list of a kind
  occurs at most once; a second one is refused.
- Step 4: `=` never occurs in a bare value, so the first `=` of `label=value` is the builder's.
  In the older form a group may itself contain `:`, so `urn:x:and:and` is a valid piece whose group
  is `urn:x:and`; the piece is the group with exactly `:and` appended, so removing exactly the last
  four characters (three for `:or`) recovers it. Unquoting undoes exactly the escapes `quote`
  applied.

Every step recovers exactly what the builder put in, so composing them gives the fields back, and
two different field sets cannot produce the same text. Order and repeats are preserved because
nothing sorts or deduplicates.

#### The one thing the text cannot decide

The two group forms collide in one case. An older label whose and-group was `urn:telicent:groups:x`
reads `urn:telicent:groups:x:and`; a current label whose group is literally named
`urn:telicent:groups:x:and`, which the URN grammar allows, reads exactly the same. The parser takes
the older reading whenever a suffix is present, which is right for every label written before the
suffixes were dropped, and `group_suffixes` says that it did. A builder that refused group names
ending in `:and` or `:or` would remove the case altogether.

#### What else the argument does not cover

- A label written before values were quoted, with `|`, `&` or `=` inside a value or a group. Such a
  value is outside the word grammar; rdf-abac read it as more than one attribute, so the label did not
  mean the fields it was built from. The parser refuses it (`NotBuilderShape`) rather than guessing.
- An expression the builder did not write: a hand-written one, a part given twice, groups in a v1
  label. Refused the same way.
- Which model wrote a label. `TelicentModel` and `IDHModel` write the same text for the same
  non-empty parts; the parser returns the fields, which is what a reader needs. A group name the
  model normalised into a URN comes back as the URN the label holds.

#### The machine check

`test_parse.py` runs the procedure over a bounded domain in full, not a sample: every word of up to
three characters built from one character of each grammar class, the awkward words `x:and`, `x:or` and
`a:and:and` as values, every list up to a fixed length with order and repeats, the three label
shapes. A larger run of the same check over the older form (24.9 million cases, 2026-11-23) found no
failure.
