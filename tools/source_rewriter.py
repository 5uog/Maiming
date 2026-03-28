# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import argparse
import ast
import io
import sys
import tokenize

"""
I use this command-line module to rewrite Python source files under the package subtree rooted at src/<package_root> by composing an import-normalization transform with a bracket-layout transform over a finite ordered file family.

Let F = <f_1, ..., f_n> be the path sequence returned by iter_python_files(src_root). For each f_i in F, I decode a source string s_i in Sigma*, and I compute

    s_i^I = T_I(s_i; m_I)
    s_i^B = T_B(s_i^I; m_B, u)

where T_I denotes the import-rewrite operator selected by --imports, m_I in {keep, absolute, relative}, T_B denotes the bracket-layout operator selected by --brackets, m_B in {keep, compress, expand}, and u denotes the indentation unit supplied by --indent. I write s_i^B back to persistent storage iff s_i^B != s_i and --check is not asserted. I otherwise preserve the extant file image and only report the induced change set.

The import path rewrite is constrained to package-local references. I resolve each module coordinate as a tuple over dotted-name segments, and I compute relative import depth by shared-prefix reduction. If p = (p_0, ..., p_k) is the current package coordinate and q = (q_0, ..., q_m) is the target module coordinate, then

    c = common_prefix_len(p, q)
    level = len(p) - c + 1
    tail = q[c:]

and I emit the relative module specification "." * level when tail = (), or "." * level + ".".join(tail) otherwise. In relative mode, I do not rewrite directly from arbitrary mixed input. I first canonicalize through the absolute form and only thereafter reduce into the relative form, because the absolute coordinate is the stable intermediary on which the tuple arithmetic is well-defined.

The bracket-layout rewrite is likewise governed by local syntactic admissibility predicates. I compress only those bracket groups for which multiline structure exists and for which the token slice contains neither comments nor multiline string literals. I expand only those groups whose top-level interior admits a comma-separated sequence and whose control structure is not blocked by generator-form syntax or unresolved lambda binding depth. Formally, if G is a bracket node and A(G) is its top-level sequence analysis, I permit expansion iff

    expandable(G) <=> commas(A(G)) != empty and blocked(A(G)) = False.

I preserve syntax by rejecting any candidate that cannot be tokenized or whose abstract syntax tree cannot be reconstructed. For the comma-elision pass used after compression, I accept the deletion of a trailing comma on a candidate interval [a, b) only when

    AST(current) = AST(current[:a] + current[b:]).

This equality is computed over ast.dump(..., include_attributes=False), so the preserved invariant is semantic tree identity at the Python AST level rather than lexical equality.

I use the following invocation forms.

    python tools/source_rewriter.py
    python tools/source_rewriter.py --check
    python tools/source_rewriter.py --brackets compress
    python tools/source_rewriter.py --brackets expand
    python tools/source_rewriter.py --imports absolute
    python tools/source_rewriter.py --imports relative
    python tools/source_rewriter.py --imports relative --brackets compress
    python tools/source_rewriter.py --root <project_root> --src <source_root> --package-root ludoxel

The operational effect of each principal mode is as follows. The default state is a fixed point with respect to both transform families, because m_I = keep and m_B = keep. The check state computes the rewrite image and the induced change predicate without mutating the filesystem. The absolute-import state maps package-local import coordinates into a canonical dotted path rooted at <package_root>. The relative-import state computes the same canonical form first and then reduces it into a minimal valid relative specification with respect to the importing module coordinate. The compress state contracts admissible multiline bracket groups into a single lexical line and then removes only those trailing commas whose deletion is AST-preserving. The expand state distributes admissible top-level sequence elements over distinct lines using the indentation unit u.

I return process status 0 when the traversal completes without errors and, in check mode, no file would change. I return status 1 when at least one file operation fails or when check mode detects a nonempty rewrite set. I return status 2 when the source root does not exist or when the traversal domain contains no Python files. Thus, if D is the discovered file domain and C is the changed-file set, the exit relation is

    rc = 2, if D = empty
    rc = 1, if errors > 0
    rc = 1, if --check and |C| > 0
    rc = 0, otherwise.

I therefore use this module as a deterministic source-to-source normalization tool whose admissible mutations are bounded by token-level safety predicates, AST-level equivalence checks where required, and a path-resolution model anchored in the package coordinate system.
"""

