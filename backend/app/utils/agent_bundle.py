"""Resolve agent install assets for dev monorepo and Docker (/app/agent)."""
import io
import tarfile
from pathlib import Path

_AGENT_ROOT: Path | None = None
_BUNDLE_PATH: Path | None = None


def resolve_agent_root() -> Path:
    global _AGENT_ROOT
    if _AGENT_ROOT is not None:
        return _AGENT_ROOT

    here = Path(__file__).resolve()
    for base in (here.parents[2], here.parents[3]):
        candidate = base / "agent"
        if (candidate / "install.sh").exists():
            _AGENT_ROOT = candidate
            return candidate

    raise FileNotFoundError("Agent directory not found (expected agent/install.sh)")


def resolve_install_script() -> Path:
    script = resolve_agent_root() / "install.sh"
    if not script.is_file():
        raise FileNotFoundError(f"install.sh missing at {script}")
    return script


def resolve_agent_bundle() -> Path:
    """Return path to prebuilt tarball, or build one in memory cache path."""
    global _BUNDLE_PATH
    if _BUNDLE_PATH is not None and _BUNDLE_PATH.is_file():
        return _BUNDLE_PATH

    root = resolve_agent_root()
    prebuilt = root / "agent-bundle.tar.gz"
    if prebuilt.is_file():
        _BUNDLE_PATH = prebuilt
        return prebuilt

    # Dev fallback: build tarball on first request.
    _BUNDLE_PATH = root / ".agent-bundle.tar.gz"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name in ("agent", "requirements.txt"):
            path = root / name
            if path.exists():
                tar.add(path, arcname=name)
    _BUNDLE_PATH.write_bytes(buf.getvalue())
    return _BUNDLE_PATH
