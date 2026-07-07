from app.services.csp import build_api_csp, build_html_csp, generate_nonce


def test_generate_nonce_length():
    nonce = generate_nonce()
    assert len(nonce) >= 16


def test_generate_nonce_unique():
    assert generate_nonce() != generate_nonce()


def test_build_api_csp_strict():
    csp = build_api_csp()
    assert "default-src 'none'" in csp
    assert "unsafe-inline" not in csp


def test_build_api_csp_report_uri():
    csp = build_api_csp(report_uri="https://example.com/csp")
    assert "report-uri https://example.com/csp" in csp


def test_build_html_csp_includes_nonce():
    csp = build_html_csp("abc123")
    assert "'nonce-abc123'" in csp
    assert "strict-dynamic" in csp