SKIP_TOKEN_TYPES = {tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}
TRANSFORM_COMPRESS = "compress"
TRANSFORM_EXPAND = "expand"
BRACKETS_KEEP = "keep"
IMPORTS_KEEP = "keep"
IMPORTS_RELATIVE = "relative"
IMPORTS_ABSOLUTE = "absolute"
OPEN_TO_CLOSE = {"(": ")", "[": "]", "{": "}"}
CLOSE_TO_OPEN = {close: open_ for open_, close in OPEN_TO_CLOSE.items()}
ALL_OPEN = set(OPEN_TO_CLOSE)
ALL_CLOSE = set(CLOSE_TO_OPEN)
DEFAULT_INDENT = "    "
DEFAULT_PACKAGE_ROOT = "ludoxel"


@dataclass
class GroupNode:
    kind: str
    open_index: int
    close_index: int | None = None
    children: list["GroupNode"] = field(default_factory=list)
    start_offset: int = 0
    end_offset: int = 0


@dataclass
class TopLevelSequenceAnalysis:
    comma_indices: list[int] = field(default_factory=list)
    blocked: bool = False


@dataclass
class OutputBuffer:
    parts: list[str] = field(default_factory=list)
    current_line: str = ""

    def append(self, text: str) -> None:
        if not text:
            return
        self.parts.append(text)
        if "\n" in text:
            self.current_line = text.rsplit("\n", 1)[-1]
        else:
            self.current_line = f"{self.current_line}{text}"

    def render(self) -> str:
        return "".join(self.parts)

    def leading_whitespace(self) -> str:
        return leading_whitespace(self.current_line)


@dataclass(frozen=True)
class Replacement:
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class ImportRewriteContext:
    root: Path
    src_root: Path
    package_root: str = DEFAULT_PACKAGE_ROOT


@dataclass(frozen=True)
class ModuleLocation:
    package_parts: tuple[str, ...]
    module_parts: tuple[str, ...]
    is_package_init: bool


@dataclass(frozen=True)
class RelativeModuleSpec:
    level: int
    module: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=("I rewrite Python source under src/<package_root> by composing a package-local import transform with a bracket-layout transform."))
    parser.add_argument("--brackets", choices=[BRACKETS_KEEP, TRANSFORM_COMPRESS, TRANSFORM_EXPAND], default=BRACKETS_KEEP, help="Bracket-group rewrite mode. Default is keep.")
    parser.add_argument("--imports", choices=[IMPORTS_KEEP, IMPORTS_RELATIVE, IMPORTS_ABSOLUTE], default=IMPORTS_KEEP, help="Import rewrite mode for package-local imports. Relative mode first canonicalizes through absolute imports. Default is keep.")
    parser.add_argument("--compress", action="store_true", help="Compatibility alias for --brackets compress.")
    parser.add_argument("--expand", action="store_true", help="Compatibility alias for --brackets expand.")
    parser.add_argument("--root", type=Path, default=None, help="Project root. If omitted, I use the parent directory of this script.")
    parser.add_argument("--src", type=Path, default=None, help="Source root. If omitted, I use <root>/src/ludoxel.")
    parser.add_argument("--package-root", type=str, default=DEFAULT_PACKAGE_ROOT, help="Top-level package name for import rewriting. Default is ludoxel.")
    parser.add_argument("--check", action="store_true", help="Do not write files. I exit with status 1 if any file would change.")
    parser.add_argument("--quiet", action="store_true", help="Do not print changed file paths. By default, I print every changed file path.")
    parser.add_argument("--verbose", action="store_true", help="Retained for compatibility. Changed file paths are printed by default.")
    parser.add_argument("--indent", type=str, default=DEFAULT_INDENT, help="Indentation unit used by --brackets expand. Default is four spaces.")
    args = parser.parse_args()
    if args.compress and args.expand:
        parser.error("--compress and --expand cannot be used together")
    if args.compress:
        args.brackets = TRANSFORM_COMPRESS
    if args.expand:
        args.brackets = TRANSFORM_EXPAND
    return args


def detect_encoding(path: Path) -> str:
    with path.open("rb") as fh:
        encoding, _ = tokenize.detect_encoding(fh.readline)
    return encoding


def read_python_text(path: Path) -> tuple[str, str]:
    encoding = detect_encoding(path)
    with path.open("r", encoding=encoding, newline="") as fh:
        text = fh.read()
    return text, encoding


