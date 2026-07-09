"""
파일: labs/dataproc/regulated_origin_job.py
역할: [실습] PySpark로 데이터 레이크의 raw JSONL을 직접 읽어 분석 — Dataproc Serverless 검증용.
질문: "규제(금지/제한)에 걸린 성분들은 어떤 기원(식물/화학 등)에서 많이 나올까?"

왜 Spark인가 (BigQuery로도 되는 일인데):
  이 데이터(수만 건)는 사실 BigQuery가 더 간단하다. 이 잡의 목적은 분석 결과가 아니라
  "레이크의 파일을 DW를 거치지 않고 분산 엔진으로 직접 처리"하는 경로의 실습이다.
  데이터가 수억 건이 되어 BQ 적재 전 대규모 전처리가 필요해지는 시점에 이 경로가 본편이 된다.

실행 (로컬 파일을 제출하면 Dataproc이 서버리스로 실행):
  gcloud dataproc batches submit pyspark labs/dataproc/regulated_origin_job.py \
    --region=asia-northeast3 --deps-bucket=gs://{버킷} \
    --service-account=sa-ingestion@{프로젝트}.iam.gserviceaccount.com \
    -- --bucket {버킷} --date 2026-07-07
"""

import argparse

from pyspark.sql import SparkSession, functions as F


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True, help="데이터 레이크 버킷 이름")
    parser.add_argument("--date", required=True, help="분석할 스냅샷 날짜 (dt=)")
    args = parser.parse_args()

    # SparkSession = Spark 프로그램의 진입점. 서버리스에선 클러스터 설정 없이 이것만으로 시작.
    spark = SparkSession.builder.appName("regulated-origin-analysis").getOrCreate()

    # 레이크에서 직접 읽기 — BigQuery를 거치지 않는다 (스키마는 JSONL에서 자동 추론)
    base = f"gs://{args.bucket}/raw"
    ingredient = spark.read.json(f"{base}/ingredient/dt={args.date}/data.jsonl")
    regulation = spark.read.json(f"{base}/regulation/dt={args.date}/data.jsonl")

    # 성분 사전 × 규제 목록 조인 (한글 성분명 기준 — dbt staging과 같은 조인 키)
    joined = ingredient.join(
        regulation, ingredient.INGR_KOR_NAME == regulation.INGR_STD_NAME, "inner"
    )

    # 기원(origin)별 집계: 규제 걸린 성분 수 + 그중 '금지' 비율
    result = (
        joined.groupBy("ORIGIN_MAJOR_KOR_NAME")
        .agg(
            F.countDistinct("INGR_KOR_NAME").alias("regulated_ingredients"),
            F.round(F.avg(F.when(F.col("PROH_NATIONAL").isNotNull(), 1).otherwise(0)), 3).alias(
                "prohibited_ratio"
            ),
        )
        .orderBy(F.desc("regulated_ingredients"))
    )

    result.show(20, truncate=False)  # 드라이버 로그에 표로 출력 (검증용)

    # 결과를 레이크의 labs 영역에 파케이(컬럼형 포맷)로 저장 — 재실행 시 덮어쓰기(멱등)
    out = f"gs://{args.bucket}/labs/regulated_origin/dt={args.date}"
    result.coalesce(1).write.mode("overwrite").parquet(out)
    print(f"저장 완료: {out}")

    spark.stop()


if __name__ == "__main__":
    main()
