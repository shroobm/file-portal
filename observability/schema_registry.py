#!/usr/bin/env python3
"""A4: generate and verify the filesystem-contract key registry.

The registry is evidence, not a second source of truth.  Every writer key below is extracted
from the Python syntax that actually builds the persisted/stdout record.  Every consumer key is
extracted from the source that reads it.  ``--check`` fails if either side drifts or if a dynamic
spread cannot be resolved; it never imports converter code and never opens the live pipeline.

Signed A4 scope (relay MSG-FAB-0055): events.jsonl, coverage_rescore --json, slice .done,
progress files, and conversion-ledger.jsonl.  The newer .intake-state.json receipt and the
convert estimate are named exclusions rather than being silently implied by "progress".
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REGISTRY_REL = Path("observability/schemas.json")
WRITER_SOURCES = (
    "windows-converter/events.py",
    "windows-converter/watch_and_convert.py",
    "windows-converter/convert_and_ship.py",
    "windows-converter/analyst.py",
    "windows-converter/coverage_rescore.py",
    "windows-converter/figure_coverage.py",
)
CONSUMER_SOURCES = (
    "windows-converter/convert_and_ship.py",
    "windows-converter/coverage_rescore.py",
    "windows-widget/src-tauri/src/algedonic.rs",
    "windows-widget/src-tauri/src/assay.rs",
    "windows-widget/src-tauri/src/events.rs",
    "windows-widget/src-tauri/src/line.rs",
    "windows-widget/src-tauri/src/room.rs",
    "windows-widget/src/event-vocab.js",
    "windows-widget/src/main.js",
    "windows-widget/src/room.js",
)


class RegistryError(RuntimeError):
    """The source cannot prove a complete writer/consumer key contract."""


@dataclass(frozen=True)
class EventShape:
    required: frozenset[str]
    possible: frozenset[str]


@dataclass(frozen=True)
class PathShape:
    """Nested paths which exist on every branch and on at least one branch."""

    required: frozenset[str]
    possible: frozenset[str]


def _read(root: Path, relative: str) -> str:
    path = root / relative
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RegistryError(f"UNREAD source {relative}: {exc}") from exc


def _tree(root: Path, relative: str) -> ast.Module:
    try:
        return ast.parse(_read(root, relative), filename=relative)
    except SyntaxError as exc:
        raise RegistryError(f"UNREAD syntax {relative}:{exc.lineno}: {exc.msg}") from exc


def _functions(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _function(tree: ast.Module, name: str, source: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    found = _functions(tree).get(name)
    if found is None:
        raise RegistryError(f"writer function disappeared: {source}:{name}")
    return found


def _literal_string(node: ast.AST | None) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _dict_keys(node: ast.Dict, *, context: str) -> set[str]:
    keys: set[str] = set()
    for key in node.keys:
        if key is None:
            raise RegistryError(f"unresolved nested dict spread in {context}")
        value = _literal_string(key)
        if value is None:
            raise RegistryError(f"non-literal dict key in {context} at line {getattr(key, 'lineno', '?')}")
        keys.add(value)
    return keys


def _dict_paths(node: ast.Dict, *, context: str, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    for key, value in zip(node.keys, node.values):
        if key is None:
            raise RegistryError(f"unresolved nested dict spread in {context}")
        name = _literal_string(key)
        if name is None:
            raise RegistryError(f"non-literal dict key in {context} at line {getattr(key, 'lineno', '?')}")
        path = f"{prefix}.{name}" if prefix else name
        paths.add(path)
        if isinstance(value, ast.Dict):
            paths.update(_dict_paths(value, context=context, prefix=path))
    return paths


def _return_dicts(function: ast.AST, *, context: str) -> list[ast.Dict]:
    returns = [node.value for node in ast.walk(function) if isinstance(node, ast.Return)]
    dicts = [node for node in returns if isinstance(node, ast.Dict)]
    if not dicts:
        raise RegistryError(f"no literal return dict in {context}")
    return dicts


def _return_paths(tree: ast.Module, name: str, source: str) -> set[str]:
    function = _function(tree, name, source)
    paths: set[str] = set()
    for node in _return_dicts(function, context=f"{source}:{name}"):
        paths.update(_dict_paths(node, context=f"{source}:{name}"))
    return paths


def _prefix_path_shape(shape: PathShape, prefix: str) -> PathShape:
    def prefixed(path: str) -> str:
        if path.startswith("[]"):
            return f"{prefix}{path}"
        return f"{prefix}.{path}" if path else prefix

    return PathShape(
        frozenset(prefixed(path) for path in shape.required),
        frozenset(prefixed(path) for path in shape.possible),
    )


def _merge_path_branches(shapes: list[PathShape]) -> PathShape:
    if not shapes:
        return PathShape(frozenset(), frozenset())
    required = set(shapes[0].required)
    possible: set[str] = set()
    for shape in shapes:
        required.intersection_update(shape.required)
        possible.update(shape.possible)
    return PathShape(frozenset(required), frozenset(possible))


def _target_path(node: ast.AST, variable: str) -> str | None:
    if isinstance(node, ast.Name):
        return "" if node.id == variable else None
    if isinstance(node, ast.Subscript):
        base = _target_path(node.value, variable)
        key = _literal_string(node.slice)
        if base is not None and key is not None:
            return f"{base}.{key}" if base else key
    return None


def _named_path_shape(
    function: ast.AST,
    variable: str,
    *,
    context: str,
    seen: frozenset[str],
) -> PathShape:
    """Resolve branch-assigned dicts, later key writes, and list item appends."""
    assignments: list[ast.AST] = []
    possible: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if value is None:
                continue
            if any(isinstance(target, ast.Name) and target.id == variable for target in targets):
                assignments.append(value)
            for target in targets:
                path = _target_path(target, variable)
                if path is None or not path:
                    continue
                possible.add(path)
                child = _value_path_shape(function, value, context=context, seen=seen)
                possible.update(_prefix_path_shape(child, path).possible)
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if (
            node.func.attr == "append"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == variable
            and len(node.args) == 1
        ):
            item = _value_path_shape(function, node.args[0], context=context, seen=seen)
            possible.update(_prefix_path_shape(item, "[]").possible)
        if (
            node.func.attr == "update"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == variable
        ):
            if len(node.args) > 1:
                raise RegistryError(f"unresolved multi-argument dict.update in {context}")
            if node.args:
                argument = node.args[0]
                if not isinstance(argument, (ast.Dict, ast.Name)):
                    raise RegistryError(
                        f"unresolved dict.update argument in {context} at line {node.lineno}"
                    )
                update = _value_path_shape(function, argument, context=context, seen=seen)
                if isinstance(argument, ast.Name) and not update.possible:
                    raise RegistryError(
                        f"unresolved dict.update name {argument.id!r} in {context} at line {node.lineno}"
                    )
                possible.update(update.possible)
            for keyword in node.keywords:
                if keyword.arg is None:
                    raise RegistryError(
                        f"unresolved dict.update keyword spread in {context} at line {node.lineno}"
                    )
                possible.add(keyword.arg)
                child = _value_path_shape(function, keyword.value, context=context, seen=seen)
                possible.update(_prefix_path_shape(child, keyword.arg).possible)

    branches = [
        _value_path_shape(function, value, context=context, seen=seen)
        for value in assignments
    ]
    merged = _merge_path_branches(branches)
    return PathShape(merged.required, frozenset(set(merged.possible) | possible))


def _value_path_shape(
    function: ast.AST,
    node: ast.AST,
    *,
    context: str,
    seen: frozenset[str] = frozenset(),
) -> PathShape:
    if isinstance(node, ast.Dict):
        required: set[str] = set()
        possible: set[str] = set()
        for key, value in zip(node.keys, node.values):
            if key is None:
                raise RegistryError(f"unresolved nested dict spread in {context}")
            name = _literal_string(key)
            if name is None:
                raise RegistryError(
                    f"non-literal dict key in {context} at line {getattr(key, 'lineno', '?')}"
                )
            required.add(name)
            possible.add(name)
            child = _value_path_shape(function, value, context=context, seen=seen)
            nested = _prefix_path_shape(child, name)
            required.update(nested.required)
            possible.update(nested.possible)
        return PathShape(frozenset(required), frozenset(possible))
    if isinstance(node, ast.IfExp):
        return _merge_path_branches(
            [
                _value_path_shape(function, node.body, context=context, seen=seen),
                _value_path_shape(function, node.orelse, context=context, seen=seen),
            ]
        )
    if isinstance(node, ast.Name):
        if node.id in seen:
            return PathShape(frozenset(), frozenset())
        return _named_path_shape(
            function,
            node.id,
            context=context,
            seen=seen | {node.id},
        )
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        item_shapes = [
            _prefix_path_shape(
                _value_path_shape(function, item, context=context, seen=seen),
                "[]",
            )
            for item in node.elts
        ]
        merged = _merge_path_branches(item_shapes)
        return PathShape(frozenset(), merged.possible)
    return PathShape(frozenset(), frozenset())


def _return_path_shape(tree: ast.Module, name: str, source: str) -> PathShape:
    function = _function(tree, name, source)
    returned = [node.value for node in ast.walk(function) if isinstance(node, ast.Return)]
    literal_returns = [node for node in returned if isinstance(node, ast.Dict)]
    if not literal_returns:
        raise RegistryError(f"no literal return dict in {source}:{name}")
    return _merge_path_branches(
        [
            _value_path_shape(function, node, context=f"{source}:{name}")
            for node in literal_returns
        ]
    )


def _assigned_dict(function: ast.AST, variable: str, *, context: str) -> ast.Dict:
    found: list[ast.Dict] = []
    for node in ast.walk(function):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(target, ast.Name) and target.id == variable for target in targets):
            value = node.value
            if isinstance(value, ast.Dict):
                found.append(value)
    if len(found) != 1:
        raise RegistryError(f"expected one literal {variable} dict in {context}; found {len(found)}")
    return found[0]


def _dict_passed_to_write(function: ast.AST, marker: str, *, context: str) -> ast.Dict:
    candidates: list[ast.Dict] = []
    for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
        if not isinstance(call.func, ast.Attribute) or call.func.attr != "write_text":
            continue
        if marker not in ast.unparse(call.func.value):
            continue
        for child in ast.walk(call):
            if isinstance(child, ast.Call) and (
                (isinstance(child.func, ast.Attribute) and child.func.attr == "dumps")
                or (isinstance(child.func, ast.Name) and child.func.id == "dumps")
            ):
                if child.args and isinstance(child.args[0], ast.Dict):
                    candidates.append(child.args[0])
    if len(candidates) != 1:
        raise RegistryError(f"expected one persisted literal dict for {context}; found {len(candidates)}")
    return candidates[0]


def _function_local_values(function: ast.AST) -> dict[str, ast.AST]:
    values: dict[str, ast.AST] = {}
    for node in ast.walk(function):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            values[node.targets[0].id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value:
            values[node.target.id] = node.value
    return values


def _tuple_strings(node: ast.AST) -> set[str] | None:
    if not isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return None
    values = {_literal_string(item) for item in node.elts}
    return None if None in values else {value for value in values if value is not None}


def _spread_shape(
    node: ast.AST,
    *,
    locals_: dict[str, ast.AST],
    functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
    context: str,
    seen: frozenset[str] = frozenset(),
) -> EventShape:
    if isinstance(node, ast.Dict):
        keys = frozenset(_dict_keys(node, context=context))
        return EventShape(keys, keys)
    if isinstance(node, ast.DictComp):
        if len(node.generators) != 1:
            raise RegistryError(f"unresolved multi-generator spread in {context}")
        keys = _tuple_strings(node.generators[0].iter)
        if keys is None:
            raise RegistryError(f"unresolved dict-comprehension spread in {context}")
        frozen = frozenset(keys)
        return EventShape(frozen, frozen)
    if isinstance(node, ast.IfExp):
        left = _spread_shape(node.body, locals_=locals_, functions=functions, context=context, seen=seen)
        right = _spread_shape(node.orelse, locals_=locals_, functions=functions, context=context, seen=seen)
        return EventShape(left.required & right.required, left.possible | right.possible)
    if isinstance(node, ast.Name):
        if node.id in seen or node.id not in locals_:
            raise RegistryError(f"unresolved event spread {node.id!r} in {context}")
        return _spread_shape(
            locals_[node.id], locals_=locals_, functions=functions, context=context, seen=seen | {node.id}
        )
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in functions:
        required: set[str] | None = None
        possible: set[str] = set()
        for returned in _return_dicts(functions[node.func.id], context=f"{context}:{node.func.id}"):
            keys = _dict_keys(returned, context=f"{context}:{node.func.id}")
            required = keys if required is None else required & keys
            possible.update(keys)
        return EventShape(frozenset(required or set()), frozenset(possible))
    if isinstance(node, ast.Attribute) and node.attr == "signature" and "_gpu_signature" in functions:
        # _MarkerStallError.signature is populated from the same `sig = _gpu_signature()`
        # value before the retry layer re-emits it. Resolve the producer function, while
        # retaining its empty-dict branch as optionality.
        return _spread_shape(
            ast.Call(func=ast.Name(id="_gpu_signature", ctx=ast.Load()), args=[], keywords=[]),
            locals_=locals_,
            functions=functions,
            context=context,
            seen=seen,
        )
    raise RegistryError(
        f"unresolved event spread {ast.dump(node, include_attributes=False)} in {context}"
    )


def _event_writer_shapes(root: Path) -> tuple[set[str], dict[str, dict[str, list[str]]], list[str]]:
    events_tree = _tree(root, "windows-converter/events.py")
    emit_fn = _function(events_tree, "emit", "windows-converter/events.py")
    record = _assigned_dict(emit_fn, "record", context="windows-converter/events.py:emit")
    base: set[str] = set()
    for key, value in zip(record.keys, record.values):
        if key is None and isinstance(value, ast.Name) and value.id == "fields":
            continue  # the call-site extraction below is the proof for this deliberate spread
        name = _literal_string(key)
        if name is None:
            raise RegistryError("unexpected dynamic base key in windows-converter/events.py:emit")
        base.add(name)
    variants: dict[str, list[EventShape]] = {}
    emitter_sources: list[str] = []
    for path in sorted((root / "windows-converter").glob("*.py")):
        relative = path.relative_to(root).as_posix()
        tree = _tree(root, relative)
        functions = _functions(tree)
        source_has_emit = False
        for function in functions.values():
            locals_ = _function_local_values(function)
            for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
                if not isinstance(call.func, ast.Name) or call.func.id != "emit" or len(call.args) < 2:
                    continue
                source_has_emit = True
                stage, event = _literal_string(call.args[0]), _literal_string(call.args[1])
                if stage is None or event is None:
                    raise RegistryError(f"non-literal emit variant in {relative}:{call.lineno}")
                required = set(base)
                possible = set(base)
                for keyword in call.keywords:
                    if keyword.arg is not None:
                        required.add(keyword.arg)
                        possible.add(keyword.arg)
                    else:
                        spread = _spread_shape(
                            keyword.value,
                            locals_=locals_,
                            functions=functions,
                            context=f"{relative}:{call.lineno}",
                        )
                        required.update(spread.required)
                        possible.update(spread.possible)
                variants.setdefault(f"{stage}/{event}", []).append(
                    EventShape(frozenset(required), frozenset(possible))
                )
        if source_has_emit:
            emitter_sources.append(relative)
    if not variants:
        raise RegistryError("no events.jsonl emit variants found")
    collapsed: dict[str, dict[str, list[str]]] = {}
    for variant, shapes in sorted(variants.items()):
        required = set(shapes[0].required)
        possible: set[str] = set()
        for shape in shapes:
            required.intersection_update(shape.required)
            possible.update(shape.possible)
        collapsed[variant] = {
            "required_keys": sorted(required),
            "optional_keys": sorted(possible - required),
        }
    return base, collapsed, emitter_sources


_RUST_INDEX = re.compile(r'\b([A-Za-z_][A-Za-z0-9_]*)\["([A-Za-z_][A-Za-z0-9_]*)"\]')
_JS_FIELD = re.compile(r'\be\.([A-Za-z_][A-Za-z0-9_]*)\b')
_JS_VARIANT = re.compile(r'^\s*"([a-z0-9_-]+/[a-z0-9_-]+)"\s*:\s*(.*),\s*$')
_RUST_IDENT = r"[A-Za-z_][A-Za-z0-9_]*"


def _rust_index_map(text: str) -> dict[str, set[str]]:
    by_variable: dict[str, set[str]] = {}
    for variable, key in _RUST_INDEX.findall(text):
        by_variable.setdefault(variable, set()).add(key)
    return by_variable


def _rust_event_variables(text: str) -> set[str]:
    return {
        variable
        for variable, keys in _rust_index_map(text).items()
        if {"stage", "event"}.issubset(keys)
    }


def _rust_event_indexes(text: str, *, only_variable: str | None = None) -> set[str]:
    by_variable = _rust_index_map(text)
    event_variables = _rust_event_variables(text)
    if only_variable is not None:
        return by_variable.get(only_variable, set()) if only_variable in event_variables else set()
    return set().union(*(by_variable[variable] for variable in event_variables)) if event_variables else set()


def _brace_body(text: str, opening: int) -> str:
    depth = 0
    for index in range(opening, len(text)):
        depth += text[index] == "{"
        depth -= text[index] == "}"
        if depth == 0:
            return text[opening:index + 1]
    raise RegistryError("unterminated Rust block while extracting an event consumer")


def _rust_derived_event_aliases(text: str) -> list[tuple[str, set[str]]]:
    """Follow a selected event into its assigned name and any `Some(alias)` arm."""
    derived: list[tuple[str, set[str]]] = []
    pattern = re.compile(
        rf'let\s+(?P<slot>{_RUST_IDENT})\s*=\s*[^;]{{0,1200}}?\.(?:r?find)\('
        rf'\|(?P<source>{_RUST_IDENT})\|\s*(?P=source)\["stage"\]\s*==\s*'
        rf'"(?P<stage>[a-z_]+)".{{0,300}}?(?P=source)\["event"\]\s*==\s*'
        rf'"(?P<event>[a-z_]+)".{{0,300}}?\)[^;]{{0,300}}?;',
        flags=re.DOTALL,
    )
    for match in pattern.finditer(text):
        tail_start = match.end()
        slot = match.group("slot")
        slot_keys = {
            key
            for variable, key in _RUST_INDEX.findall(text[tail_start:])
            if variable == slot
        }
        if slot_keys:
            derived.append((f"{match.group('stage')}/{match.group('event')}", slot_keys))
        match_slot = re.search(rf'\bmatch\s+{re.escape(match.group("slot"))}\s*\{{', text[tail_start:])
        if match_slot is None:
            continue
        match_open = tail_start + match_slot.end() - 1
        match_body = _brace_body(text, match_open)
        some = re.search(rf'Some\((?P<alias>{_RUST_IDENT})\)\s*=>\s*\{{', match_body)
        if some is None:
            continue
        some_open = match_open + some.end() - 1
        body = _brace_body(text, some_open)
        alias = some.group("alias")
        keys = {key for variable, key in _RUST_INDEX.findall(body) if variable == alias}
        derived.append((f"{match.group('stage')}/{match.group('event')}", keys))
    return derived


def _event_consumers(root: Path) -> tuple[set[str], dict[str, set[str]]]:
    global_keys: set[str] = set()
    variants: dict[str, set[str]] = {}
    for relative in (
        "windows-widget/src-tauri/src/algedonic.rs",
        "windows-widget/src-tauri/src/assay.rs",
        "windows-widget/src-tauri/src/events.rs",
        "windows-widget/src-tauri/src/line.rs",
        "windows-widget/src-tauri/src/room.rs",
    ):
        text = _read(root, relative)
        event_variables = _rust_event_variables(text)
        # `ev` is the conventional row binding. Other aliases are admitted only from a
        # stage/event selector or a data-flow-linked Some(alias) arm, avoiding false keys from
        # an unrelated shadowed `later` receipt row in algedonic.rs.
        global_keys.update(_rust_event_indexes(text, only_variable="ev"))
        # Current Rust readers express variants as adjacent stage/event predicates or match arms.
        for match in re.finditer(
            rf'(?P<variable>{_RUST_IDENT})\["stage"\]\s*==\s*"(?P<stage>[a-z_]+)"'
            rf'.{{0,260}}?(?P=variable)\["event"\]\s*==\s*"(?P<event>[a-z_]+)"',
            text,
            flags=re.DOTALL,
        ):
            tail = text[match.end():]
            brace = tail.find("{")
            semicolon = tail.find(";")
            if brace >= 0 and (semicolon < 0 or brace < semicolon):
                depth = 0
                end = brace
                for end, char in enumerate(tail[brace:], start=brace):
                    depth += char == "{"
                    depth -= char == "}"
                    if depth == 0:
                        break
                body = text[match.start(): match.end() + end + 1]
            else:
                end = semicolon if semicolon >= 0 else min(len(tail), 400)
                body = text[match.start(): match.end() + end + 1]
            variants.setdefault(f"{match.group('stage')}/{match.group('event')}", set()).update(
                _rust_event_indexes(body, only_variable=match.group("variable"))
            )
        for match in re.finditer(
            r'\(Some\("([a-z_]+)"\),\s*Some\("([a-z_]+)"\)\)[^\n]*=>\s*\{(.*?)(?:\n\s*\}|\n\s*_\s*=>)',
            text,
            flags=re.DOTALL,
        ):
            arm_keys = {
                key
                for variable, key in _RUST_INDEX.findall(match.group(3))
                if variable in event_variables
            }
            variants.setdefault(f"{match.group(1)}/{match.group(2)}", set()).update(
                arm_keys
            )
        for variant, keys in _rust_derived_event_aliases(text):
            global_keys.update(keys)
            variants.setdefault(variant, set()).update(keys)
        if relative.endswith("algedonic.rs"):
            for call in re.findall(r'sfield\(ev,\s*&\[([^]]+)\]\)', text):
                global_keys.update(re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"', call))
        if relative.endswith("assay.rs"):
            variants.setdefault("audit/scored", set()).update(
                re.findall(r'scored\["([A-Za-z_][A-Za-z0-9_]*)"\]', text)
            )
    vocab = _read(root, "windows-widget/src/event-vocab.js")
    for line in vocab.splitlines():
        match = _JS_VARIANT.match(line)
        if match:
            variants.setdefault(match.group(1), set()).update(_JS_FIELD.findall(match.group(2)))
    main_text = _read(root, "windows-widget/src/main.js")
    product_clock = main_text[main_text.index("function productClock"): main_text.index("\n}\n", main_text.index("function productClock"))]
    global_keys.update(re.findall(r'\bev\.([A-Za-z_][A-Za-z0-9_]*)', product_clock))
    room_text = _read(root, "windows-widget/src/room.js")
    local_projection = next(line for line in room_text.splitlines() if "const local =" in line)
    global_keys.update(re.findall(r'\be\.([A-Za-z_][A-Za-z0-9_]*)', local_projection))
    # Generic latest-event projections consume only the common envelope.
    global_keys.update({"ts", "stage", "event"})
    return global_keys, variants


def _python_name_paths(function: ast.AST, roots: dict[str, str]) -> set[str]:
    """Resolve literal subscript/get paths rooted at named consumer objects."""
    aliases = dict(roots)
    changed = True
    while changed:
        changed = False
        for node in ast.walk(function):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                continue
            path = _subscript_path(node.value, aliases)
            if path is not None and aliases.get(node.targets[0].id) != path:
                aliases[node.targets[0].id] = path
                changed = True
    paths: set[str] = set()
    for node in ast.walk(function):
        path = _subscript_path(node, aliases)
        if path:
            paths.add(path)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
        ):
            base = _subscript_path(node.func.value, aliases)
            key = _literal_string(node.args[0])
            if base is not None and key is not None:
                paths.add(f"{base}.{key}" if base else key)
    return paths


def _subscript_path(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id)
    if isinstance(node, ast.Subscript):
        base = _subscript_path(node.value, aliases)
        key = _literal_string(node.slice)
        if base is not None and key is not None:
            return f"{base}.{key}" if base else key
    return None


def _regex_keys(text: str, pattern: str) -> set[str]:
    return set(re.findall(pattern, text))


def _contract_shapes(root: Path) -> dict[str, dict]:
    convert_source = "windows-converter/convert_and_ship.py"
    convert_tree = _tree(root, convert_source)
    convert_functions = _functions(convert_tree)
    analyst_source = "windows-converter/analyst.py"
    analyst_tree = _tree(root, analyst_source)
    coverage_source = "windows-converter/coverage_rescore.py"
    coverage_tree = _tree(root, coverage_source)
    figure_source = "windows-converter/figure_coverage.py"
    figure_tree = _tree(root, figure_source)

    progress_fn = _function(convert_tree, "_write_progress", convert_source)
    convert_progress_required = _dict_paths(
        _assigned_dict(progress_fn, "record", context=f"{convert_source}:_write_progress"),
        context=f"{convert_source}:_write_progress",
    )
    convert_progress_optional: set[str] = set()
    for call in (node for node in ast.walk(convert_tree) if isinstance(node, ast.Call)):
        if not (
            (isinstance(call.func, ast.Name) and call.func.id == "_run_marker")
            or (isinstance(call.func, ast.Attribute) and call.func.attr == "_run_marker")
        ):
            continue
        for keyword in call.keywords:
            if keyword.arg == "progress_context":
                if not isinstance(keyword.value, ast.Dict):
                    raise RegistryError(f"unresolved progress_context at {convert_source}:{call.lineno}")
                convert_progress_optional.update(
                    _dict_paths(keyword.value, context=f"{convert_source}:{call.lineno}")
                )

    analyst_fn = _function(analyst_tree, "process", analyst_source)
    analyst_progress = _dict_paths(
        _dict_passed_to_write(analyst_fn, "ANALYST_PROGRESS", context=f"{analyst_source}:process"),
        context=f"{analyst_source}:process",
    )

    done_fn = _function(convert_tree, "_convert_chunked", convert_source)
    done_paths = _dict_paths(
        _dict_passed_to_write(done_fn, ".done", context=f"{convert_source}:_convert_chunked"),
        context=f"{convert_source}:_convert_chunked",
    )
    ledger_paths = _dict_paths(
        _assigned_dict(
            _function(convert_tree, "_ledger_record", convert_source),
            "record",
            context=f"{convert_source}:_ledger_record",
        ),
        context=f"{convert_source}:_ledger_record",
    )

    coverage_shape = _return_path_shape(coverage_tree, "run_rescore", coverage_source)
    figure_shape = _prefix_path_shape(
        _return_path_shape(figure_tree, "coverage", figure_source),
        "p1_page_coverage",
    )
    inventory_shape = _prefix_path_shape(
        _return_path_shape(coverage_tree, "final_conversion_inventory", coverage_source),
        "final_conversion_inventory",
    )
    coverage_required = (
        set(coverage_shape.required) | set(figure_shape.required) | set(inventory_shape.required)
    )
    coverage_possible = (
        set(coverage_shape.possible) | set(figure_shape.possible) | set(inventory_shape.possible)
    )

    line_source = "windows-widget/src-tauri/src/line.rs"
    line_text = _read(root, line_source)
    convert_progress_consumed = _regex_keys(line_text, r'p\["([A-Za-z_][A-Za-z0-9_]*)"\]')
    convert_progress_consumed.update(_regex_keys(line_text, r'cp_field\("([A-Za-z_][A-Za-z0-9_]*)"\)'))
    analyst_progress_consumed = set()
    for line in line_text.splitlines():
        if "analyst_progress.as_ref()" in line:
            analyst_progress_consumed.update(_regex_keys(line, r'v\["([A-Za-z_][A-Za-z0-9_]*)"\]'))

    done_consumed = _python_name_paths(done_fn, {"prior": ""})
    done_identity_fn = _function(convert_tree, "_done_identity_mismatch", convert_source)
    done_consumed.update(_python_name_paths(done_identity_fn, {"prior": ""}))
    done_consumed.update(
        _dict_keys(
            _assigned_dict(done_identity_fn, "fields", context=f"{convert_source}:_done_identity_mismatch"),
            context=f"{convert_source}:_done_identity_mismatch",
        )
    )
    ledger_consumed = _python_name_paths(
        _function(convert_tree, "estimate_from_ledger", convert_source), {"r": ""}
    )
    coverage_consumed = _python_name_paths(
        _function(coverage_tree, "main", coverage_source), {"report": ""}
    )

    base, event_variants, event_emitter_sources = _event_writer_shapes(root)
    event_global_consumed, event_variant_consumed = _event_consumers(root)

    contracts = {
        "events.jsonl": {
            "format": "jsonl",
            "writers": [
                "windows-converter/events.py:emit",
                *[f"{source}:emit call sites" for source in event_emitter_sources],
            ],
            "consumers": [
                "windows-widget/src-tauri/src/events.rs",
                "windows-widget/src-tauri/src/line.rs",
                "windows-widget/src-tauri/src/room.rs",
                "windows-widget/src-tauri/src/algedonic.rs",
                "windows-widget/src-tauri/src/assay.rs",
                "windows-widget/src/event-vocab.js",
                "windows-widget/src/main.js",
                "windows-widget/src/room.js",
            ],
            "envelope_required_keys": sorted(base),
            "variants": event_variants,
            "consumer_global_keys": sorted(event_global_consumed),
            "consumer_variant_keys": {
                key: sorted(value) for key, value in sorted(event_variant_consumed.items())
            },
        },
        "coverage_rescore.stdout": {
            "format": "json",
            "writers": [
                "windows-converter/coverage_rescore.py:run_rescore",
                "windows-converter/coverage_rescore.py:final_conversion_inventory",
                "windows-converter/figure_coverage.py:coverage",
            ],
            "consumers": ["windows-converter/coverage_rescore.py:main text projection"],
            "required_paths": sorted(coverage_required),
            "optional_paths": sorted(coverage_possible - coverage_required),
            "consumer_paths": sorted(coverage_consumed),
        },
        "slice.done": {
            "format": "json",
            "writers": ["windows-converter/convert_and_ship.py:_convert_chunked"],
            "consumers": [
                "windows-converter/convert_and_ship.py:_done_identity_mismatch",
                "windows-converter/convert_and_ship.py:_convert_chunked resume",
            ],
            "required_paths": sorted(done_paths),
            "optional_paths": [],
            "consumer_paths": sorted(done_consumed),
        },
        "convert_progress": {
            "format": "json",
            "writers": ["windows-converter/convert_and_ship.py:_write_progress"],
            "consumers": ["windows-widget/src-tauri/src/line.rs:state"],
            "required_paths": sorted(convert_progress_required),
            "optional_paths": sorted(convert_progress_optional - convert_progress_required),
            "consumer_paths": sorted(convert_progress_consumed),
        },
        "analyst_progress": {
            "format": "json",
            "writers": ["windows-converter/analyst.py:process._progress"],
            "consumers": ["windows-widget/src-tauri/src/line.rs:state"],
            "required_paths": sorted(analyst_progress),
            "optional_paths": [],
            "consumer_paths": sorted(analyst_progress_consumed),
        },
        "conversion-ledger.jsonl": {
            "format": "jsonl",
            "writers": ["windows-converter/convert_and_ship.py:_ledger_record"],
            "consumers": ["windows-converter/convert_and_ship.py:estimate_from_ledger"],
            "required_paths": sorted(ledger_paths),
            "optional_paths": [],
            "consumer_paths": sorted(ledger_consumed),
        },
    }
    _assert_parity(contracts)
    return contracts


def _assert_parity(contracts: dict[str, dict]) -> None:
    events = contracts["events.jsonl"]
    union = set(events["envelope_required_keys"])
    for shape in events["variants"].values():
        union.update(shape["required_keys"])
        union.update(shape["optional_keys"])
    missing_global = set(events["consumer_global_keys"]) - union
    if missing_global:
        raise RegistryError(f"events.jsonl consumer uses unregistered key(s): {sorted(missing_global)}")
    for variant, keys in events["consumer_variant_keys"].items():
        if variant not in events["variants"]:
            raise RegistryError(f"consumer references unregistered event variant {variant}")
        shape = events["variants"][variant]
        missing = set(keys) - set(shape["required_keys"]) - set(shape["optional_keys"])
        if missing:
            raise RegistryError(
                f"event consumer {variant} uses key(s) registered only elsewhere: {sorted(missing)}"
            )
    for name, contract in contracts.items():
        if name == "events.jsonl":
            continue
        declared = set(contract["required_paths"]) | set(contract["optional_paths"])
        missing = set(contract["consumer_paths"]) - declared
        if missing:
            raise RegistryError(f"{name} consumer uses unregistered path(s): {sorted(missing)}")


def build_registry(root: Path) -> dict:
    root = root.resolve()
    return {
        "registry_version": 1,
        "authority": "generated from writer and consumer source; observability/schema_registry.py --check",
        "scope": {
            "signed_ticket": "A4 schema registry + key tripwire (MSG-FAB-0055; Rab signed 2026-08-31)",
            "included": [
                "events.jsonl",
                "coverage_rescore --json stdout",
                "chunk slice .done",
                ".convert-progress.json",
                ".analyst-progress.json",
                "conversion-ledger.jsonl",
            ],
            "explicit_exclusions": {
                ".convert-estimate.json": "estimate/promise receipt, not a progress file in signed A4",
                ".intake-state.json": "Conveyor State receipt created after A4 was banked; separate contract",
            },
        },
        "contracts": _contract_shapes(root),
    }


def registry_bytes(root: Path) -> bytes:
    text = json.dumps(build_registry(root), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return text.encode("utf-8")


def check_registry(root: Path, registry_path: Path | None = None) -> None:
    path = registry_path or root / REGISTRY_REL
    expected = registry_bytes(root)
    try:
        observed = path.read_bytes()
    except OSError as exc:
        raise RegistryError(f"registry absent or unreadable: {path}: {exc}") from exc
    if observed != expected:
        raise RegistryError(
            f"registry drift: {path} is not the byte-exact projection; run schema_registry.py --write"
        )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="A4 filesystem-contract schema registry")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="fail on parity or checked-in drift")
    action.add_argument("--write", action="store_true", help="regenerate observability/schemas.json")
    action.add_argument("--print", dest="print_registry", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=_repo_root())
    args = parser.parse_args(list(argv) if argv is not None else None)
    root = args.repo_root.resolve()
    try:
        data = registry_bytes(root)
        if args.check:
            check_registry(root)
            print("PASS — A4 schema registry matches writers; all consumer keys are registered")
        elif args.write:
            target = root / REGISTRY_REL
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f"{target.name}.tmp")
            temporary.write_bytes(data)
            temporary.replace(target)
            print(f"WROTE {target.relative_to(root).as_posix()} ({len(data)} bytes)")
        else:
            sys.stdout.buffer.write(data)
    except RegistryError as exc:
        print(f"FAIL — {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
