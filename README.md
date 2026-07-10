# 🧴 Beauty Pipeline — 피부타입별 화장품 추천 데이터 플랫폼

> 식약처 공공 데이터(배치)와 사용자 행동 이벤트(스트리밍)를 GCP에서 처리해
> **피부타입별 화장품 추천 API**로 서빙하는 엔드투엔드 데이터 플랫폼.
> 인프라 100% Terraform, CI 보안 게이트 3종, 키리스 CD — 1인 프로젝트, 상시 비용 0원.

**🔗 라이브 데모**: [추천 API (Swagger)](https://recommendation-api-bfvsee2ydq-du.a.run.app/docs) ·
[호출 예시](https://recommendation-api-bfvsee2ydq-du.a.run.app/recommendations/dry?limit=3) ·
[📊 대시보드 (Looker Studio)](https://datastudio.google.com/reporting/8dac604e-c634-483e-a1d5-3b90c51202d2)
**📖 처음이라면**: [프로젝트 투어](docs/project-tour.md) — 데이터 흐름과 모든 폴더 5분 안내

## 아키텍처

```
①수집          ②저장(레이크)    ③적재(DW)       ④변환             ⑦서빙
식약처 API ──▶ GCS dt=파티션 ──▶ BigQuery raw ─▶ dbt staging→marts ─▶ 추천 API
(재시도·멱등)   (원형 보존)      (파티션 교체)    (품질 테스트 17건)   (Cloud Run)
가상 사용자 ──▶ 이벤트 생성기 ──▶ Pub/Sub ──▶ BigQuery 구독      ⑥스트리밍 (컨슈머 코드 0줄)
⑤오케스트레이션: Airflow 일 배치 (재시도 2층) · 밑바탕: Terraform / CI·CD / 최소권한 IAM / 알림
```

## 검증된 숫자

| 항목 | 결과 |
|---|---|
| 배치 수집 | 식약처 3개 API **61,408건** → 레이크 → DW (멱등 설계 — 실제 회선 단절 3회를 재실행만으로 복구) |
| 스트리밍 | 발행 300건 → 도착 300건 (**유실 0**), event_id 중복 제거로 at-least-once 대응 |
| 데이터 품질 | dbt 테스트가 실결함 탐지: 완전 중복 176건, 타입 오추론 3컬럼 |
| 추천 정확성 | 합성 데이터에 심은 선호 신호를 SQL로 복원 — 상위5 매칭률 **72% vs 무작위 36%** |
| 무인 운영 | Airflow가 PC 종료·인터넷 단절 등 실장애 5건을 자동 재시도/재개로 극복 (개입 1회) |
| 보안 | gitleaks 이력 유출 0 · Trivy HIGH/CRITICAL 0 · 키 파일 0개 (키리스 인증 3종) |
| 비용 | 상시 리소스 0 — 두 달 운영 예상 지출이 크레딧의 수 % 수준 |

## 기술 스택과 "왜"

| 영역 | 선택 | 안 쓴 것과 이유 |
|---|---|---|
| 수집/오케스트레이션 | Python 3.12, Airflow(로컬 Docker) | Cloud Composer — 월 수십만 원 상시 비용은 규모 대비 과잉 |
| 스트리밍 | Pub/Sub + BigQuery 구독 | Dataflow — 초당 수 건에 상시 워커는 과잉 ([ADR 001](docs/adr/001-event-pipeline.md)) |
| 저장/변환 | GCS·BigQuery·dbt | Spark — 수만 건엔 BQ가 정답 (단, [실습으로 검증](docs/labs/001-dataproc-serverless.md)) |
| 서빙 | FastAPI + Cloud Run | GKE — 단순 HTTP엔 Run ([실습으로 비교](docs/labs/002-gke-autopilot.md)) |
| 인프라/보안 | Terraform, WIF, Secret Manager, gitleaks/Bandit/Trivy | SA 키 파일 — 만들지 않으면 유출도 없다 |

## 저장소 지도

| 위치 | 내용 |
|---|---|
| [PLAN.md](PLAN.md) / [RULES.md](RULES.md) | 기획안(JD→기술 매핑, 로드맵) / 작업 규칙 |
| [terraform/](terraform/) · [ingestion/](ingestion/) · [dbt/](dbt/) · [airflow/](airflow/) · [api/](api/) | 파이프라인 단계별 코드 (각 폴더에 README) |
| [docs/adr/](docs/adr/) · [docs/troubleshooting/](docs/troubleshooting/) · [docs/labs/](docs/labs/) | 결정 기록 / 삽질 기록 / 단기 실습 실측 |
| [docs/iam.md](docs/iam.md) · [docs/teardown-plan.md](docs/teardown-plan.md) | 권한 대장 / 크레딧 종료 철거 계획 |
| [docs/greenfield-playbook.md](docs/greenfield-playbook.md) | 0에서 데이터 플랫폼을 세우는 순서 — 이 저장소가 워크드 예제 |

## 재현 방법

```bash
git clone https://github.com/donghajang213/beauty-pipeline && cd beauty-pipeline
uv sync && cp .env.example .env          # 공공데이터포털 키 입력
cd terraform && terraform init && terraform apply   # 인프라 전체 (~10분)
uv run python -m ingestion.batch.fetch_to_gcs      # 첫 수집
```
상세 실행법은 각 폴더 README 참조. 전 과정이 코드라 **처음부터 끝까지 재현 가능**합니다.
