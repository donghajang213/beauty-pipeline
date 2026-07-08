"""
파일: api/main.py
역할: 피부타입별 화장품 추천 REST API — 파이프라인의 최종 산출물(marts.recommendations)을 서빙.
흐름: 클라이언트 → Cloud Run(이 앱) → BigQuery marts 조회 → JSON 응답
실행(로컬): uv run uvicorn api.main:app --reload --port 8000
문서: 실행 후 http://localhost:8000/docs (FastAPI가 자동 생성하는 Swagger UI)

설계 노트:
- API는 marts만 읽는다 (raw/staging 접근 금지) — 계층 규칙의 마지막 조각.
- 추천 "계산"은 여기서 하지 않는다. dbt가 미리 계산한 테이블을 읽기만 한다.
  (서빙에서 무거운 계산을 하면 응답이 느리고 비용이 요청마다 발생 — 사전 계산 패턴)
"""

import logging
import os
from enum import StrEnum

from fastapi import FastAPI, HTTPException, Query
from google.cloud import bigquery
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Beauty Pipeline — 피부타입별 화장품 추천 API",
    description="식약처 공공데이터 × 행동 이벤트 기반 추천. 포트폴리오 프로젝트.",
    version="0.1.0",
)

# BigQuery 클라이언트는 프로세스당 1개 재사용 (요청마다 만들면 인증 왕복으로 느려진다)
_bq: bigquery.Client | None = None


def bq() -> bigquery.Client:
    global _bq
    if _bq is None:
        _bq = bigquery.Client()
    return _bq


class SkinType(StrEnum):  # StrEnum = str + Enum (파이썬 3.11+) — ruff UP042 권장
    """Enum으로 선언하면 FastAPI가 검증·문서화를 자동으로 해준다 — 잘못된 값은 422 응답."""

    dry = "dry"
    oily = "oily"
    combination = "combination"
    sensitive = "sensitive"
    normal = "normal"


class Recommendation(BaseModel):
    """응답 스키마 — pydantic 모델이 곧 API 문서가 된다."""

    rank: int
    product_id: str
    product_name: str
    category: str
    price_krw: int
    score: float
    has_restricted_ingredient: bool


@app.get("/health")
def health() -> dict:
    """Cloud Run/모니터링용 생존 확인 — 외부 의존성(BigQuery)은 건드리지 않는다."""
    return {"status": "ok"}


@app.get("/recommendations/{skin_type}", response_model=list[Recommendation])
def recommendations(
    skin_type: SkinType,
    limit: int = Query(default=10, ge=1, le=50, description="반환할 추천 수"),
) -> list[Recommendation]:
    """피부타입별 추천 상위 N개."""
    # 파라미터 바인딩(@skin_type)을 쓴다 — 문자열 조립은 SQL 인젝션의 문 (보안 기본기)
    query = f"""
        select rank, product_id, product_name, category, price_krw, score,
               has_restricted_ingredient
        from `{os.environ.get("GOOGLE_CLOUD_PROJECT", bq().project)}.marts.recommendations`
        where skin_type = @skin_type and rank <= @limit
        order by rank
    """
    job = bq().query(
        query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("skin_type", "STRING", skin_type.value),
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
            ]
        ),
    )
    rows = [Recommendation(**dict(r)) for r in job.result()]
    if not rows:
        # 데이터가 아직 없을 때 빈 200보다 명확한 신호 — 운영 시 원인 추적이 쉬움
        raise HTTPException(status_code=404, detail=f"{skin_type.value} 추천 데이터가 없습니다")
    return rows
