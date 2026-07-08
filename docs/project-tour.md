# 프로젝트 투어 — 데이터 엔지니어링의 흐름과 이 저장소의 모든 것

> **누구를 위한 문서**: 이 저장소를 처음 보는 사람(채용담당자, 면접관, 그리고 미래의 나).
> 데이터가 어떻게 흐르는지, 각 폴더가 그 흐름의 어디를 맡는지 한 번에 설명한다.

---

## 1. 데이터 엔지니어링의 흐름 — 이 프로젝트가 구현한 것

데이터 엔지니어의 일은 한 문장으로: **"원천의 지저분한 데이터를, 믿을 수 있는 형태로, 끊기지 않게 흘려보내는 배관을 만들고 운영하는 것"**.

```
                     ①수집          ②저장           ③적재          ④변환              ⑦서빙
  식약처 API ──────▶ ingestion ──▶ GCS 레이크 ──▶ BigQuery raw ──▶ dbt staging ──▶ marts ──▶ 추천 API
  (배치, 일 1회)     (재시도·멱등)   (원형 보존)     (파티션)        (정제·테스트)    (추천)    (Cloud Run)
                                                       ▲
  가상 사용자 ─────▶ 이벤트 생성기 ──▶ Pub/Sub ──▶ BigQuery 구독     ⑥스트리밍 (실시간)
  (조회/찜/구매/평점)                  (우체통)      (관리형 적재)

  ⑤오케스트레이션: Airflow가 ①~④를 매일 02:00 자동 실행, 실패 시 재시도
  밑바탕: Terraform(인프라 코드화) · CI(품질 게이트) · IAM(최소 권한) · 예산 알림(비용)
```

### 각 단계의 존재 이유 (면접 요약본)

| 단계 | 왜 필요한가 | 이 프로젝트의 핵심 결정 |
|---|---|---|
| ①수집 | 외부 세상은 불안정하다 — 재시도·타임아웃·멱등성이 없으면 매일 새벽 사람이 깨야 한다 | 전량 수집 후 원자적 업로드, 같은 날짜 재실행 = 덮어쓰기 |
| ②저장(레이크) | 가공 로직에 버그가 있어도 원본이 있으면 재처리 가능 | dt=날짜 Hive 파티션, 90일 수명, 원형(JSONL) 보존 |
| ③적재(DW) | 파일은 분석할 수 없다 — SQL이 닿는 곳으로 | load job(무료) + 파티션 데코레이터 교체(멱등) |
| ④변환 | 원본 그대로는 못 쓴다(이름·타입·중복·규제) — 정제를 한 곳에 모은다 | dbt: staging은 뷰, marts는 테이블. 테스트는 프로파일링 근거로만 |
| ⑤오케스트레이션 | 순서·재시도·이력을 사람이 아니라 기계가 관리 | 로컬 Docker Airflow (Composer 비용 회피), 재시도 2층 구조 |
| ⑥스트리밍 | 하루 뒤가 아니라 지금 일어나는 일 | Pub/Sub + BigQuery 구독 (Dataflow 배제 — ADR 001), event_id 중복 제거 |
| ⑦서빙 | 데이터의 최종 고객은 사람/서비스 | 사전 계산 패턴 — API는 marts를 읽기만. 스케일 투 제로 |

### 데이터가 실제로 흐른 증거 (숫자)

- 식약처 3개 API → **61,408건** 수집·적재 (원료성분 21,833 / 규제 7,257 / 제조업체 32,318)
- 품질 테스트가 잡은 실제 결함: 완전 중복 **176건**, 타입 오추론 3컬럼 (식별자→숫자)
- 스트리밍: 발행 300건 → 도착 300건 (유실 0, 지연 수 초)
- 추천 검증: 상위5 피부타입 매칭률 **72%** vs 무작위 36% (생성기에 심은 신호를 SQL로 복원)
- 장애 복구: 검증 이틀간 실제 장애 5건(PC 종료, 회선 단절×2, 캐시 오염 등) — 사람 개입 1회

---

## 2. 저장소 투어 — 폴더와 파일 전부

### 루트 문서 (프로젝트의 헌법)

| 파일 | 역할 |
|---|---|
| `README.md` | 첫인상 — 한 줄 소개, 스택, 아키텍처, 성과 숫자 |
| `PLAN.md` | 기획안 — 왜 이 프로젝트인가, JD→기술 매핑, 로드맵(체크박스), 비용 배분 |
| `RULES.md` | 작업 규칙 — 문서화/Git/보안/비용/IaC 원칙. 모든 결정의 근거 |
| `pyproject.toml` + `uv.lock` | 파이썬 의존성 명세와 정확한 버전 고정(재현성) |
| `.python-version` | Python 3.12 고정 (uv가 읽음) |
| `.env.example` | 시크릿 "양식" — 실제 값은 .env(비커밋)에만 |
| `.gitignore` | 시크릿/산출물 커밋 차단 (인라인 주석 금지 등 삽질의 흔적 포함) |

### terraform/ — 인프라 (①~⑦이 올라가는 땅)

