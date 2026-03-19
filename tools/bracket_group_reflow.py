# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: tools/bracket_group_reflow.py
from __future__ import annotations

"""
Usage:
    python tools/bracket_group_reflow.py --compress [--check] [--verbose] [--root <project_root>] [--src <source_root>]
    python tools/bracket_group_reflow.py --expand [--check] [--verbose] [--root <project_root>] [--src <source_root>] [--indent <text>]
"""

import argparse
import ast
import io
import sys
import tokenize
from dataclasses import dataclass, field
from pathlib import Path

SKIP_TOKEN_TYPES = {tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}
TRANSFORM_COMPRESS = "compress"
TRANSFORM_EXPAND = "expand"
OPEN_TO_CLOSE = {"(": ")", "[": "]", "{": "}"}
CLOSE_TO_OPEN = {close: open_ for open_, close in OPEN_TO_CLOSE.items()}
ALL_OPEN = set(OPEN_TO_CLOSE)
ALL_CLOSE = set(CLOSE_TO_OPEN)
DEFAULT_INDENT = "    "


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reflow bracket groups in src/ludoxel/**/*.py. "
            "Use --compress to contract multiline () / [] groups into one line, "
            "or --expand to reintroduce a canonical multiline layout."
        )
    )
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--compress",
        action="store_true",
        help="Collapse eligible multiline () / [] groups into one line and remove safe trailing commas."
    )
    mode_group.add_argument(
        "--expand",
        action="store_true",
        help="Expand eligible comma-separated () / [] groups into a canonical multiline form."
    )
    parser.add_argument("--root", type=Path, default=None, help="Project root. If omitted, I use the parent directory of this script.")
    parser.add_argument("--src", type=Path, default=None, help="Source root. If omitted, I use <root>/src/ludoxel.")
    parser.add_argument("--check", action="store_true", help="Do not write files. I exit with status 1 if any file would change.")
    parser.add_argument("--verbose", action="store_true", help="Print every changed file path.")
    parser.add_argument("--indent", type=str, default=DEFAULT_INDENT, help="Indentation unit used by --expand. Default is four spaces.")
    return parser.parse_args()


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
    return tokens[node.open_index : node.close_index + 1]


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


def compact_token_slice(token_slice: list[tokenize.TokenInfo], original: str, offsets: list[int]) -> str:
    significant = [tok for tok in token_slice if tok.type not in SKIP_TOKEN_TYPES]
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


def render_region_compress(
    original: str,
    start_offset: int,
    end_offset: int,
    nodes: list[GroupNode],
    tokens: list[tokenize.TokenInfo],
    offsets: list[int],
) -> str:
    parts: list[str] = []
    cursor = start_offset
    for node in sorted(nodes, key=lambda n: n.start_offset):
        parts.append(original[cursor : node.start_offset])
        if is_compressible_group(node, tokens):
            token_slice = token_slice_for_node(node, tokens)
            parts.append(compact_token_slice(token_slice, original, offsets))
        else:
            parts.append(
                render_region_compress(
                    original=original,
                    start_offset=node.start_offset,
                    end_offset=node.end_offset,
                    nodes=node.children,
                    tokens=tokens,
                    offsets=offsets,
                )
            )
        cursor = node.end_offset
    parts.append(original[cursor:end_offset])
    return "".join(parts)


def render_region_expand_to_buffer(
    original: str,
    start_offset: int,
    end_offset: int,
    nodes: list[GroupNode],
    tokens: list[tokenize.TokenInfo],
    offsets: list[int],
    indent_unit: str,
    buffer: OutputBuffer,
) -> None:
    cursor = start_offset
    for node in sorted(nodes, key=lambda n: n.start_offset):
        buffer.append(original[cursor : node.start_offset])
        if is_expandable_group(node, tokens):
            base_indent = buffer.leading_whitespace()
            buffer.append(
                render_expanded_node(
                    node=node,
                    original=original,
                    tokens=tokens,
                    offsets=offsets,
                    indent_unit=indent_unit,
                    base_indent=base_indent,
                )
            )
        else:
            render_region_expand_to_buffer(
                original=original,
                start_offset=node.start_offset,
                end_offset=node.end_offset,
                nodes=node.children,
                tokens=tokens,
                offsets=offsets,
                indent_unit=indent_unit,
                buffer=buffer,
            )
        cursor = node.end_offset
    buffer.append(original[cursor:end_offset])