def write_python_text(path: Path, text: str, encoding: str) -> None:
    with path.open("w", encoding=encoding, newline="") as fh:
        fh.write(text)


def offset_table(text: str) -> list[int]:
    offsets = [0]
    total = 0
    for line in text.splitlines(keepends=True):
        total += len(line)
        offsets.append(total)
    return offsets


def to_offset(offsets: list[int], row: int, col: int) -> int:
    return offsets[row - 1] + col


def tokenize_text(text: str) -> list[tokenize.TokenInfo]:
    return list(tokenize.generate_tokens(io.StringIO(text).readline))


def build_group_tree(tokens: list[tokenize.TokenInfo]) -> list[GroupNode]:
    roots: list[GroupNode] = []
    stack: list[GroupNode] = []
    for index, tok in enumerate(tokens):
        if tok.type != tokenize.OP:
            continue

        if tok.string in OPEN_TO_CLOSE:
            node = GroupNode(kind=tok.string, open_index=index)
            if stack:
                stack[-1].children.append(node)
            else:
                roots.append(node)
            stack.append(node)
            continue

        if tok.string in CLOSE_TO_OPEN:
            if not stack:
                continue
            expected_open = CLOSE_TO_OPEN[tok.string]
            if stack[-1].kind != expected_open:
                continue
            stack[-1].close_index = index
            stack.pop()

    return roots


def annotate_group_offsets(nodes: list[GroupNode], tokens: list[tokenize.TokenInfo], offsets: list[int]) -> None:
    for node in nodes:
        annotate_group_offsets(node.children, tokens, offsets)
        if node.close_index is None:
            continue
        open_tok = tokens[node.open_index]
        close_tok = tokens[node.close_index]
        node.start_offset = to_offset(offsets, open_tok.start[0], open_tok.start[1])
        node.end_offset = to_offset(offsets, close_tok.end[0], close_tok.end[1])


def contains_comment_or_multiline_string(token_slice: list[tokenize.TokenInfo]) -> bool:
    for tok in token_slice:
        if tok.type == tokenize.COMMENT:
            return True
        if tok.type == tokenize.STRING and tok.start[0] != tok.end[0]:
            return True
    return False


def token_slice_for_node(node: GroupNode, tokens: list[tokenize.TokenInfo]) -> list[tokenize.TokenInfo]:
    if node.close_index is None:
        return []
    return tokens[node.open_index: node.close_index + 1]


def node_spans_multiple_lines(node: GroupNode, tokens: list[tokenize.TokenInfo]) -> bool:
    if node.close_index is None:
        return False
    open_tok = tokens[node.open_index]
    close_tok = tokens[node.close_index]
    return open_tok.start[0] != close_tok.end[0]


def joiner(prev: tokenize.TokenInfo, curr: tokenize.TokenInfo) -> str:
    if prev.string in {"(", "[", "{", "."}:
        return ""
    if curr.string in {".", ",", ")", "]", "}", "(", "[", "{"}:
        return ""
    return " "


def compact_significant_tokens(significant: list[tokenize.TokenInfo], original: str, offsets: list[int]) -> str:
    if not significant:
        return ""
    parts = [significant[0].string]
    for prev, curr in zip(significant, significant[1:]):
        prev_end = to_offset(offsets, prev.end[0], prev.end[1])
        curr_start = to_offset(offsets, curr.start[0], curr.start[1])
        raw_gap = original[prev_end:curr_start]
        if "\n" in raw_gap or "\r" in raw_gap:
            parts.append(joiner(prev, curr))
        else:
            parts.append(raw_gap)
        parts.append(curr.string)
    return "".join(parts)


def compact_token_slice(token_slice: list[tokenize.TokenInfo], original: str, offsets: list[int]) -> str:
    significant = [tok for tok in token_slice if tok.type not in SKIP_TOKEN_TYPES]
    return compact_significant_tokens(significant, original, offsets)


