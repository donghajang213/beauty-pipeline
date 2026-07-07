"""
파일: airflow/dags/beauty_daily.py
역할: 하루 한 번 전체 배치 파이프라인을 실행하는 DAG 정의.

DAG(Directed Acyclic Graph) = "작업들과 그 순서"를 코드로 그린 방향 그래프.
Airflow는 이 그래프를 읽고 ① 스케줄에 맞춰 실행 ② 순서 보장 ③ 실패 시 재시도
④ 이력/로그 관리를 해준다. 우리가 손으로 하던 fetch → load → dbt의 자동화.

그래프 모양 (원천별 fetch→load는 병렬, 변환은 전체 적재 후 한 번):
    fetch_ingredient   ──▶ load_ingredient   ─┐
    fetch_regulation   ──▶ load_regulation   ─┼─▶ dbt_run ──▶ dbt_test
    fetch_manufacturer ──▶ load_manufacturer ─┘
"""

from datetime import timedelta

import pendulum
from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator

# 수집 대상 — ingestion/sources.py의 레지스트리와 같은 이름 (한 곳이 늘면 양쪽 갱신)
SOURCES = ["ingredient", "regulation", "manufacturer"]

# 모든 태스크의 공통 기본값
default_args = {
    "retries": 3,  # 이번 주 3번의 네트워크 단절이 가르쳐준 값 — 일시 장애는 Airflow가 알아서 재시도
    "retry_delay": timedelta(minutes=5),  # 코드 안 백오프(초 단위)보다 긴 호흡의 재시도
}

with DAG(
    dag_id="beauty_daily",
    description="식약처 화장품 데이터 일 배치: fetch → load → dbt",
    # cron 표현식: 매일 02:00 (KST — compose의 DEFAULT_TIMEZONE 기준)
    # 새벽인 이유: 공공 API 갱신 후 + 사용량 적은 시간대
    schedule="0 2 * * *",
    start_date=pendulum.datetime(2026, 7, 1, tz="Asia/Seoul"),
    # catchup=False: 과거 미실행분을 소급 실행하지 않음 (스냅샷 데이터라 과거 재실행은 무의미)
    catchup=False,
    default_args=default_args,
    tags=["batch", "beauty-pipeline"],
) as dag:
    # dbt: 전체 적재가 끝난 뒤 staging 갱신 → 품질 테스트
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="cd /opt/beauty/dbt && dbt run --profiles-dir .",
    )
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="cd /opt/beauty/dbt && dbt test --profiles-dir .",
    )

    for source in SOURCES:
        # {{ ds }} = Airflow가 주입하는 "실행 기준 날짜" 템플릿 변수.
        # 명시적으로 날짜를 넘기므로, 과거 날짜로 수동 재실행(backfill)해도 그 날짜로 동작한다.
        fetch = BashOperator(
            task_id=f"fetch_{source}",
            bash_command=(
                "cd /opt/beauty && "
                f"python -m ingestion.batch.fetch_to_gcs --source {source} --date {{{{ ds }}}}"
            ),
        )
        load = BashOperator(
            task_id=f"load_{source}",
            bash_command=(
                "cd /opt/beauty && "
                f"python -m ingestion.batch.load_to_bq --source {source} --date {{{{ ds }}}}"
            ),
        )
        # >> = "왼쪽이 성공해야 오른쪽 실행" (의존성 선언)
        fetch >> load >> dbt_run

    dbt_run >> dbt_test
