"""
파일: ingestion/batch/load_to_bq.py
역할: GCS 데이터 레이크의 JSONL을 BigQuery raw 데이터셋으로 적재 (파이프라인 3단계: DW Load).
입력: gs://{bucket}/raw/{source}/dt={날짜}/data.jsonl (fetch_to_gcs.py의 출력)
출력: BigQuery 테이블 raw.{source} 의 해당 날짜 파티션
실행: uv run python -m ingestion.batch.load_to_bq --source all
      uv run python -m ingestion.batch.load_to_bq --source regulation --date 2026-07-07

설계 결정 (면접 포인트):
1. load job 사용, 스트리밍 인서트 아님: 레이크에 파일이 이미 있으면 load job이 정답 —
   BigQuery load job은 "무료"이고, 스트리밍 인서트는 유료 + 중복 위험이 있다.
2. 파티션 데코레이터(raw.{source}$YYYYMMDD) + WRITE_TRUNCATE:
   "그 날짜 파티션만 통째로 교체"가 되어 재실행해도 중복이 없다(멱등).
   전체 테이블 TRUNCATE와 달리 다른 날짜의 스냅샷 이력은 보존된다.
3. 스키마 자동 감지(autodetect): raw 계층은 "원형 보존"이 목적이라 스키마를 손으로
   고정하지 않는다. 타입 정제는 다음 단계(dbt staging)의 책임.
"""

import argparse
import datetime as dt
import logging
import zoneinfo

from google.cloud import bigquery

from ingestion.config import get_settings
from ingestion.sources import SOURCES

logger = logging.getLogger(__name__)

KST = zoneinfo.ZoneInfo("Asia/Seoul")
RAW_DATASET = "raw"  # terraform/bigquery.tf 에서 생성한 데이터셋


def gcs_uri(bucket: str, source_name: str, snapshot_date: str) -> str:
    """fetch_to_gcs.blob_path와 같은 규칙으로 읽기 URI를 만든다 (쓰는 쪽과 규칙 공유)."""
    return f"gs://{bucket}/raw/{source_name}/dt={snapshot_date}/data.jsonl"


def partition_decorator(source_name: str, snapshot_date: str) -> str:
    """'테이블$YYYYMMDD' — BigQuery에서 특정 날짜 파티션만 지목하는 문법."""
    return f"{source_name}${snapshot_date.replace('-', '')}"


def load_source(client: bigquery.Client, bucket: str, source_name: str, date: str) -> int:
    """원천 하나의 스냅샷을 해당 날짜 파티션에 적재하고 행 수를 돌려준다."""
    uri = gcs_uri(bucket, source_name, date)
    table_ref = f"{client.project}.{RAW_DATASET}.{partition_decorator(source_name, date)}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True,  # raw 계층: 스키마는 자동 감지, 정제는 dbt가
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # 파티션 교체 = 멱등
        # 테이블이 처음 만들어질 때 "적재 시점 기준 일 단위 파티션" 테이블로 생성
        time_partitioning=bigquery.TimePartitioning(type_=bigquery.TimePartitioningType.DAY),
    )

    logger.info("[%s] 적재 시작: %s → %s", source_name, uri, table_ref)
    job = client.load_table_from_uri(uri, table_ref, job_config=job_config)
    job.result()  # load job은 비동기 — 완료(또는 실패)까지 대기

    rows = job.output_rows or 0
    logger.info("[%s] 적재 완료: %d행", source_name, rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="GCS raw JSONL → BigQuery 적재")
    parser.add_argument("--source", default="all", choices=["all", *SOURCES.keys()])
    parser.add_argument(
        "--date",
        default=dt.datetime.now(KST).date().isoformat(),
        help="적재할 스냅샷 날짜 YYYY-MM-DD (기본: 오늘/KST)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = get_settings()
    if not settings.gcs_raw_bucket:
        raise RuntimeError(".env에 GCS_RAW_BUCKET이 없습니다")

    client = bigquery.Client()  # 프로젝트는 ADC의 기본 프로젝트를 따른다 (gcloud config)

    names = list(SOURCES.keys()) if args.source == "all" else [args.source]
    total = sum(load_source(client, settings.gcs_raw_bucket, n, args.date) for n in names)
    logger.info("전체 적재 완료: %d개 테이블, 총 %d행 (dt=%s)", len(names), total, args.date)


if __name__ == "__main__":
    main()