| 파일 | 만드는 것 |
|---|---|
| `versions.tf` | Terraform 버전, GCS 원격 state, google 프로바이더 고정 |
| `variables.tf` | 입력값(project_id, region, api_image_tag, 공통 라벨) |
| `storage.tf` | 데이터 레이크 버킷 (public 차단, 90일 수명) |
| `bigquery.tf` | raw / staging / marts 데이터셋 — "그릇은 Terraform, 내용물은 dbt" |
| `pubsub.tf` | user-events 토픽, BigQuery 구독, events 테이블, 생성기 SA |
| `cloudrun.tf` | Artifact Registry, API 전용 SA, Cloud Run 서비스(스케일 투 제로) |
| `iam.tf` | 수집용 SA — 버킷/데이터셋 단위 최소 권한 |
| `outputs.tf` | 생성된 리소스 주소 (다른 코드가 참조) |

### ingestion/ — ①수집 + ⑥스트리밍의 발행 측

| 파일 | 역할 |
|---|---|
| `config.py` | .env 로드, fail-fast 검증 (시크릿과 코드의 분리) |
| `datago.py` | 공공데이터포털 공용 클라이언트 — 재시도(지수 백오프)·페이지네이션·오류 통일 |
| `sources.py` | 원천 레지스트리 — 검증된 API 이름/URL (설정과 로직의 분리) |
| `probe.py` | 새 API 탐침 CLI — 문서 없는 공공 API를 실호출로 검증 |
| `batch/fetch_to_gcs.py` | API → 레이크 (dt= 파티션, 멱등 덮어쓰기) |
| `batch/load_to_bq.py` | 레이크 → BigQuery (load job, 파티션 교체 멱등) |
| `streaming/generate_catalog.py` | 실제 성분 기반 합성 카탈로그 300제품 (시드 고정) |
| `streaming/event_generator.py` | 피부타입별 행동 모델 → Pub/Sub 발행 (숨겨진 신호 내장) |

### dbt/ — ④변환 (데이터 모델링의 본체)

| 파일 | 역할 |
|---|---|
| `dbt_project.yml` / `profiles.yml` | 프로젝트 설정 / BigQuery 연결(oauth — 키 파일 없음) |
| `macros/generate_schema_name.sql` | +schema를 데이터셋 이름 그대로 쓰는 표준 오버라이드 |
| `models/staging/_sources.yml` | raw 테이블 선언 (계보 추적의 시작점) |
| `models/staging/stg_ingredient.sql` | 성분 사전 — 컬럼 영문화, 중복 1건 제거 |
| `models/staging/stg_regulation.sql` | 성분×국가 규제 — grain 분석으로 unique 미적용 |
| `models/staging/stg_manufacturer.sql` | 타입 교정(식별자 INT64→STRING, lpad), 완전 중복 175건 제거 |
| `models/staging/stg_products.sql` | 합성 카탈로그 최신 스냅샷 |
| `models/staging/stg_events.sql` | 스트리밍 JSON 파싱 + event_id 중복 제거 (at-least-once 대응) |
| `models/marts/recommendations.sql` | **최종 산출물** — 행동 점수 × 규제 필터 × 피부타입 순위 |
| `models/*/_models.yml` | 품질 테스트 15건 선언 (grain 검증, accepted_values 등) |

### airflow/ — ⑤오케스트레이션

| 파일 | 역할 |
|---|---|
| `Dockerfile` / `docker-compose.yml` | 로컬 standalone Airflow (ADC 마운트 — 키 파일 없는 인증) |
| `dags/beauty_daily.py` | 매일 02:00: 3원천 fetch→load → dbt run→test, 재시도 5분×3 |

### api/ — ⑦서빙

| 파일 | 역할 |
|---|---|
| `main.py` | FastAPI — marts 조회 전용, Enum 검증 + 파라미터 바인딩 |
| `Dockerfile` / `requirements.txt` | slim + non-root 이미지, API 전용 최소 의존성 |

### 나머지

| 위치 | 역할 |
|---|---|
| `tests/` | 단위 테스트 18건 — 외부 서비스는 전부 mock (CI에서 시크릿 없이 돎) |
| `.github/workflows/ci.yml` | PR마다 ruff + pytest 자동 (병합 게이트) |
| `docs/adr/` | 아키텍처 결정 기록 (예: 001 이벤트 파이프라인 — Dataflow 배제 근거) |
| `docs/troubleshooting/` | 삽질 기록 (증상→원인→해결→배운 점) |
| `docs/iam.md` | 서비스 계정별 권한 대장 — "누가 무엇을 왜" |
| `docs/setup/`, `docs/weekly/` | 수동 부트스트랩 기록, 주간 회고 |
| `writing/` | 취업 글쓰기 — 블로그 초안, 자소서 소재은행(STAR), 포트폴리오 1페이지 |

---

## 3. 이 구조가 말하는 것 (관통하는 원칙)

1. **멱등성**: fetch도 load도 dbt도 "다시 실행"이 안전하다 — 장애 복구가 명령 하나
2. **원형 보존 → 단계적 정제**: raw는 안 건드리고, 정제는 staging, 비즈니스 로직은 marts — 문제가 생기면 어느 층인지 바로 안다
3. **최소 권한**: 계정마다 "그 일에 필요한 것만" — 규칙을 문서가 아니라 IAM으로 강제
4. **코드로 관리**: 인프라(Terraform), 파이프라인(파이썬), 변환(dbt), 스케줄(DAG), 품질(테스트) — 전부 리뷰·재현 가능
5. **비용 의식**: 상시 리소스 0개 (Airflow는 로컬, Cloud Run은 스케일 투 제로, 나머지는 사용량 과금)
