"""
파일: ingestion/streaming/generate_catalog.py
역할: 가상 화장품 카탈로그(300개)를 생성해 데이터 레이크와 BigQuery(raw.products)에 적재.
왜 가상인가: 제품↔성분 매핑 공공 데이터가 없다 (ADR 001 결정 3).
    대신 "실제 성분명(stg_ingredient)"을 재료로 써서, 추천 로직이
    실제 규제 데이터와 조인될 수 있는 카탈로그를 합성한다.
실행: uv run python -m ingestion.streaming.generate_catalog
멱등성: 시드 고정(--seed) → 같은 시드로 몇 번을 돌려도 같은 카탈로그 + 같은 경로 덮어쓰기.
"""

import argparse
import datetime as dt
import logging
import random
import zoneinfo

from google.cloud import bigquery, storage

from ingestion.batch.fetch_to_gcs import blob_path, to_jsonl
from ingestion.batch.load_to_bq import load_source
from ingestion.config import get_settings

logger = logging.getLogger(__name__)
KST = zoneinfo.ZoneInfo("Asia/Seoul")

SKIN_TYPES = ["dry", "oily", "combination", "sensitive", "normal"]
CATEGORIES = ["스킨토너", "에센스세럼", "크림로션", "클렌징", "선케어", "마스크팩"]
BRANDS = ["퓨어랩", "글로우본", "세라린", "허브셀", "아쿠아논", "미모리"]
LINES = ["수분", "진정", "미백", "탄력", "저자극", "모공"]


def fetch_real_ingredient_names(client: bigquery.Client, limit: int = 2000) -> list[str]:
    """실제 성분 사전에서 성분명을 가져온다 — 합성 카탈로그에 '진짜 재료'를 쓰기 위해."""
    # f-string에는 신뢰된 값(프로젝트 ID, 정수 limit)만 — 외부 입력 없음
    query = f"""
        select ingredient_name_kr
        from `{client.project}.staging.stg_ingredient`
        where ingredient_name_kr is not null
        limit {limit}
    """
    return [row.ingredient_name_kr for row in client.query(query).result()]


def build_catalog(ingredient_names: list[str], size: int, seed: int) -> list[dict]:
    """시드 고정 난수로 제품 목록을 만든다. 같은 입력 = 같은 출력 (재현 가능)."""
    rng = random.Random(seed)  # 전역 random 대신 인스턴스 — 다른 코드와 시드 간섭 방지
    catalog = []
    for i in range(size):
        category = rng.choice(CATEGORIES)
        target = rng.choice(SKIN_TYPES + ["all"])  # 'all' = 모든 피부용
        catalog.append(
            {
                "product_id": f"p_{i:04d}",
                "product_name": f"{rng.choice(BRANDS)} {rng.choice(LINES)} {category}",
                "category": category,
                "target_skin_type": target,
                "price_krw": rng.randrange(8000, 60000, 500),
                # 실제 성분명 3~6개 — 나중에 규제 테이블(stg_regulation)과 조인되는 연결고리
                "key_ingredients": rng.sample(ingredient_names, k=rng.randint(3, 6)),
            }
        )
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="가상 화장품 카탈로그 생성 → GCS + BigQuery")
    parser.add_argument("--size", type=int, default=300, help="제품 수 (기본 300)")
    parser.add_argument("--seed", type=int, default=42, help="난수 시드 — 고정하면 재현 가능")
    parser.add_argument("--date", default=dt.datetime.now(KST).date().isoformat())
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = get_settings()
    if not settings.gcs_raw_bucket:
        raise RuntimeError(".env에 GCS_RAW_BUCKET이 없습니다")

    bq = bigquery.Client()
    names = fetch_real_ingredient_names(bq)
    logger.info("실제 성분명 %d개 확보", len(names))

    catalog = build_catalog(names, size=args.size, seed=args.seed)

    # 배치 수집기와 같은 규칙으로 레이크에 저장 → 같은 load 함수로 BigQuery 적재 (경로 규칙 재사용)
    bucket = storage.Client().bucket(settings.gcs_raw_bucket)
    path = blob_path("products", args.date)
    bucket.blob(path).upload_from_string(to_jsonl(catalog), content_type="application/jsonl")
    logger.info("카탈로그 %d개 → gs://%s/%s", len(catalog), bucket.name, path)

    rows = load_source(bq, settings.gcs_raw_bucket, "products", args.date)
    logger.info("BigQuery 적재 완료: raw.products %d행", rows)


if __name__ == "__main__":
    main()
