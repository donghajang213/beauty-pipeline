# 00 — 부트스트랩 기록 (수동 작업)

> RULES.md 6장: 모든 리소스는 Terraform으로 관리하되, Terraform 이전에 필요한 최초 수동 작업은 여기에 기록한다.

## 수행 내역

| 날짜 | 작업 | 방법 | 비고 |
|---|---|---|---|
| 2026-06-16 | GCP 프로젝트 생성 | 콘솔 (수동) | 프로젝트 ID: `beauty-pipeline-499600` |
| 2026-07-06 | 삭제 요청 상태였던 프로젝트 복구 | `gcloud projects undelete` | 6월에 삭제했던 것을 재사용 |
| 2026-07-06 | Git 저장소 초기화, GitHub 리포 생성 (private) | git / gh CLI | https://github.com/donghajang213/beauty-pipeline |
| 2026-07-06 | 결제 계정 연결 | `gcloud billing projects link` | 계정 `01A59C-739527-82790C` (KRW) |
| 2026-07-06 | 필수 API 활성화 | `gcloud services enable` | BigQuery, GCS, Pub/Sub, Cloud Run, Secret Manager, Monitoring, Logging, IAM, Artifact Registry, Budgets |
| 2026-07-06 | 예산 알림 생성 | `gcloud billing budgets create` | **크레딧 제외(gross) 기준**으로 소진 속도 감시 |
| 2026-07-06 | 예산 금액 확정 | `gcloud billing budgets update` | 실제 잔액 ₩432,898 확인 → 월 ₩216,000 (2개월 분할, PLAN.md 6.1 배분 계획 참조) |
| 2026-07-06 | 공공데이터포털 식약처 화장품 API 활용 신청 | 웹 (수동) | 승인 대기 시간 있음 |

## 왜 이 작업들은 수동인가?

- **GCP 프로젝트 생성 / 결제 연결**: Terraform을 실행할 프로젝트 자체가 있어야 하므로 (닭과 달걀 문제).
- **공공데이터포털 신청**: 사람 인증이 필요한 웹 절차.
- 이후의 모든 GCP 리소스(버킷, 데이터셋, 토픽, 서비스 계정 등)는 Terraform으로만 생성한다.