def analyze_top_level_sequence(node: GroupNode, tokens: list[tokenize.TokenInfo]) -> TopLevelSequenceAnalysis:
    if node.close_index is None:
        return TopLevelSequenceAnalysis()
    commas: list[int] = []
    depth = 0
    lambda_level = 0
    for i in range(node.open_index + 1, node.close_index):
        tok = tokens[i]
        if tok.type == tokenize.OP:
            if tok.string in ALL_OPEN:
                depth += 1
                continue
            if tok.string in ALL_CLOSE:
                if depth > 0:
                    depth -= 1
                continue
            if depth == 0 and tok.string == ":" and lambda_level > 0:
                lambda_level -= 1
                continue
            if depth == 0 and tok.string == "," and lambda_level == 0:
                commas.append(i)
                continue
        if tok.type == tokenize.NAME and depth == 0:
            if tok.string == "lambda":
                lambda_level += 1
                continue
            if tok.string in {"for", "async"}:
                return TopLevelSequenceAnalysis(blocked=True)
    if lambda_level > 0:
        return TopLevelSequenceAnalysis(blocked=True)
    return TopLevelSequenceAnalysis(comma_indices=commas, blocked=False)


def is_compressible_group(node: GroupNode, tokens: list[tokenize.TokenInfo]) -> bool:
    token_slice = token_slice_for_node(node, tokens)
    if not token_slice:
        return False
    if contains_comment_or_multiline_string(token_slice):
        return False
    return node_spans_multiple_lines(node, tokens)


def is_expandable_group(node: GroupNode, tokens: list[tokenize.TokenInfo]) -> bool:
    token_slice = token_slice_for_node(node, tokens)
    if not token_slice:
        return False
    if contains_comment_or_multiline_string(token_slice):
        return False
    analysis = analyze_top_level_sequence(node, tokens)
    if analysis.blocked:
        return False
    return bool(analysis.comma_indices)


def child_nodes_in_range(children: list[GroupNode], start_offset: int, end_offset: int) -> list[GroupNode]:
    return [child for child in children if child.start_offset >= start_offset and child.end_offset <= end_offset]


def leading_whitespace(text: str) -> str:
    index = 0
    while index < len(text) and text[index] in {" ", "\t"}:
        index += 1
    return text[:index]


def previous_significant_token(index: int, tokens: list[tokenize.TokenInfo]) -> tokenize.TokenInfo | None:
    for i in range(index - 1, -1, -1):
        tok = tokens[i]
        if tok.type in SKIP_TOKEN_TYPES:
            continue
        return tok
    return None


def is_optional_from_import_group(node: GroupNode, tokens: list[tokenize.TokenInfo]) -> bool:
    if node.kind != "(" or node.close_index is None:
        return False
    prev = previous_significant_token(node.open_index, tokens)
    if prev is None:
        return False
    return prev.type == tokenize.NAME and prev.string == "import"


def compact_optional_from_import_group(node: GroupNode, original: str, tokens: list[tokenize.TokenInfo], offsets: list[int]) -> str:
    if node.close_index is None:
        return original[node.start_offset: node.end_offset]
    significant = [tok for tok in tokens[node.open_index + 1: node.close_index] if tok.type not in SKIP_TOKEN_TYPES]
    if significant and significant[-1].type == tokenize.OP and significant[-1].string == ",":
        significant = significant[:-1]
    return compact_significant_tokens(significant, original, offsets)


def render_region_compress(original: str, start_offset: int, end_offset: int, nodes: list[GroupNode], tokens: list[tokenize.TokenInfo], offsets: list[int]) -> str:
    parts: list[str] = []
    cursor = start_offset
    for node in sorted(nodes, key=lambda n: n.start_offset):
        parts.append(original[cursor: node.start_offset])
        if is_compressible_group(node, tokens):
            if is_optional_from_import_group(node, tokens):
                parts.append(compact_optional_from_import_group(node=node, original=original, tokens=tokens, offsets=offsets))
            else:
                token_slice = token_slice_for_node(node, tokens)
                parts.append(compact_token_slice(token_slice, original, offsets))
        else:
            parts.append(render_region_compress(original=original, start_offset=node.start_offset, end_offset=node.end_offset, nodes=node.children, tokens=tokens, offsets=offsets))
        cursor = node.end_offset
    parts.append(original[cursor:end_offset])
    return "".join(parts)


