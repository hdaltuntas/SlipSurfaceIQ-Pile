"""Semantic-version utilities for the Suite, the core and the applications.

The Suite keeps three version families in step with each other:

    CORE_VERSION   the shared engineering library and plugin contract
    suite version   the launcher (``slipsurface.__version__``)
    app versions    each application module, one ``app.json`` each

Everything here is standard-library only, because the version machinery is
needed before any application — and therefore before any of their
dependencies — is imported.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

__all__ = ["parse", "compare", "is_compatible", "module_version", "VersionError"]

#: A release number: v-prefixed or not, optionally with a pre-release or a
#: build suffix (which this simplified comparison ignores, as the Suite only
#: ever ships stable releases).
_RELEASE = re.compile(r"^\s*v?(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?\s*$")

#: The compatibility operators an ``app.json`` ``requires_core`` may use
_OPS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}

_CLAUSE = re.compile(r"^(>=|<=|==|!=|>|<)?\s*(.+)$")


class VersionError(ValueError):
    """A version or a compatibility clause that cannot be read."""


def parse(version: str) -> tuple[int, int, int]:
    """Read ``1.2.3`` (or ``v1.2.3``) as a (major, minor, patch) tuple."""
    match = _RELEASE.match(str(version))
    if not match:
        raise VersionError(f"not a release version: {version!r}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def compare(a: str, b: str) -> int:
    """-1, 0 or 1 as release ``a`` is older than, equal to or newer than ``b``."""
    left, right = parse(a), parse(b)
    if left < right:
        return -1
    if left > right:
        return 1
    return 0


def is_compatible(core_version: str, spec: str) -> bool:
    """Whether ``core_version`` satisfies a ``requires_core`` specification.

    The specification is a comma-separated AND of clauses such as
    ``">=0.1.0,<0.2.0"``; a bare version counts as ``==``. An empty
    specification accepts any core.
    """
    if spec is None or not str(spec).strip():
        return True
    version = parse(core_version)
    for clause in str(spec).split(","):
        clause = clause.strip()
        if not clause:
            continue
        match = _CLAUSE.match(clause)
        if not match:
            raise VersionError(f"not a compatibility clause: {clause!r}")
        operator, target = match.group(1) or "==", match.group(2).strip()
        if not _OPS[operator](version, parse(target)):
            return False
    return True


def module_version(package_file: str) -> str:
    """Return a module's own version from its bundled or relocated manifest.

    In the Suite the manifest is adjacent to the package initializer; for
    independent modules it sits in the package's parent directory. This
    intentionally differs from the Suite version and CORE_VERSION.
    """
    directory = Path(package_file).resolve().parent
    for manifest in (directory / "app.json", directory.parent / "app.json"):
        if manifest.is_file():
            try:
                version = json.loads(manifest.read_text(encoding="utf-8"))["version"]
            except (OSError, ValueError, KeyError, TypeError) as error:
                raise VersionError(f"invalid module manifest: {manifest}") from error
            parse(version)
            return version
    raise VersionError(f"module manifest not found: {directory}")
