"""
파일: tests/test_datago.py
역할: DataGoKrClient의 핵심 로직(페이지 순회, 오류 감지)을 실제 API 없이 검증.
왜: 외부 API에 의존하는 테스트는 느리고 불안정하다 → 가짜 응답(mock)으로 "우리 코드"만 검증.
    (RULES.md 3장: 외부 API 호출은 mock 처리)
실행: uv run pytest
"""

import pytest

from ingestion.datago import DataGoKrClient, DataGoKrError, _extract_body


def _client_with_fake_pages(monkeypatch, pages: list[dict]) -> DataGoKrClient:
    """get_page가 미리 준비한 가짜 응답을 순서대로 돌려주도록 바꿔치기(monkeypatch)한다."""
    client = DataGoKrClient(service_key="fake-key")
    calls = iter(pages)
    monkeypatch.setattr(client, "get_page", lambda *a, **k: next(calls))
    return client


def test_fetch_all_paginates_until_total(monkeypatch):
    """totalCount(3건)를 채울 때까지 2페이지를 순회해 모두 모으는지 검증."""
    page1_items = [{"id": 1}, {"id": 2}]
    pages = [
        {"header": {"resultCode": "00"}, "body": {"totalCount": 3, "items": page1_items}},
        {"header": {"resultCode": "00"}, "body": {"totalCount": 3, "items": [{"id": 3}]}},
    ]
    client = _client_with_fake_pages(monkeypatch, pages)

    rows = client.fetch_all("http://fake", page_size=2)

    assert [r["id"] for r in rows] == [1, 2, 3]


def test_fetch_all_stops_on_empty_page(monkeypatch):
    """서버가 totalCount보다 적게 주고 빈 페이지를 반환해도 무한 루프에 빠지지 않는지 검증."""
    pages = [
        {"header": {"resultCode": "00"}, "body": {"totalCount": 99, "items": [{"id": 1}]}},
        {"header": {"resultCode": "00"}, "body": {"totalCount": 99, "items": []}},
    ]
    client = _client_with_fake_pages(monkeypatch, pages)

    rows = client.fetch_all("http://fake", page_size=1)

    assert len(rows) == 1


def test_error_code_raises():
    """포털이 오류 코드(30 = 등록되지 않은 키)를 주면 전용 예외가 나는지 검증."""
    bad = {"header": {"resultCode": "30", "resultMsg": "SERVICE_KEY_IS_NOT_REGISTERED_ERROR"}}
    with pytest.raises(DataGoKrError, match="30"):
        _extract_body(bad)


def test_extract_body_handles_response_wrapper():
    """구형({"response": {...}}) 응답 껍데기도 body를 꺼내는지 검증."""
    data = {"response": {"header": {"resultCode": "00"}, "body": {"totalCount": 0, "items": []}}}
    assert _extract_body(data) == {"totalCount": 0, "items": []}
