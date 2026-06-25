"""Build and resolve agent install assets for dev monorepo and Docker (/app/agent)."""
import io
import tarfile
from pathlib import Path

_AGENT_ROOT: Path | None = None

# Paths that must exist inside agent-bundle.tar.gz (POSIX-style, no leading ./)
REQUIRED_BUNDLE_PATHS = frozenset({"agent/main.py", "requirements.txt"})


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


def _normalize_tar_name(name: str) -> str:
    return name.lstrip("./").replace("\\", "/")


def bundle_paths(tar_path: Path) -> set[str]:
    """Return normalized member paths inside a tarball."""
    with tarfile.open(tar_path, "r:gz") as tar:
        return {_normalize_tar_name(m.name) for m in tar.getmembers() if m.isfile()}


def validate_bundle(tar_path: Path) -> bool:
    """True if tarball unpacks to agent/main.py + requirements.txt at archive root."""
    if not tar_path.is_file() or tar_path.stat().st_size == 0:
        return False
    try:
        paths = bundle_paths(tar_path)
    except (tarfile.TarError, OSError):
        return False
    return REQUIRED_BUNDLE_PATHS.issubset(paths)


def build_agent_bundle(dest: Path | None = None) -> Path:
    """
    Create agent-bundle.tar.gz with layout:
      agent/main.py, agent/..., requirements.txt
    """
    root = resolve_agent_root()
    package_dir = root / "agent"
    requirements = root / "requirements.txt"

    if not (package_dir / "main.py").is_file():
        raise FileNotFoundError(
            f"Python package not found at {package_dir}/main.py. "
            f"Expected repo layout: agent/agent/main.py beside agent/requirements.txt"
        )
    if not requirements.is_file():
        raise FileNotFoundError(f"requirements.txt not found at {requirements}")

    out = dest or (root / "agent-bundle.tar.gz")
    out.parent.mkdir(parents=True, exist_ok=True)

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.GNU_FORMAT) as tar:
        tar.add(package_dir, arcname="agent")
        tar.add(requirements, arcname="requirements.txt")

    data = buf.getvalue()
    out.write_bytes(data)

    if not validate_bundle(out):
        out.unlink(missing_ok=True)
        raise RuntimeError(f"Built bundle at {out} failed validation (missing agent/main.py)")

    return out


def resolve_agent_bundle() -> Path:
    """Return a validated agent-bundle.tar.gz, rebuilding if missing or invalid."""
    root = resolve_agent_root()

    for candidate in (root / "agent-bundle.tar.gz", root / ".agent-bundle.tar.gz"):
        if validate_bundle(candidate):
            return candidate

    return build_agent_bundle(root / "agent-bundle.tar.gz")
