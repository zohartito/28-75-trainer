"""Descriptor-bound filesystem and bounded-input primitives for local reviews."""

from __future__ import annotations

import json
import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Iterator


MAX_REVIEW_FILES = 10_000
MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_FOLDER_BYTES = 4 * 1024 * 1024 * 1024
MAX_JSON_BYTES = 5 * 1024 * 1024
MAX_XMP_BYTES = 1 * 1024 * 1024
READ_CHUNK_BYTES = 1024 * 1024


def absolute_path(path: str | Path) -> Path:
    """Return a lexical absolute path without following a leaf link."""

    return Path(os.path.abspath(os.path.expanduser(os.fspath(path))))


def _system_alias_normalized(path: str | Path) -> Path:
    """Normalize stable macOS aliases without consulting a mutable leaf path."""

    absolute = absolute_path(path)
    if absolute.parts[:2] in {("/", "var"), ("/", "tmp"), ("/", "etc")}:
        return Path("/private") / Path(*absolute.parts[1:])
    return absolute


def require_safe_component(value: str, *, label: str = "name") -> str:
    if not value or len(value) > 64 or value in {".", ".."}:
        raise ValueError(f"{label} must be one non-empty path component of at most 64 characters")
    if value != Path(value).name:
        raise ValueError(f"{label} must be exactly one safe path component")
    if any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-" for character in value):
        raise ValueError(f"{label} may contain only letters, numbers, dot, underscore, and hyphen")
    return value


def _directory_flags() -> int:
    if not hasattr(os, "O_NOFOLLOW"):
        raise OSError("This platform cannot safely open no-follow paths")
    return os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW


