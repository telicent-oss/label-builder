"""The reverse of the builder: an rdf-abac security label expression that ``SecurityLabelBuilder``
wrote, back to the fields it was built from.

Why it is exact. rdf-abac reads a bare value only if it is a word (letters, digits, ``_ : . - +``,
not starting with a digit or ending with ``: . - +``), and the builder's delimiters ``( ) & | =`` are
not word characters, so every delimiter in the text is one the builder wrote and the text is an
unambiguous encoding of the fields: split on ``&`` at bracket depth zero, split a bracketed list on
``|``, strip the fixed prefix or suffix of each piece. Quoted values (``"..."``) are unescaped.
Order and repeats are kept. Anything that is not the builder's shape, such as a hand-written
expression or a value an older builder wrote unquoted with ``|`` or ``&`` in it, raises
``NotBuilderShape`` rather than guessing.

Groups come in two forms: the older builder wrote ``group:and`` and ``(group:or|...)``; the current
one writes the group URNs bare, ``group&group`` and ``(group|group)``. Both are read, and
``ParsedLabel.group_suffixes`` says which was found. The text alone cannot tell an older label whose
group was ``urn:x`` from a current label whose group is literally ``urn:x:and``; a trailing ``:and``
or ``:or`` is read as the older form, which is right for every label written before the suffixes
were dropped.
"""
from __future__ import annotations

from dataclasses import dataclass, field

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

# Label names by generation: the CORE-era TelicentLabelsV1 and TelicentSecurityLabelsV2.
GENERATIONS = {
    "v2": ("classification", "permitted_organisations", "permitted_nationalities"),
    "v1": ("clearance", "deployed_organisation", "nationality"),
}


class NotBuilderShape(ValueError):
    """The expression is not one the builder writes; nothing is guessed about it."""


@dataclass
class ParsedLabel:
    """One alternative of a label: the fields the builder was given. Lists keep order and repeats."""
    generation: str
    classification: str | None = None
    permitted_organisations: list[str] = field(default_factory=list)
    permitted_nationalities: list[str] = field(default_factory=list)
    and_groups: list[str] = field(default_factory=list)
    or_groups: list[str] = field(default_factory=list)
    """True if the groups carried the older ``:and`` / ``:or`` suffixes, False if written bare,
    None if the label has no groups."""
    group_suffixes: bool | None = None


def parse_security_labels(expression: str) -> list[ParsedLabel]:
    """The fields of each top-level alternative of ``expression``.

    A label built with ``add`` and ``add_multiple`` alone gives one element; one built with
    ``add_or_expression`` gives one element per alternative, in order.
    """
    text = expression.strip()
    if not text:
        raise NotBuilderShape("empty expression")
    return [_parse_alternative(alt) for alt in _split_top(text, "|")]


def _parse_alternative(text: str) -> ParsedLabel:
    if not (text.startswith("(") and text.endswith(")")) or _depth_closes_early(text):
        raise NotBuilderShape("an alternative is one bracketed expression")
    pieces = _split_top(text[1:-1], "&")
    parsed: ParsedLabel | None = None
    seen: set[str] = set()
    for piece in pieces:
        if not piece:
            raise NotBuilderShape("empty piece")
        if piece.startswith("("):
            if not piece.endswith(")") or _depth_closes_early(piece):
                raise NotBuilderShape("unbalanced list")
            alternatives = _split_top(piece[1:-1], "|")
            name, values, suffixed = _list_name_and_values(alternatives)
            parsed = parsed or ParsedLabel(_generation_of(name))
            kind = _list_kind(parsed.generation, name)
            if kind in seen:
                raise NotBuilderShape(f"{kind} given twice")
            seen.add(kind)
            if kind == "or_groups":
                _note_group_form(parsed, suffixed)
            getattr(parsed, kind).extend(values)
        elif "=" in piece and not piece.startswith('"'):
            name, value = piece.split("=", 1)
            parsed = parsed or ParsedLabel(_generation_of(name))
            if name != GENERATIONS[parsed.generation][0]:
                raise NotBuilderShape(f"unknown single-value label {name}")
            if "classification" in seen:
                raise NotBuilderShape("classification given twice")
            seen.add("classification")
            parsed.classification = _unquote(value)
        else:
            # A bare attribute is an and-group: ``group:and`` from the older builder, or the group
            # URN itself from the current one.
            attr = _unquote(piece)
            parsed = parsed or ParsedLabel("v2")
            if parsed.generation != "v2":
                raise NotBuilderShape("groups in a v1 label")
            if attr.endswith(":and"):
                _note_group_form(parsed, True)
                parsed.and_groups.append(attr[:-4])
            else:
                _note_group_form(parsed, False)
                parsed.and_groups.append(attr)
    if parsed is None:
        raise NotBuilderShape("no labels")
    return parsed


