# 실습 001 — Dataproc Serverless로 Spark 배치 (만들고 → 기록하고 → 남는 것 0)

> **목적**: JD 단골 "Spark 경험"을 상시 클러스터 비용 없이 확보.
> **원칙**: 실습은 실데이터로, 기록은 재현 가능하게, 종료 후 상시 리소스 0.

## 무엇을 했나

- 데이터 레이크의 raw JSONL(성분 21,833 + 규제 7,257)을 **BigQuery를 거치지 않고** Spark로 직접 조인/집계
- 질문: "규제에 걸린 성분은 어떤 기원(식물/화학 등)에서 많이 나올까?"
- 잡: [labs/dataproc/regulated_origin_job.py](../../labs/dataproc/regulated_origin_job.py) — 결과는 레이크 `labs/` 영역에 파케이 저장

## 왜 Serverless인가 (Dataproc 클러스터 대비)

| | 클러스터 방식 | Serverless |
|---|---|---|
| 준비 | 클러스터 생성/관리 (상시 비용) | 잡 제출만 — 실행 시간만큼 과금 |
| 이번 실습 비용 | 시간당 수천 원 + 끄는 걸 잊으면 참사 | (실행 후 기입) |
| 실무 사용처 | 장시간/상시 워크로드 | 간헐적 배치 — 우리 케이스 |

## 실행 결과 (실측, 2026-07-09)

- 배치 ID `330003d1aec144fba0c4fba85328cde4` — SUCCEEDED (기동 포함 약 3분)
- 결과: 규제 성분의 기원 1위는 유기화합물 계열(103종, 금지 비율 18.3%),
  색소 계열은 규제 다수이나 전면 금지 0% — 결과 파케이는 `labs/regulated_origin/dt=2026-07-07`
- 비용: 기본 12 DCU × 약 3분 ≈ **100원 미만** (상시 클러스터였다면 시간당 수천 원)

## 삽질 기록

1. **PowerShell이 `--` 구분자를 삼킴**: 잡 인자가 gcloud 옵션으로 오인됨 → Bash에서 제출
2. **Windows gcloud의 스테이징 버그**: 로컬 .py 제출 시 GCS 스테이징 경로를 백슬래시로
   생성(`dependencies\job.py`) → `URISyntaxException`. 우회: 파일을 직접 GCS에 올리고
   `gs://` URI로 제출 (스테이징 단계 제거). 교훈 — Windows에서 클라우드 CLI는 경로 처리를 의심할 것

## 배운 것 / 면접 포인트

- 레이크(파일) → Spark 직접 처리 경로는 "BQ 적재 전 대규모 전처리"가 필요할 때의 본편 —
  지금 규모(수만 건)에선 BigQuery가 더 낫다는 판단까지가 학습이다
- Serverless Spark의 트레이드오프: 기동 지연(콜드스타트 ~1분) vs 관리 비용 0
- 실행 SA(sa-ingestion)에 dataproc.worker만 추가 — 최소 권한 원칙 유지

## 정리(철거) 확인

- Dataproc Serverless는 잡 종료와 함께 컴퓨팅이 사라진다 — 지울 클러스터 자체가 없음
- 남은 것: GCS의 결과 파케이(수 KB, 90일 수명 규칙 적용) + IAM 바인딩 1건(문서화)
