"""Тесты журнала отчётов и правила подтверждения перед отправкой."""

from tools.list_reports import get_stats, list_reports


def test_list_reports_returns_list(data_dir):
    reports = list_reports(limit=5)
    assert isinstance(reports, list)


def test_get_stats_keys(data_dir):
    stats = get_stats()
    assert isinstance(stats, dict)
    for key in ("total", "drafts", "approved", "sent", "approval_rate"):
        assert key in stats


def test_send_requires_approved():
    """Отправка несуществующего/неподтверждённого отчёта должна падать."""
    from tools.send_report import send_report

    result = send_report(999999, "nonexistent.pdf", "engineer@example.com")
    assert result["status"] == "error"
    assert result["error"]


def test_send_rejects_bad_recipient():
    from tools.send_report import send_report

    result = send_report(1, "nonexistent.pdf", "not-an-email")
    assert result["status"] == "error"