def render_region_expand_to_buffer(original: str, start_offset: int, end_offset: int, nodes: list[GroupNode], tokens: list[tokenize.TokenInfo], offsets: list[int], indent_unit: str, buffer: OutputBuffer) -> None:
    cursor = start_offset
    for node in sorted(nodes, key=lambda n: n.start_offset):
        buffer.append(original[cursor: node.start_offset])
        if is_expandable_group(node, tokens):
            base_indent = buffer.leading_whitespace()
            buffer.append(render_expanded_node(node=node, original=original, tokens=tokens, offsets=offsets, indent_unit=indent_unit, base_indent=base_indent))
        else:
            render_region_expand_to_buffer(original=original, start_offset=node.start_offset, end_offset=node.end_offset, nodes=node.children, tokens=tokens, offsets=offsets, indent_unit=indent_unit, buffer=buffer)
        cursor = node.end_offset
    buffer.append(original[cursor:end_offset])


def render_region_expand_to_string(original: str, start_offset: int, end_offset: int, nodes: list[GroupNode], tokens: list[tokenize.TokenInfo], offsets: list[int], indent_unit: str, initial_line_prefix: str="") -> str:
    buffer = OutputBuffer(current_line=initial_line_prefix)
    render_region_expand_to_buffer(original=original, start_offset=start_offset, end_offset=end_offset, nodes=nodes, tokens=tokens, offsets=offsets, indent_unit=indent_unit, buffer=buffer)
    return buffer.render()


def render_expanded_node(node: GroupNode, original: str, tokens: list[tokenize.TokenInfo], offsets: list[int], indent_unit: str, base_indent: str) -> str:
    if node.close_index is None:
        return original[node.start_offset: node.end_offset]
    analysis = analyze_top_level_sequence(node, tokens)
    if analysis.blocked or not analysis.comma_indices:
        return render_region_expand_to_string(original=original, start_offset=node.start_offset, end_offset=node.end_offset, nodes=node.children, tokens=tokens, offsets=offsets, indent_unit=indent_unit, initial_line_prefix=base_indent)
    open_tok = tokens[node.open_index]
    close_tok = tokens[node.close_index]
    inner_start = to_offset(offsets, open_tok.end[0], open_tok.end[1])
    inner_end = to_offset(offsets, close_tok.start[0], close_tok.start[1])
    item_ranges: list[tuple[int, int]] = []
    cursor = inner_start
    for comma_index in analysis.comma_indices:
        comma_tok = tokens[comma_index]
        comma_start = to_offset(offsets, comma_tok.start[0], comma_tok.start[1])
        item_ranges.append((cursor, comma_start))
        cursor = to_offset(offsets, comma_tok.end[0], comma_tok.end[1])
    item_ranges.append((cursor, inner_end))
    item_indent = f"{base_indent}{indent_unit}"
    parts = [node.kind, "\n"]
    emitted = 0
    for item_start, item_end in item_ranges:
        child_subset = child_nodes_in_range(node.children, item_start, item_end)
        item_text = render_region_expand_to_string(original=original, start_offset=item_start, end_offset=item_end, nodes=child_subset, tokens=tokens, offsets=offsets, indent_unit=indent_unit, initial_line_prefix=item_indent).strip()
        if not item_text:
            continue
        parts.append(item_indent)
        parts.append(item_text)
        parts.append(",\n")
        emitted += 1
    if emitted == 0:
        return f"{node.kind}{OPEN_TO_CLOSE[node.kind]}"
    parts.append(base_indent)
    parts.append(OPEN_TO_CLOSE[node.kind])
    return "".join(parts)


def ast_signature(text: str) -> str | None:
    try:
        tree = ast.parse(text, type_comments=True)
    except SyntaxError:
        return None
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def ast_equivalent(text_a: str, text_b: str) -> bool:
    sig_a = ast_signature(text_a)
    if sig_a is None:
        return False
    sig_b = ast_signature(text_b)
    if sig_b is None:
        return False
    return sig_a == sig_b


def last_significant_token_before_close(node: GroupNode, tokens: list[tokenize.TokenInfo]) -> tokenize.TokenInfo | None:
    if node.close_index is None:
        return None
    for i in range(node.close_index - 1, node.open_index, -1):
        tok = tokens[i]
        if tok.type in SKIP_TOKEN_TYPES:
            continue
        return tok
    return None


