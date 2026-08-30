from unittest.mock import MagicMock, patch

from agent.collector.metrics import collect_metrics, get_os_info


def test_collect_metrics_shape():
    mock_mem = MagicMock()
    mock_mem.percent = 45.2

    mock_disk = MagicMock()
    mock_disk.percent = 70.1

    mock_net = MagicMock()
    mock_net.bytes_recv = 1024
    mock_net.bytes_sent = 2048

    with (
        patch("agent.collector.metrics.psutil") as mock_psutil,
        patch("agent.collector.metrics.time") as mock_time,
    ):
        mock_psutil.cpu_percent.return_value = 25.0
        mock_psutil.virtual_memory.return_value = mock_mem
        mock_psutil.disk_usage.return_value = mock_disk
        mock_psutil.net_io_counters.return_value = mock_net
        mock_psutil.getloadavg.return_value = (1.0, 1.5, 2.0)
        mock_psutil.boot_time.return_value = 1700000000.0
        mock_time.time.return_value = 1700086400.0
        mock_time.strftime.return_value = "2023-11-15T00:00:00Z"

        result = collect_metrics()

    assert isinstance(result, dict)
    assert "cpu_percent" in result
    assert "memory_percent" in result
    assert "disk_percent" in result
    assert "network_in" in result
    assert "network_out" in result
    assert "load_average" in result
    assert "uptime_seconds" in result
    assert "recorded_at" in result
    assert result["cpu_percent"] == 25.0
    assert result["memory_percent"] == 45.2
    assert result["network_in"] == 1024


def test_get_os_info():
    result = get_os_info()
    assert isinstance(result, str)
    assert len(result) > 0
