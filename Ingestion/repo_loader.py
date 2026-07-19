"""
Step 1 of the pipeline: clone a GitHub repo (shallow) and walk its
file tree, yielding only files worth parsing.
"""

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import git  # GitPython

from config import (
    IGNORED_DIRS,
    IGNORED_EXTENSIONS,
    IGNORED_FILENAMES,
    MAX_FILE_SIZE_BYTES,
    EXTENSION_TO_LANGUAGE,
)


@dataclass
class SourceFile:
    absolute_path: Path
    relative_path: str   # relative to repo root, e.g. "app/api/routes.py"
    language: str         # "python" | "javascript" | "typescript" | "tsx"


def clone_repo(repo_url: str, dest_dir: str | None = None) -> Path:
    """
    Shallow-clones a GitHub repo and returns the local path.
    If dest_dir is None, clones into a fresh temp directory.
    """
    if dest_dir is None:
        dest_dir = tempfile.mkdtemp(prefix="codebase_rag_")
    else:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)

    git.Repo.clone_from(repo_url, dest_dir, depth=1, single_branch=True)
    return Path(dest_dir)


def _is_ignored_file(path: Path) -> bool:
    if path.name in IGNORED_FILENAMES:
        return True
    if path.suffix in IGNORED_EXTENSIONS:
        return True
    if path.name.endswith(".min.js") or path.name.endswith(".min.css"):
        return True
    try:
        if path.stat().st_size > MAX_FILE_SIZE_BYTES:
            return True
    except OSError:
        return True
    return False


def walk_repo(repo_root: Path) -> list[SourceFile]:
    """
    Walks the repo tree, skipping ignored dirs, and returns every
    source file we know how to parse (i.e. has a supported extension).
    """
    source_files: list[SourceFile] = []

    for dirpath, dirnames, filenames in os.walk(repo_root):
        # prune ignored dirs in-place so os.walk doesn't descend into them
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]

        for fname in filenames:
            fpath = Path(dirpath) / fname
            ext = fpath.suffix

            if ext not in EXTENSION_TO_LANGUAGE:
                continue
            if _is_ignored_file(fpath):
                continue

            rel_path = str(fpath.relative_to(repo_root)).replace(os.sep, "/")
            source_files.append(
                SourceFile(
                    absolute_path=fpath,
                    relative_path=rel_path,
                    language=EXTENSION_TO_LANGUAGE[ext],
                )
            )

    return source_files


if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/Yashcodes07/QueDB.git"
    root = clone_repo(url, dest_dir="/home/claude/codebase_rag/_tmp_repo")
    files = walk_repo(root)
    print(f"Found {len(files)} source files to parse")
    for f in files[:15]:
        print(f"  [{f.language}] {f.relative_path}")