def trailing_comma_candidate_ranges(text: str) -> list[tuple[int, int]]:
    try:
        tokens = tokenize_text(text)
    except tokenize.TokenError:
        return []
    offsets = offset_table(text)
    roots = build_group_tree(tokens)
    annotate_group_offsets(roots, tokens, offsets)
    candidates: list[tuple[int, int]] = []

    def visit(nodes: list[GroupNode]) -> None:
        for node in nodes:
            visit(node.children)
            token_slice = token_slice_for_node(node, tokens)
            if not token_slice:
                continue
            if contains_comment_or_multiline_string(token_slice):
                continue
            last_tok = last_significant_token_before_close(node, tokens)
            if last_tok is None:
                continue
            if last_tok.type != tokenize.OP or last_tok.string != ",":
                continue
            start = to_offset(offsets, last_tok.start[0], last_tok.start[1])
            end = to_offset(offsets, last_tok.end[0], last_tok.end[1])
            candidates.append((start, end))

    visit(roots)
    return candidates


def drop_safe_trailing_commas(text: str) -> str:
    if ast_signature(text) is None:
        return text
    candidates = trailing_comma_candidate_ranges(text)
    if not candidates:
        return text
    current = text
    for start, end in sorted(candidates, reverse=True):
        candidate = f"{current[:start]}{current[end:]}"
        if ast_equivalent(current, candidate):
            current = candidate
    return current


def resolve_module_location(path: Path, context: ImportRewriteContext) -> ModuleLocation | None:
    try:
        rel = path.resolve().relative_to(context.src_root.resolve())
    except ValueError:
        return None
    parts = rel.with_suffix("").parts
    if not parts:
        return None
    if parts[0] != context.package_root:
        package_parts = (context.package_root,) + tuple(parts[:-1])
        module_parts = tuple(parts)
        is_init = parts[-1] == "__init__"
        if is_init:
            package_parts = (context.package_root,) + tuple(parts[:-1])
            module_parts = (context.package_root,) + tuple(parts[:-1])
        return ModuleLocation(package_parts=package_parts, module_parts=module_parts, is_package_init=is_init)
    is_init = parts[-1] == "__init__"
    if is_init:
        package_parts = tuple(parts[:-1])
        module_parts = tuple(parts[:-1])
    else:
        package_parts = tuple(parts[:-1])
        module_parts = tuple(parts)
    return ModuleLocation(package_parts=package_parts, module_parts=module_parts, is_package_init=is_init)


def split_dotted_name(name: str | None) -> tuple[str, ...]:
    if not name:
        return ()
    return tuple(part for part in name.split(".") if part)


def common_prefix_len(a: tuple[str, ...], b: tuple[str, ...]) -> int:
    size = min(len(a), len(b))
    index = 0
    while index < size and a[index] == b[index]:
        index += 1
    return index


def resolve_absolute_module_from_importfrom(node: ast.ImportFrom, module_location: ModuleLocation) -> tuple[str, ...] | None:
    if node.level == 0:
        parts = split_dotted_name(node.module)
        return parts or None
    anchor = module_location.package_parts
    ascend = max(node.level - 1, 0)
    if ascend > len(anchor):
        return None
    base = anchor[: len(anchor) - ascend]
    target = base + split_dotted_name(node.module)
    return target or None


def compute_relative_module_spec(current_package: tuple[str, ...], target_module: tuple[str, ...]) -> RelativeModuleSpec | None:
    if not current_package or not target_module:
        return None
    prefix_len = common_prefix_len(current_package, target_module)
    level = len(current_package) - prefix_len + 1
    if level < 1:
        return None
    tail = target_module[prefix_len:]
    return RelativeModuleSpec(level=level, module=".".join(tail) or None)


def format_relative_module(spec: RelativeModuleSpec) -> str:
    dots = "." * spec.level
    return dots if spec.module is None else f"{dots}{spec.module}"


def render_aliases(names: list[ast.alias]) -> str:
    parts: list[str] = []
    for alias in names:
        if alias.asname:
            parts.append(f"{alias.name} as {alias.asname}")
        else:
            parts.append(alias.name)
    return ", ".join(parts)


def importfrom_to_relative_text(node: ast.ImportFrom, module_location: ModuleLocation) -> str | None:
    absolute_module = resolve_absolute_module_from_importfrom(node, module_location)
    if not absolute_module:
        return None
    if absolute_module[0] != module_location.package_parts[0]:
        return None
    spec = compute_relative_module_spec(module_location.package_parts, absolute_module)
    if spec is None:
        return None
    return f"from {format_relative_module(spec)} import {render_aliases(node.names)}"


