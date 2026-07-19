"""
Step 2 of the pipeline: parse a source file with tree-sitter and
extract function/class-level chunks — the AST-aware alternative to
naive fixed-size text splitting.

Each chunk carries exactly the metadata we'll need later for citations:
file_path, start_line, end_line, function_name.
"""

from dataclasses import dataclass, field

from tree_sitter import Language, Parser
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript

from config import CHUNK_NODE_TYPES

# Build each Language object once at import time
_LANGUAGES = {
    "python": Language(tspython.language()),
    "javascript": Language(tsjavascript.language()),
    "typescript": Language(tstypescript.language_typescript()),
    "tsx": Language(tstypescript.language_tsx()),
}


@dataclass
class CodeChunk:
    file_path: str        # relative path, e.g. "app/ai/hybrid_search.py"
    language: str
    node_type: str         # "function_definition", "class_declaration", etc.
    name: str               # best-effort function/class name, "" if not found
    start_line: int         # 1-indexed, inclusive
    end_line: int            # 1-indexed, inclusive
    code: str                 # the raw source text of this chunk

    def citation(self) -> str:
        return f"{self.file_path}:{self.start_line}-{self.end_line}"


# Cache parsers per language so we don't rebuild them for every file
_PARSER_CACHE: dict[str, object] = {}


def _get_parser(language: str):
    if language not in _PARSER_CACHE:
        _PARSER_CACHE[language] = Parser(_LANGUAGES[language])
    return _PARSER_CACHE[language]


def _extract_name(node, source_bytes: bytes) -> str:
    """
    Best-effort: look for a child node of type 'identifier' (or
    'property_identifier' for JS class methods) to use as the chunk name.
    """
    for child in node.children:
        if child.type in ("identifier", "property_identifier", "type_identifier"):
            return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="ignore")
    return ""


def chunk_file(file_path: str, language: str, source_code: str) -> list[CodeChunk]:
    """
    Parses source_code with the appropriate tree-sitter grammar and
    returns one CodeChunk per top-level (and nested) function/class node.
    """
    parser = _get_parser(language)
    source_bytes = source_code.encode("utf-8")
    tree = parser.parse(source_bytes)

    target_types = CHUNK_NODE_TYPES.get(language, set())
    chunks: list[CodeChunk] = []

    def visit(node):
        if node.type in target_types:
            start_line = node.start_point[0] + 1  # tree-sitter rows are 0-indexed
            end_line = node.end_point[0] + 1
            code_text = source_bytes[node.start_byte:node.end_byte].decode(
                "utf-8", errors="ignore"
            )
            chunks.append(
                CodeChunk(
                    file_path=file_path,
                    language=language,
                    node_type=node.type,
                    name=_extract_name(node, source_bytes),
                    start_line=start_line,
                    end_line=end_line,
                    code=code_text,
                )
            )
            # Don't recurse into this node's children for chunk purposes —
            # avoids double-counting e.g. a method inside a class as both
            # part of the class chunk AND its own chunk. We still want
            # nested classes/functions found though, so recurse anyway
            # but callers can dedupe by (file, start, end) if needed.

        for child in node.children:
            visit(child)

    visit(tree.root_node)
    return chunks


def chunk_whole_file_as_fallback(file_path: str, language: str, source_code: str) -> CodeChunk:
    """
    If a file has no detectable functions/classes (e.g. a small config
    or __init__.py), fall back to treating the whole file as one chunk
    so we don't silently drop it from the index.
    """
    line_count = source_code.count("\n") + 1
    return CodeChunk(
        file_path=file_path,
        language=language,
        node_type="whole_file",
        name=file_path.split("/")[-1],
        start_line=1,
        end_line=line_count,
        code=source_code,
    )