# 🧴 Beauty Pipeline — 피부타입별 화장품 추천 데이터 플랫폼

> 식약처 공공 화장품 데이터(배치)와 가상 사용자 행동 이벤트(스트리밍)를 GCP 위에서 처리해,
> **피부타입별 화장품 추천 API**를 제공하는 엔드투엔드 데이터 플랫폼입니다.
> 모든 인프라는 Terraform으로 관리되고, CI/CD와 보안 스캔이 자동화되어 있습니다.

🚧 **현재 상태**: Phase 0 (기반 구축) 진행 중 — [로드맵](PLAN.md#5-단계별-로드맵)

## 문서 안내

| 문서 | 내용 |
|---|---|
| [PLAN.md](PLAN.md) | 기획안 — 왜 이 프로젝트인가, JD→기술 매핑, 아키텍처, 로드맵 |
| [RULES.md](RULES.md) | 작업 규칙 — 문서화/Git/보안/비용 원칙 |
| [docs/](docs/) | 결정 기록(ADR), 트러블슈팅, 주간 회고 |

## 기술 스택

- **수집/처리**: Python 3.12, Airflow(배치 오케스트레이션), Pub/Sub(스트리밍)
- **저장/변환**: GCS(데이터 레이크), BigQuery(DW), dbt(변환/품질 테스트)
- **서빙**: FastAPI, Cloud Run
- **인프라/운영**: Terraform(IaC), GitHub Actions(CI/CD), Cloud Monitoring
- **보안**: Secret Manager, gitleaks, Bandit, Trivy

## 아키텍처

> 상세 다이어그램은 [PLAN.md 3장](PLAN.md#3-목표-아키텍처) 참조. 프로젝트 진행에 따라 갱신됩니다.

```
식약처 API ──[배치/Airflow]──▶ GCS ──▶ BigQuery ──▶ dbt(추천 mart) ──▶ 추천 API(FastAPI)
가상 이벤트 ──[스트리밍]──▶ Pub/Sub ──▶ BigQuery ──────────────┘
```