def importfrom_to_absolute_text(node: ast.ImportFrom, module_location: ModuleLocation) -> str | None:
    absolute_module = resolve_absolute_module_from_importfrom(node, module_location)
    if not absolute_module:
        return None
    if absolute_module[0] != module_location.package_parts[0]:
        return None
    module_name = ".".join(absolute_module)
    return f"from {module_name} import {render_aliases(node.names)}"


def import_to_relative_lines(node: ast.Import, module_location: ModuleLocation) -> list[str] | None:
    lines: list[str] = []
    package_root = module_location.package_parts[0] if module_location.package_parts else None
    if package_root is None:
        return None
    for alias in node.names:
        if alias.asname is None:
            return None
        module_parts = split_dotted_name(alias.name)
        if not module_parts or module_parts[0] != package_root:
            return None
        if len(module_parts) < 2:
            return None
        spec = compute_relative_module_spec(module_location.package_parts, module_parts[:-1])
        if spec is None:
            return None
        imported_name = module_parts[-1]
        lines.append(f"from {format_relative_module(spec)} import {imported_name} as {alias.asname}")
    return lines


def import_to_absolute_lines(node: ast.Import) -> list[str] | None:
    if not node.names:
        return None
    return [f"import {render_aliases(node.names)}"]


def node_offsets(node: ast.AST, offsets: list[int]) -> tuple[int, int] | None:
    lineno = getattr(node, "lineno", None)
    col_offset = getattr(node, "col_offset", None)
    end_lineno = getattr(node, "end_lineno", None)
    end_col_offset = getattr(node, "end_col_offset", None)
    if None in {lineno, col_offset, end_lineno, end_col_offset}:
        return None
    return to_offset(offsets, lineno, col_offset), to_offset(offsets, end_lineno, end_col_offset)


def line_start_offset(text: str, offset: int) -> int:
    index = text.rfind("\n", 0, offset)
    return 0 if index < 0 else index + 1


def line_end_offset(text: str, offset: int) -> int:
    index = text.find("\n", offset)
    return len(text) if index < 0 else index + 1


def statement_indentation(text: str, start: int) -> str:
    line_start = line_start_offset(text, start)
    return leading_whitespace(text[line_start:start])


def segment_has_comment(text: str, start: int, end: int) -> bool:
    segment = text[start:end]
    for line in segment.splitlines():
        comment_index = line.find("#")
        if comment_index < 0:
            continue
        prefix = line[:comment_index]
        if prefix.count('"') % 2 == 0 and prefix.count("'") % 2 == 0:
            return True
    return False


def build_import_replacements(text: str, path: Path, context: ImportRewriteContext, mode: str) -> list[Replacement]:
    if mode == IMPORTS_KEEP:
        return []
    try:
        tree = ast.parse(text, type_comments=True)
    except SyntaxError:
        return []
    offsets = offset_table(text)
    module_location = resolve_module_location(path, context)
    if module_location is None or not module_location.package_parts:
        return []
    replacements: list[Replacement] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        span = node_offsets(node, offsets)
        if span is None:
            continue
        start, end = span
        if segment_has_comment(text, start, end):
            continue
        indent = statement_indentation(text, start)
        replacement_lines: list[str] | None = None
        if mode == IMPORTS_RELATIVE:
            if isinstance(node, ast.ImportFrom):
                rendered = importfrom_to_relative_text(node, module_location)
                if rendered is None:
                    continue
                replacement_lines = [rendered]
            else:
                replacement_lines = import_to_relative_lines(node, module_location)
                if replacement_lines is None:
                    continue
        elif mode == IMPORTS_ABSOLUTE:
            if isinstance(node, ast.ImportFrom):
                rendered = importfrom_to_absolute_text(node, module_location)
                if rendered is None:
                    continue
                replacement_lines = [rendered]
            else:
                replacement_lines = import_to_absolute_lines(node)
                if replacement_lines is None:
                    continue
        else:
            continue
        replacement_text = "\n".join(f"{indent}{line}" for line in replacement_lines)
        replacements.append(Replacement(start=start, end=end, text=replacement_text))
    replacements.sort(key=lambda item: item.start)
    filtered: list[Replacement] = []
    last_end = -1
    for repl in replacements:
        if repl.start < last_end:
            continue
        filtered.append(repl)
        last_end = repl.end
    return filtered