def render_region_expand_to_string(
    original: str,
    start_offset: int,
    end_offset: int,
    nodes: list[GroupNode],
    tokens: list[tokenize.TokenInfo],
    offsets: list[int],
    indent_unit: str,
    initial_line_prefix: str = "",
) -> str:
    buffer = OutputBuffer(current_line=initial_line_prefix)
    render_region_expand_to_buffer(
        original=original,
        start_offset=start_offset,
        end_offset=end_offset,
        nodes=nodes,
        tokens=tokens,
        offsets=offsets,
        indent_unit=indent_unit,
        buffer=buffer,
    )
    return buffer.render()


def render_expanded_node(
    node: GroupNode,
    original: str,
    tokens: list[tokenize.TokenInfo],
    offsets: list[int],
    indent_unit: str,
    base_indent: str,
) -> str:
    if node.close_index is None:
        return original[node.start_offset : node.end_offset]
    analysis = analyze_top_level_sequence(node, tokens)
    if analysis.blocked or not analysis.comma_indices:
        return render_region_expand_to_string(
            original=original,
            start_offset=node.start_offset,
            end_offset=node.end_offset,
            nodes=node.children,
            tokens=tokens,
            offsets=offsets,
            indent_unit=indent_unit,
            initial_line_prefix=base_indent,
        )
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
        item_text = render_region_expand_to_string(
            original=original,
            start_offset=item_start,
            end_offset=item_end,
            nodes=child_subset,
            tokens=tokens,
            offsets=offsets,
            indent_unit=indent_unit,
            initial_line_prefix=item_indent,
        ).strip()
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


def transform_source(text: str, mode: str, indent_unit: str) -> str:
    try:
        tokens = tokenize_text(text)
    except tokenize.TokenError:
        return text
    offsets = offset_table(text)
    roots = build_group_tree(tokens)
    annotate_group_offsets(roots, tokens, offsets)
    if mode == TRANSFORM_COMPRESS:
        compressed = render_region_compress(
            original=text,
            start_offset=0,
            end_offset=len(text),
            nodes=roots,
            tokens=tokens,
            offsets=offsets,
        )
        return drop_safe_trailing_commas(compressed)
    if mode == TRANSFORM_EXPAND:
        return render_region_expand_to_string(
            original=text,
            start_offset=0,
            end_offset=len(text),
            nodes=roots,
            tokens=tokens,
            offsets=offsets,
            indent_unit=indent_unit,
            initial_line_prefix="",
        )
    raise ValueError(f"unsupported mode: {mode}")


def iter_python_files(src_root: Path) -> list[Path]:
    return sorted(path for path in src_root.rglob("*.py") if path.is_file())


def process_file(path: Path, mode: str, indent_unit: str, *, check_only: bool = False) -> tuple[bool, str | None]:
    try:
        original, encoding = read_python_text(path)
    except Exception as exc:
        return False, f"read failed: {exc}"
    rewritten = transform_source(original, mode, indent_unit)
    if rewritten == original:
        return False, None
    if not check_only:
        try:
            write_python_text(path, rewritten, encoding)
        except Exception as exc:
            return False, f"write failed: {exc}"
    return True, None


def resolved_mode(args: argparse.Namespace) -> str:
    if args.compress:
        return TRANSFORM_COMPRESS
    if args.expand:
        return TRANSFORM_EXPAND
    raise ValueError("either --compress or --expand is required")


def main() -> int:
    args = parse_args()
    mode = resolved_mode(args)
    root = Path(args.root).resolve() if args.root is not None else Path(__file__).resolve().parent.parent
    src_root = Path(args.src).resolve() if args.src is not None else root / "src" / "ludoxel"
    if not src_root.is_dir():
        print(f"error: source root was not found: {src_root}", file=sys.stderr)
        return 2
    files = iter_python_files(src_root)
    if not files:
        print(f"error: no .py files were found under {src_root}", file=sys.stderr)
        return 2
    changed_count = 0
    error_count = 0
    for path in files:
        changed, error = process_file(path=path, mode=mode, indent_unit=args.indent, check_only=bool(args.check))
        if error is not None:
            error_count += 1
            print(f"[error] {path}: {error}", file=sys.stderr)
            continue
        if changed:
            changed_count += 1
            if args.verbose:
                print(path)
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
