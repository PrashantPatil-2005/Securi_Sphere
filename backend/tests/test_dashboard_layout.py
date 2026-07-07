from app.schemas.dashboard import DashboardWidget
from app.services.dashboard_layout import _normalize_widgets


def test_normalize_widgets_dedupes_ids():
    widgets = [
        DashboardWidget(id="kpis", visible=True),
        DashboardWidget(id="kpis", visible=False),
        DashboardWidget(id="timeline", visible=True),
    ]
    result = _normalize_widgets(widgets)
    assert len(result) == 2
    assert result[0]["id"] == "kpis"
    assert result[1]["id"] == "timeline"


def test_saved_search_widget_id_format():
    widget_id = "saved_search:550e8400-e29b-41d4-a716-446655440000"
    assert widget_id.startswith("saved_search:")
    assert len(widget_id) > len("saved_search:")
