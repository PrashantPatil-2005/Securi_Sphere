"""Tests for post-ingestion pipeline composition."""

import inspect

from app.pipeline import processor


def test_post_ingestion_pipeline_omits_cross_host_correlation():
    """Cross-host correlation runs on a scheduler, not on every ingest batch."""
    source = inspect.getsource(processor.run_post_ingestion_pipeline)
    assert "run_cross_host_correlation" not in source
