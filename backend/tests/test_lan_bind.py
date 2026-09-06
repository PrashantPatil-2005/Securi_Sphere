from app.utils.lan_bind import validate_server_url_interface


def test_loopback_server_url_is_allowed():
    validate_server_url_interface("http://127.0.0.1:8000", local_ips={"10.0.0.5"})
    validate_server_url_interface("http://localhost:8000", local_ips={"10.0.0.5"})


def test_hostname_server_url_is_allowed():
    validate_server_url_interface("https://securi.example.com", local_ips={"10.0.0.5"})


def test_matching_lan_ip_is_allowed():
    validate_server_url_interface("http://10.0.0.5:8000", local_ips={"10.0.0.5", "127.0.0.1"})


def test_stale_lan_ip_raises():
    try:
        validate_server_url_interface(
            "http://10.255.255.1:8000",
            local_ips={"10.0.0.5", "127.0.0.1"},
        )
    except ValueError as exc:
        msg = str(exc)
        assert "10.255.255.1" in msg
        assert "10.0.0.5" in msg
        assert "sync-lan-urls.ps1" in msg
    else:
        raise AssertionError("expected ValueError for stale SERVER_URL")


def test_skip_flag_bypasses_check():
    validate_server_url_interface(
        "http://10.255.255.1:8000",
        skip=True,
        local_ips={"10.0.0.1"},
    )


def test_tracked_source_has_no_stale_wifi_ip():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    skip_parts = {".git", "node_modules", "venv", "__pycache__", ".next"}
    banned = ("192.168.0." + "107", "192.168.0." + "106")
    hits = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_parts for part in path.parts):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2", ".gz", ".zip"}:
            continue
        if path.name in {".env", ".env.local"} or path.name.endswith(".env"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for needle in banned:
            if needle in text:
                hits.append(f"{path.relative_to(root)}: {needle}")
    assert hits == [], "hardcoded LAN IPs found:\n" + "\n".join(hits)
