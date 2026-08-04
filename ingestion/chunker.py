from dataclasses import dataclass, field

from tree_sitter import Language, Parser
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript

from ingestion_config import CHUNK_NODE_TYPES

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


_PARSER_CACHE: dict[str, object] = {}


def _get_parser(language: str):
    if language not in _PARSER_CACHE:
        _PARSER_CACHE[language] = Parser(_LANGUAGES[language])
    return _PARSER_CACHE[language]


def _extract_name(node, source_bytes: bytes) -> str:
  
    for child in node.children:
        if child.type in ("identifier", "property_identifier", "type_identifier"):
            return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="ignore")
    return ""


def _decode(node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")


def _resolve_arrow_function_name(node, source_bytes: bytes) -> str | None:
   
    parent = node.parent
    if parent is None:
        return None

    # const handleSubmit = () => {...}
    if parent.type == "variable_declarator":
        for child in parent.children:
            if child.type == "identifier":
                return _decode(child, source_bytes)

    # this.handleSubmit = () => {...}  /  obj.prop = () => {...}
    if parent.type == "assignment_expression":
        left = parent.children[0] if parent.children else None
        if left is not None:
            return _decode(left, source_bytes)

    # { onSubmit: () => {...} }  — object property / method shorthand
    if parent.type == "pair":
        for child in parent.children:
            if child.type in ("property_identifier", "string"):
                return _decode(child, source_bytes).strip("'\"")


    return None


def chunk_file(file_path: str, language: str, source_code: str) -> list[CodeChunk]:
    
    parser = _get_parser(language)
    source_bytes = source_code.encode("utf-8")
    tree = parser.parse(source_bytes)

    target_types = CHUNK_NODE_TYPES.get(language, set())
    chunks: list[CodeChunk] = []

    def visit(node):
        if node.type in target_types:
            name = None
            skip_as_chunk = False

            if node.type == "arrow_function":
                name = _resolve_arrow_function_name(node, source_bytes)
                if name is None:
                   
                    skip_as_chunk = True
            else:
                name = _extract_name(node, source_bytes)

            if not skip_as_chunk:
                start_line = node.start_point[0] + 1  # tree-sitter rows are 0-indexed
                end_line = node.end_point[0] + 1
                code_text = _decode(node, source_bytes)
                chunks.append(
                    CodeChunk(
                        file_path=file_path,
                        language=language,
                        node_type=node.type,
                        name=name or "",
                        start_line=start_line,
                        end_line=end_line,
                        code=code_text,
                    )
                )
      

        for child in node.children:
            visit(child)

    visit(tree.root_node)
    return chunks


def chunk_whole_file_as_fallback(file_path: str, language: str, source_code: str) -> CodeChunk:
 
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