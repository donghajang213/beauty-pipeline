"""
파일: ingestion/batch/fetch_to_gcs.py
역할: 식약처 API에서 데이터를 받아 GCS 데이터 레이크의 raw 영역에 저장 (파이프라인 1단계).
입력: 공공데이터포털 API (인증키는 .env / GCS 버킷명은 GCS_RAW_BUCKET)
출력: gs://{bucket}/raw/{source}/dt={날짜}/data.jsonl
실행: uv run python -m ingestion.batch.fetch_to_gcs --source all
      uv run python -m ingestion.batch.fetch_to_gcs --source regulation --date 2026-07-06

설계 결정 2가지 (면접 포인트):
1. 스냅샷 + 날짜 파티션: 이 API들은 "매일의 변경분"이 아니라 "전체 목록"을 주는 마스터성
   데이터다. 그래서 매일 전체를 dt=날짜 폴더에 스냅샷으로 남긴다 — 과거 시점 재현 가능.
2. 멱등성(idempotency): 같은 날짜로 재실행하면 같은 경로를 덮어쓴다(append 아님).
   재실행 = 중복이 아니라 갱신이 되도록 설계해야 장애 복구가 두렵지 않다 (RULES.md 3장).
"""

import argparse
import datetime as dt
import json
import logging
import zoneinfo

from google.cloud import storage

from ingestion.config import get_settings
from ingestion.datago import DataGoKrClient
from ingestion.sources import SOURCES, Source

logger = logging.getLogger(__name__)

KST = zoneinfo.ZoneInfo("Asia/Seoul")


def blob_path(source_name: str, snapshot_date: str) -> str:
    """GCS 안의 저장 경로를 만든다.

    dt={날짜} 형식은 Hive 파티션 관례 — BigQuery/Spark가 이 패턴을 파티션으로 인식해
    "특정 날짜만 읽기"가 가능해진다 (전체 스캔 방지 = 비용 절감).
    """
    return f"raw/{source_name}/dt={snapshot_date}/data.jsonl"


def to_jsonl(rows: list[dict]) -> str:
    """행 목록을 JSON Lines 형식(한 줄 = 한 레코드)으로 직렬화한다.

    JSONL을 쓰는 이유: BigQuery가 네이티브로 적재 지원 + 한 줄씩 스트리밍 처리 가능.
    ensure_ascii=False: 한글을 \\uXXXX 로 깨뜨리지 않고 그대로 저장 (사람이 읽을 수 있게).
    """
    return "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"


def fetch_source(client: DataGoKrClient, bucket: storage.Bucket, source: Source, date: str) -> int:
    """원천 하나를 수집해 GCS에 업로드하고 행 수를 돌려준다."""
    logger.info("[%s] 수집 시작: %s", source.name, source.description)
    rows = client.fetch_all(source.url, page_size=100)

    # 빈 결과는 업로드하지 않고 실패시킨다 — "조용히 빈 파일"은 하류(dbt)에서 원인 추적이 어렵다
    if not rows:
        raise RuntimeError(f"[{source.name}] 0건 수집 — API 이상 가능성, 업로드 중단")

    path = blob_path(source.name, date)
    # upload_from_string: 같은 경로에 다시 쓰면 덮어씀 → 재실행 멱등성의 실체
    bucket.blob(path).upload_from_string(to_jsonl(rows), content_type="application/jsonl")
    logger.info("[%s] 완료: %d건 → gs://%s/%s", source.name, len(rows), bucket.name, path)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="식약처 API → GCS raw 배치 수집")
    parser.add_argument(
        "--source",
        default="all",
        choices=["all", *SOURCES.keys()],
        help="수집할 원천 (기본 all)",
    )
    parser.add_argument(
        "--date",
        default=dt.datetime.now(KST).date().isoformat(),
        help="스냅샷 날짜 YYYY-MM-DD (기본: 오늘/KST) — 과거 날짜로 재실행(backfill) 가능",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = get_settings()
    if not settings.gcs_raw_bucket:
        raise RuntimeError(
            ".env에 GCS_RAW_BUCKET이 없습니다 (terraform output data_lake_bucket 값)"
        )

    client = DataGoKrClient(settings.data_go_kr_service_key)
    # GCS 클라이언트는 ADC(로컬: gcloud 로그인 / Cloud Run: 서비스 계정)로 자동 인증된다
    bucket = storage.Client().bucket(settings.gcs_raw_bucket)

    targets = list(SOURCES.values()) if args.source == "all" else [SOURCES[args.source]]
    total = sum(fetch_source(client, bucket, src, args.date) for src in targets)
    logger.info("전체 완료: %d개 원천, 총 %d건 (dt=%s)", len(targets), total, args.date)


if __name__ == "__main__":
    main()