def _note_group_form(parsed: ParsedLabel, suffixed: bool) -> None:
    """Records whether the groups carry suffixes; one label never mixes the two forms."""
    if parsed.group_suffixes is None:
        parsed.group_suffixes = suffixed
    elif parsed.group_suffixes != suffixed:
        raise NotBuilderShape("groups with and without the :and/:or suffixes in one label")


def _list_name_and_values(alternatives: list[str]) -> tuple[str, list[str], bool]:
    """A bracketed list is either ``name=v|name=v...`` (one name throughout) or or-groups, with or
    without the older ``:or`` suffix; the third element says whether the suffix was there."""
    if all(a.startswith('"') or "=" not in a for a in alternatives):
        attrs = [_unquote(a) for a in alternatives]
        suffixed = [a.endswith(":or") for a in attrs]
        if all(suffixed):
            return "or_groups", [a[:-3] for a in attrs], True
        if not any(suffixed):
            return "or_groups", attrs, False
        raise NotBuilderShape("or-groups with and without the :or suffix in one list")
    name: str | None = None
    values = []
    for a in alternatives:
        if "=" not in a or a.startswith('"'):
            raise NotBuilderShape("mixed list")
        n, v = a.split("=", 1)
        if name is None:
            name = n
        elif n != name:
            raise NotBuilderShape("a list with two label names")
        values.append(_unquote(v))
    if name is None:
        raise NotBuilderShape("empty list")
    return name, values, False


def _list_kind(generation: str, name: str) -> str:
    if name == "or_groups":
        if generation != "v2":
            raise NotBuilderShape("or-groups in a v1 label")
        return "or_groups"
    _, orgs, nats = GENERATIONS[generation]
    if name == orgs:
        return "permitted_organisations"
    if name == nats:
        return "permitted_nationalities"
    raise NotBuilderShape(f"unknown list label {name}")


def _generation_of(name: str) -> str:
    if name == "or_groups":
        return "v2"
    for gen, names in GENERATIONS.items():
        if name in names:
            return gen
    raise NotBuilderShape(f"unknown label {name}")


def _split_top(text: str, sep: str) -> list[str]:
    """Splits on ``sep`` at bracket depth zero, outside quoted strings."""
    out, cur, depth, quoted = [], [], 0, False
    i = 0
    while i < len(text):
        ch = text[i]
        if quoted:
            cur.append(ch)
            if ch == "\\" and i + 1 < len(text):
                cur.append(text[i + 1])
                i += 1
            elif ch == '"':
                quoted = False
        elif ch == '"':
            quoted = True
            cur.append(ch)
        elif ch == "(":
            depth += 1
            cur.append(ch)
        elif ch == ")":
            depth -= 1
            if depth < 0:
                raise NotBuilderShape("unbalanced brackets")
            cur.append(ch)
        elif ch == sep and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    if depth != 0 or quoted:
        raise NotBuilderShape("unbalanced brackets or quotes")
    out.append("".join(cur))
    return out


def _depth_closes_early(text: str) -> bool:
    """True if the opening bracket of ``text`` closes before its end: ``(a)&(b)`` is not one list."""
    depth, quoted, i = 0, False, 0
    while i < len(text):
        ch = text[i]
        if quoted:
            if ch == "\\":
                i += 1
            elif ch == '"':
                quoted = False
        elif ch == '"':
            quoted = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and i < len(text) - 1:
                return True
        i += 1
    return False


def _unquote(value: str) -> str:
    """A bare word as it is; a quoted string with rdf-abac's escapes undone."""
    if not (len(value) >= 2 and value[0] == '"' and value[-1] == '"'):
        if '"' in value:
            raise NotBuilderShape("a quote inside a bare value")
        return value
    out, i, body = [], 0, value[1:-1]
    while i < len(body):
        ch = body[i]
        if ch == "\\":
            i += 1
            if i >= len(body):
                raise NotBuilderShape("bad escape")
            e = body[i]
            if e == "n":
                out.append("\n")
            elif e == "t":
                out.append("\t")
            elif e == "r":
                out.append("\r")
            elif e == "u":
                out.append(chr(int(body[i + 1:i + 5], 16)))
                i += 4
            elif e == "U":
                out.append(chr(int(body[i + 1:i + 9], 16)))
                i += 8
            else:
                out.append(e)
        else:
            out.append(ch)
        i += 1
    return "".join(out)
