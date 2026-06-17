"""Fix UTF-16 encoded text files on Windows (convert to UTF-8)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"node_modules", "venv", ".next", "__pycache__", ".pytest_cache", ".git", "site-packages"}
TEXT_EXTENSIONS = {
    ".py", ".yml", ".yaml", ".txt", ".md", ".sh", ".ts", ".tsx", ".css", ".json",
    ".example", ".service", ".ini", ".env", ".local", ".js", ".mjs", ".toml",
}


def fix_file(path: Path) -> bool:
    data = path.read_bytes()
    if b"\x00" not in data:
        return False
    if data.startswith(b"\xff\xfe"):
        text = data.decode("utf-16")
    elif data.startswith(b"\xfe\xff"):
        text = data.decode("utf-16-be")
    else:
        text = data.decode("utf-16-le")
    path.write_text(text.replace("\r\n", "\n").replace("\r", "\n"), encoding="utf-8", newline="\n")
    return True


def main() -> None:
    fixed = []
    for path in ROOT.rglob("*"):
        if path.is_dir() or any(p in SKIP_DIRS for p in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS and path.name not in {".env", ".env.example"}:
            continue
        try:
            if fix_file(path):
                fixed.append(path.relative_to(ROOT))
        except Exception as exc:
            print(f"Error: {path.relative_to(ROOT)}: {exc}")
    if fixed:
        print(f"Fixed {len(fixed)} file(s):")
        for f in fixed:
            print(f"  {f}")
    else:
        print("No encoding issues found.")


if __name__ == "__main__":
    main()
