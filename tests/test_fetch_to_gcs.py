"""
파일: tests/test_fetch_to_gcs.py
역할: fetch 스크립트의 순수 로직(경로 규칙, 직렬화)을 GCS 없이 검증.
왜: 업로드 자체는 구글 라이브러리의 몫 — 우리가 책임지는 "경로 규칙"과 "데이터 형식"만 테스트.
"""

import json

from ingestion.batch.fetch_to_gcs import blob_path, to_jsonl


def test_blob_path_follows_hive_partition_convention():
    """dt={날짜} Hive 파티션 관례를 지키는지 — 이 규칙이 깨지면 BigQuery 파티션 인식 실패."""
    assert blob_path("ingredient", "2026-07-06") == "raw/ingredient/dt=2026-07-06/data.jsonl"


def test_to_jsonl_one_line_per_record():
    """한 줄 = 한 레코드, 마지막 줄바꿈 포함 (BigQuery JSONL 규격)."""
    text = to_jsonl([{"a": 1}, {"b": 2}])
    lines = text.strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"a": 1}
    assert text.endswith("\n")


def test_to_jsonl_keeps_korean_readable():
    """한글이 \\uXXXX 이스케이프 없이 원문 그대로 저장되는지."""
    text = to_jsonl([{"INGR_KOR_NAME": "가공소금"}])
    assert "가공소금" in text
