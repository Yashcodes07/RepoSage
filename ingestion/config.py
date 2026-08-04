"""
Configuration for repo ingestion: which dirs/files to skip, which
extensions map to which tree-sitter language.
"""

# Directories to skip entirely (never descend into these)
IGNORED_DIRS = {
    ".git", "node_modules", "dist", "build", "__pycache__",
    "venv", ".venv", "env", ".env", "target", "vendor",
    ".next", ".nuxt", "coverage", ".pytest_cache", "chroma_db",
    ".idea", ".vscode", "egg-info", ".mypy_cache", "site-packages",
}

# File extensions that are never source code (binaries, media, locks)
IGNORED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp",
    ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin",
    ".map", ".min.js", ".min.css",
    ".lock",
}

# File names to always skip regardless of extension
IGNORED_FILENAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Pipfile.lock", ".DS_Store",
}

# Max file size to parse (skip huge generated files, e.g. bundled JS)
MAX_FILE_SIZE_BYTES = 500_000  # 500 KB

# Maps file extension -> tree-sitter language name (per tree_sitter_languages)
EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".mts": "typescript",
    ".cts": "typescript",
}

# For each language, which AST node types count as a "chunk" (function/class-level unit)
CHUNK_NODE_TYPES = {
    "python": {"function_definition", "class_definition"},
    "javascript": {
        "function_declaration", "class_declaration",
        "method_definition", "arrow_function",
    },
    "typescript": {
        "function_declaration", "class_declaration",
        "method_definition", "arrow_function", "interface_declaration",
    },
    "tsx": {
        "function_declaration", "class_declaration",
        "method_definition", "arrow_function", "interface_declaration",
    },
}