def _open_directory(path: Path) -> int:
    """Open a directory chain without resolving or following path links."""

    # macOS intentionally aliases /var and /tmp. Normalize those fixed system
    # aliases lexically, then use no-follow descriptors for every component.
    canonical = _system_alias_normalized(path)
    fd = os.open("/", _directory_flags())
    try:
        for part in canonical.parts[1:]:
            next_fd = os.open(part, _directory_flags(), dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except Exception:
        os.close(fd)
        raise


def _identity(file_stat: os.stat_result) -> tuple[int, int, int, int, int]:
    return (file_stat.st_dev, file_stat.st_ino, file_stat.st_size, file_stat.st_mtime_ns, file_stat.st_ctime_ns)


def file_identity(handle: BinaryIO) -> tuple[int, int, int, int, int]:
    return _identity(os.fstat(handle.fileno()))


def verify_file_unchanged(handle: BinaryIO, identity: tuple[int, int, int, int, int]) -> None:
    if identity != file_identity(handle):
        raise ValueError("File changed while being processed")


def _verify_regular_file(fd: int, *, max_bytes: int, label: str) -> tuple[int, int, int, int, int]:
    file_stat = os.fstat(fd)
    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError(f"Refusing non-regular file: {label}")
    if file_stat.st_size > max_bytes:
        raise ValueError(f"File exceeds the {max_bytes} byte limit: {label}")
    return _identity(file_stat)


@dataclass(frozen=True)
class ReviewEntry:
    relative: Path
    is_symlink: bool


class ReviewRoot:
    """A retained review-root descriptor used for traversal and leaf opening."""

    def __init__(self, path: str | Path):
        self.path = _system_alias_normalized(path)
        self.fd = _open_directory(self.path)
        self._closed = False

    def __enter__(self) -> "ReviewRoot":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed:
            os.close(self.fd)
            self._closed = True

    def relative(self, path: str | Path) -> Path:
        try:
            relative = _system_alias_normalized(path).relative_to(self.path)
        except ValueError as exc:
            raise ValueError(f"Path is outside the allowed root: {path}") from exc
        if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
            raise ValueError("Expected a file below the allowed root")
        return relative

    def open_regular(self, path: str | Path, *, max_bytes: int) -> BinaryIO:
        relative = self.relative(path)
        directory_fd = os.dup(self.fd)
        try:
            for component in relative.parts[:-1]:
                next_fd = os.open(component, _directory_flags(), dir_fd=directory_fd)
                os.close(directory_fd)
                directory_fd = next_fd
            fd = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
            try:
                _verify_regular_file(fd, max_bytes=max_bytes, label=str(relative))
                return os.fdopen(fd, "rb")
            except Exception:
                os.close(fd)
                raise
        finally:
            os.close(directory_fd)

    def iter_entries(self, *, max_entries: int = MAX_REVIEW_FILES) -> Iterator[ReviewEntry]:
        """Stream every entry while bounding files, directories, and symlinks."""

        count = 0

        def walk(directory_fd: int, relative: Path) -> Iterator[ReviewEntry]:
            nonlocal count
            with os.scandir(directory_fd) as entries:
                for entry in entries:
                    count += 1
                    if count > max_entries:
                        raise ValueError(f"Review folder exceeds the {max_entries} entry limit")
                    entry_relative = relative / entry.name
                    if entry.is_symlink():
                        yield ReviewEntry(entry_relative, True)
                    elif entry.is_dir(follow_symlinks=False):
                        child_fd = os.open(entry.name, _directory_flags(), dir_fd=directory_fd)
                        try:
                            yield from walk(child_fd, entry_relative)
                        finally:
                            os.close(child_fd)
                    elif entry.is_file(follow_symlinks=False):
                        yield ReviewEntry(entry_relative, False)

        yield from walk(self.fd, Path())


def open_regular_file(path: str | Path, *, max_bytes: int, root: ReviewRoot | str | Path | None = None) -> BinaryIO:
    if isinstance(root, ReviewRoot):
        return root.open_regular(path, max_bytes=max_bytes)
    if root is not None:
        with ReviewRoot(root) as review_root:
            # Duplicate the descriptor through fdopen before the context closes.
            return review_root.open_regular(path, max_bytes=max_bytes)
    target = absolute_path(path)
    directory_fd = _open_directory(target.parent)
    try:
        fd = os.open(target.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
        try:
            _verify_regular_file(fd, max_bytes=max_bytes, label=str(target))
            return os.fdopen(fd, "rb")
        except Exception:
            os.close(fd)
            raise
    finally:
        os.close(directory_fd)


def read_bounded(handle: BinaryIO, *, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = handle.read(min(READ_CHUNK_BYTES, max_bytes - total + 1))
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > max_bytes:
            raise ValueError(f"Read exceeds the {max_bytes} byte limit")
        chunks.append(chunk)


class BoundedReader:
    """A file-like reader that never lets a parser consume past its budget."""

    def __init__(self, handle: BinaryIO, *, max_bytes: int):
        self.handle = handle
        self.max_bytes = max_bytes
        self.total = 0

    def read(self, size: int = -1) -> bytes:
        # Request at most one byte past the remaining budget.  This turns a
        # concurrently growing file into a bounded failure instead of letting
        # a parser's internal buffering read arbitrary data.
        remaining_plus_one = self.max_bytes - self.total + 1
        request = remaining_plus_one if size < 0 else min(size, remaining_plus_one)
        chunk = self.handle.read(request)
        self.total += len(chunk)
        if self.total > self.max_bytes:
            raise ValueError(f"Read exceeds the {self.max_bytes} byte limit")
        return chunk


def hash_bounded(handle: BinaryIO, *, max_bytes: int) -> str:
    import hashlib

    before = _identity(os.fstat(handle.fileno()))
    digest = hashlib.sha256()
    total = 0
    while True:
        chunk = handle.read(READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValueError(f"Hash read exceeds the {max_bytes} byte limit")
        digest.update(chunk)
    if before != _identity(os.fstat(handle.fileno())):
        raise ValueError("File changed while being hashed")
    return digest.hexdigest()


def copy_bounded(source: BinaryIO, target: BinaryIO, *, max_bytes: int) -> int:
    before = _identity(os.fstat(source.fileno()))
    total = 0
    while True:
        chunk = source.read(READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValueError(f"Copy read exceeds the {max_bytes} byte limit")
        target.write(chunk)
    if before != _identity(os.fstat(source.fileno())):
        raise ValueError("Source file changed while being copied")
    return total


def load_json_object(path: str | Path, *, max_bytes: int = MAX_JSON_BYTES) -> dict[str, Any]:
    try:
        with open_regular_file(path, max_bytes=max_bytes) as handle:
            raw = read_bounded(handle, max_bytes=max_bytes)
        data = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, OverflowError, RecursionError, TypeError, ValueError) as exc:
        raise ValueError("JSON input is invalid, oversized, or too deeply nested") from exc
    if not isinstance(data, dict):
        raise ValueError("JSON input must be an object")
    return data


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"JSON constant is not allowed: {value}")


class OutputTarget:
    """An output leaf whose parent descriptor remains open through publish."""

    def __init__(self, path: str | Path):
        self.path = _system_alias_normalized(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.parent_fd = _open_directory(self.path.parent)
        except OSError as exc:
            raise ValueError(f"Refusing to write through an unsafe output parent: {self.path.parent}") from exc
        self.name = self.path.name
        self._closed = False

    def __enter__(self) -> "OutputTarget":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed:
            os.close(self.parent_fd)
            self._closed = True

    def leaf_is_symlink(self) -> bool:
        try:
            return stat.S_ISLNK(os.stat(self.name, dir_fd=self.parent_fd, follow_symlinks=False).st_mode)
        except FileNotFoundError:
            return False

    def write_text(self, content: str) -> Path:
        return self._write(content.encode("utf-8"))

    def write_bytes(self, content: bytes) -> Path:
        return self._write(content)

    def append_text(self, content: str, *, initial: str = "") -> Path:
        """Append to a regular no-follow leaf through the retained parent."""
        fd = os.open(
            self.name, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
            0o600, dir_fd=self.parent_fd,
        )
        with os.fdopen(fd, "ab") as handle:
            file_stat = os.fstat(handle.fileno())
            if not stat.S_ISREG(file_stat.st_mode):
                raise ValueError(f"Refusing non-regular output: {self.path}")
            if file_stat.st_size == 0:
                handle.write(initial.encode("utf-8"))
            handle.write(content.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        return self.path

    def _write(self, content: bytes) -> Path:
        temporary_name = f".{self.name}.{secrets.token_hex(16)}.tmp"
        temporary_fd: int | None = None
        try:
            temporary_fd = os.open(
                temporary_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=self.parent_fd,
            )
            with os.fdopen(temporary_fd, "wb") as handle:
                temporary_fd = None
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.name, src_dir_fd=self.parent_fd, dst_dir_fd=self.parent_fd)
            os.fsync(self.parent_fd)
            return self.path
        except Exception:
            if temporary_fd is not None:
                os.close(temporary_fd)
            try:
                os.unlink(temporary_name, dir_fd=self.parent_fd)
            except FileNotFoundError:
                pass
            raise


def prepare_output_target(path: str | Path) -> OutputTarget:
    return OutputTarget(path)


class OutputDirectory:
    """Retained destination directory descriptor for exclusive generated leaves."""

    def __init__(self, path: str | Path):
        self.path = _system_alias_normalized(path)
        self.path.mkdir(parents=True, exist_ok=True)
        try:
            self.fd = _open_directory(self.path)
        except OSError as exc:
            raise ValueError(f"Refusing to use an unsafe output directory: {self.path}") from exc
        self._closed = False

    def __enter__(self) -> "OutputDirectory":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed:
            os.close(self.fd)
            self._closed = True

    def open_exclusive(self, name: str) -> BinaryIO:
        require_safe_component(name, label="output filename")
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
        return os.fdopen(fd, "wb")

    def unlink(self, name: str) -> None:
        require_safe_component(name, label="output filename")
        os.unlink(name, dir_fd=self.fd)

    def atomic_write_bytes(self, name: str, content: bytes) -> None:
        """Atomically replace one safe leaf through this retained directory."""

        require_safe_component(name, label="output filename")
        temporary_name = f".{name}.{secrets.token_hex(16)}.tmp"
        temporary_fd: int | None = None
        try:
            temporary_fd = os.open(
                temporary_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=self.fd,
            )
            with os.fdopen(temporary_fd, "wb") as handle:
                temporary_fd = None
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, name, src_dir_fd=self.fd, dst_dir_fd=self.fd)
            os.fsync(self.fd)
        except Exception:
            if temporary_fd is not None:
                os.close(temporary_fd)
            try:
                os.unlink(temporary_name, dir_fd=self.fd)
            except FileNotFoundError:
                pass
            raise

    def atomic_write_text(self, name: str, content: str) -> None:
        self.atomic_write_bytes(name, content.encode("utf-8"))


def atomic_write_text(path: str | Path | OutputTarget, content: str) -> Path:
    if isinstance(path, OutputTarget):
        return path.write_text(content)
    with prepare_output_target(path) as target:
        return target.write_text(content)


def atomic_write_bytes(path: str | Path | OutputTarget, content: bytes) -> Path:
    if isinstance(path, OutputTarget):
        return path.write_bytes(content)
    with prepare_output_target(path) as target:
        return target.write_bytes(content)
