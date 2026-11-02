from app.services.pdf import render_report_html


def test_render_html_includes_cover_title_and_meta():
    snapshot = {
        "sections": [
            {"id": "cover", "title": "Kapak", "kind": "cover", "body": "Acme Raporu\nTarih: 2026-11"}
        ]
    }
    html = render_report_html(snapshot)
    assert "Acme Raporu" in html
    assert "Tarih: 2026-11" in html


def test_render_html_escapes_user_content():
    snapshot = {
        "sections": [
            {
                "id": "s1",
                "title": "<script>alert(1)</script>",
                "kind": "text",
                "body": "<b>zararlı</b> içerik",
            }
        ]
    }
    html = render_report_html(snapshot)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<b>zararlı</b>" not in html


def test_render_html_applies_risk_color_to_findings():
    snapshot = {
        "sections": [
            {
                "id": "findings",
                "title": "Bulgular",
                "kind": "findings",
                "body": "critical:Kimlik doğrulama atlatması\nlow:Eski TLS",
            }
        ]
    }
    html = render_report_html(snapshot)
    assert "#B3261E" in html  # critical
    assert "#1F7A52" in html  # low
    assert "Kimlik doğrulama atlatması" in html


def test_render_html_handles_empty_sections():
    html = render_report_html({"sections": []})
    assert "<html" in html
