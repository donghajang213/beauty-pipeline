"""
파일: tests/test_api.py
역할: API의 검증/직렬화 로직을 BigQuery 없이 테스트 (FastAPI TestClient + mock).
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import api.main as api_main
from api.main import app

client = TestClient(app)


def test_health_needs_no_gcp():
    """헬스체크는 외부 의존성 없이 항상 200이어야 한다 (Cloud Run 기동 판정용)."""
    assert client.get("/health").json() == {"status": "ok"}


def test_invalid_skin_type_rejected():
    """Enum 밖의 값은 쿼리 실행 전에 422로 거절 — 잘못된 입력이 BigQuery까지 가지 않는다."""
    assert client.get("/recommendations/robot").status_code == 422


def test_recommendations_shape(monkeypatch):
    """정상 조회 시 응답 스키마가 계약(Recommendation 모델)대로인지 검증."""
    fake_row = {
        "rank": 1,
        "product_id": "p_0001",
        "product_name": "퓨어랩 수분 크림로션",
        "category": "크림로션",
        "price_krw": 12000,
        "score": 42.5,
        "has_restricted_ingredient": False,
    }
    fake_client = MagicMock()
    fake_client.project = "test-project"
    fake_client.query.return_value.result.return_value = [fake_row]
    monkeypatch.setattr(api_main, "_bq", fake_client)

    resp = client.get("/recommendations/dry?limit=1")

    assert resp.status_code == 200
    assert resp.json()[0]["product_id"] == "p_0001"


def test_empty_result_is_404(monkeypatch):
    """마트가 비어 있으면 조용한 빈 배열 대신 404 — 운영 시 원인 추적을 위해."""
    fake_client = MagicMock()
    fake_client.project = "test-project"
    fake_client.query.return_value.result.return_value = []
    monkeypatch.setattr(api_main, "_bq", fake_client)

    assert client.get("/recommendations/oily").status_code == 404
