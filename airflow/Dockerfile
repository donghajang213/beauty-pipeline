# ─────────────────────────────────────────────────────────────
# 파일: airflow/Dockerfile
# 역할: 공식 Airflow 이미지 위에 "우리 파이프라인의 의존성"을 얹은 커스텀 이미지
# 왜: Airflow가 fetch/load/dbt를 실행하려면 컨테이너 안에도 같은 라이브러리가 필요하다.
#     (Airflow는 Windows에서 네이티브 실행 불가 → Docker가 표준 실행 방법)
# ─────────────────────────────────────────────────────────────

FROM apache/airflow:2.10.4-python3.12

# 파이프라인 의존성 — pyproject.toml의 runtime 의존성과 같은 목록을 유지할 것
RUN pip install --no-cache-dir \
    "requests>=2.32" \
    "python-dotenv>=1.0" \
    "google-cloud-storage>=2.16" \
    "google-cloud-bigquery>=3.25" \
    "dbt-bigquery>=1.9"