def apply_replacements(text: str, replacements: list[Replacement]) -> str:
    if not replacements:
        return text
    parts: list[str] = []
    cursor = 0
    for repl in replacements:
        parts.append(text[cursor:repl.start])
        parts.append(repl.text)
        cursor = repl.end
    parts.append(text[cursor:])
    return "".join(parts)


def rewrite_imports(text: str, path: Path, context: ImportRewriteContext, mode: str) -> str:
    replacements = build_import_replacements(text, path, context, mode)
    if not replacements:
        return text
    candidate = apply_replacements(text, replacements)
    if ast_signature(candidate) is None:
        return text
    return candidate


def rewrite_imports_pipeline(text: str, path: Path, context: ImportRewriteContext, mode: str) -> str:
    if mode == IMPORTS_KEEP:
        return text
    if mode == IMPORTS_ABSOLUTE:
        return rewrite_imports(text, path, context, IMPORTS_ABSOLUTE)
    if mode == IMPORTS_RELATIVE:
        canonical = rewrite_imports(text, path, context, IMPORTS_ABSOLUTE)
        return rewrite_imports(canonical, path, context, IMPORTS_RELATIVE)
    raise ValueError(f"unsupported import mode: {mode}")


def transform_source(text: str, path: Path, *, bracket_mode: str, indent_unit: str, import_mode: str, import_context: ImportRewriteContext) -> str:
    current = text
    if import_mode != IMPORTS_KEEP:
        current = rewrite_imports_pipeline(current, path, import_context, import_mode)
    try:
        tokens = tokenize_text(current)
    except tokenize.TokenError:
        return current
    offsets = offset_table(current)
    roots = build_group_tree(tokens)
    annotate_group_offsets(roots, tokens, offsets)
    if bracket_mode == TRANSFORM_COMPRESS:
        compressed = render_region_compress(original=current, start_offset=0, end_offset=len(current), nodes=roots, tokens=tokens, offsets=offsets)
        return drop_safe_trailing_commas(compressed)
    if bracket_mode == TRANSFORM_EXPAND:
        return render_region_expand_to_string(original=current, start_offset=0, end_offset=len(current), nodes=roots, tokens=tokens, offsets=offsets, indent_unit=indent_unit, initial_line_prefix="")
    if bracket_mode == BRACKETS_KEEP:
        return current
    raise ValueError(f"unsupported bracket mode: {bracket_mode}")


def iter_python_files(src_root: Path) -> list[Path]:
    return sorted(path for path in src_root.rglob("*.py") if path.is_file())


def process_file(path: Path, *, bracket_mode: str, indent_unit: str, import_mode: str, import_context: ImportRewriteContext, check_only: bool=False) -> tuple[bool, str | None]:
    try:
        original, encoding = read_python_text(path)
    except Exception as exc:
        return False, f"read failed: {exc}"
    rewritten = transform_source(original, path, bracket_mode=bracket_mode, indent_unit=indent_unit, import_mode=import_mode, import_context=import_context)
    if rewritten == original:
        return False, None
    if not check_only:
        try:
            write_python_text(path, rewritten, encoding)
        except Exception as exc:
            return False, f"write failed: {exc}"
    return True, None


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve() if args.root is not None else Path(__file__).resolve().parent.parent
    src_root = Path(args.src).resolve() if args.src is not None else root / "src" / args.package_root
    if not src_root.is_dir():
        print(f"error: source root was not found: {src_root}", file=sys.stderr)
        return 2
    files = iter_python_files(src_root)
    if not files:
        print(f"error: no .py files were found under {src_root}", file=sys.stderr)
        return 2
    import_context = ImportRewriteContext(root=root, src_root=src_root, package_root=args.package_root)
    changed_count = 0
    error_count = 0
    show_changed_paths = not args.quiet
    for path in files:
        changed, error = process_file(path=path, bracket_mode=args.brackets, indent_unit=args.indent, import_mode=args.imports, import_context=import_context, check_only=bool(args.check))
        if error is not None:
            error_count += 1
            print(f"[error] {path}: {error}", file=sys.stderr)
            continue
        if changed:
            changed_count += 1
            if show_changed_paths:
                print(display_path(path, root))
    action = "would update" if args.check else "updated"
    print(f"{action}: {changed_count} file(s)")
    if error_count:
        print(f"errors: {error_count} file(s)", file=sys.stderr)
        return 1
    if args.check and changed_count:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
