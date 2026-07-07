"""
파일: tests/test_load_to_bq.py
역할: BigQuery 적재기의 순수 로직(경로/파티션 규칙)을 GCP 없이 검증.
왜: 읽기 URI가 쓰기 경로(fetch_to_gcs)와 어긋나면 적재가 통째로 빈다 — 규칙 일치를 테스트로 고정.
"""

from ingestion.batch.fetch_to_gcs import blob_path
from ingestion.batch.load_to_bq import gcs_uri, partition_decorator


def test_read_uri_matches_write_path():
    """쓰는 쪽(fetch)과 읽는 쪽(load)의 경로 규칙이 항상 같아야 한다."""
    bucket = "my-bucket"
    assert gcs_uri(bucket, "ingredient", "2026-07-07") == (
        f"gs://{bucket}/" + blob_path("ingredient", "2026-07-07")
    )


def test_partition_decorator_format():
    """BigQuery 파티션 데코레이터는 하이픈 없는 YYYYMMDD 형식."""
    assert partition_decorator("regulation", "2026-07-07") == "regulation$20260707"
