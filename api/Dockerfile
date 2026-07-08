# ─────────────────────────────────────────────────────────────
# 파일: api/Dockerfile
# 역할: 추천 API를 어디서나 똑같이 실행되는 컨테이너 이미지로 포장
# 빌드(저장소 루트에서): docker build -t recommendation-api -f api/Dockerfile .
# 원칙: 이미지는 최소로 — API가 import하는 것만 설치 (dbt/airflow 등 파이프라인 의존성 제외)
# ─────────────────────────────────────────────────────────────

FROM python:3.12-slim

# 보안 기본기: 컨테이너 안에서 root로 실행하지 않는다 (Trivy/보안 스캔 단골 지적사항)
RUN useradd --create-home appuser
WORKDIR /app

# 의존성 먼저 복사·설치 → 코드만 바뀌면 이 레이어는 캐시 재사용 (빌드 속도)
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
USER appuser

# Cloud Run은 PORT 환경변수로 포트를 지정한다 (기본 8080)
ENV PORT=8080
CMD exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT}
