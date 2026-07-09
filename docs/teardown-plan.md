# 철거 계획 — 크레딧 종료(2026-08-31) 대비

> **목적**: 크레딧이 끝나는 날, 당황하지 않고 순서대로 정리하기 위한 사전 계획.
> 원칙: 포트폴리오의 증거(코드, 문서, 블로그, 스크린샷)는 전부 GCP 밖에 있으므로
> GCP 리소스는 미련 없이 지울 수 있다 — 그게 처음부터 IaC로 만든 이유다.

## 지우기 전에 확보할 것 (8월 마지막 주)

- [ ] 스크린샷 아카이브: Airflow Grid(장애→복구), Looker Studio, Cloud Run 콘솔, BigQuery 계보
- [ ] 최종 숫자 기록: 총 처리 건수, 무인 운영 일수, 총 지출 → README/포트폴리오에 반영
- [ ] Looker Studio는 삭제되지 않지만 원천(BQ)이 사라지면 빈 껍데기 → 스크린샷 필수
- [ ] 최종 주간 회고 + 블로그 마무리 글

## 철거 순서

1. **Airflow 스케줄 정지**: `docker compose down` (로컬 — GCP 비용과 무관하지만 오류 로그 방지)
2. **Terraform 일괄 철거**: `cd terraform && terraform destroy`
   - 지워지는 것: 버킷(데이터 포함 — force_destroy), BQ 데이터셋 3개, Pub/Sub, Cloud Run,
     AR 이미지, SA 5개, 알림, WIF, Secret Manager
   - 예상 소요: ~10분. plan을 먼저 보고 destroy 대상 개수 확인
3. **수동 잔여물 정리** (Terraform 밖 — bootstrap 문서의 역순):
   - state 버킷: `gcloud storage rm -r gs://beauty-pipeline-499600-tfstate`
   - 예산 알림: `gcloud billing budgets delete <ID>` (제일 마지막 — 지우기 전까지 감시 유지)
4. **최종 확인**: 콘솔 결제 → 이 프로젝트 예상 비용 0원 확인. 필요시 프로젝트 자체를 종료 예약

## 철거 후에도 남는 것 (= 포트폴리오의 실체)

- GitHub 저장소 전체 (코드 + 문서 + PR 이력 19개+)
- 티스토리 블로그 시리즈
- `terraform apply` 한 번으로 언제든 전체 재현 가능하다는 사실 —
  면접에서 "지금은 꺼져 있지만 30분이면 다시 살립니다"가 가능한 상태

## 로컬 재현 모드 (크레딧 없이 시연)

- 수집기: `--date` 지정 실행으로 로컬에서 API→JSONL 생성 가능 (GCS 대신 로컬 저장 옵션은 필요 시 추가)
- Airflow: 로컬 Docker라 그대로 동작 (GCP 태스크만 실패 — DAG 구조 시연은 가능)
- API: 로컬 uvicorn + (재현 시) BigQuery 대신 목업 — 시연은 스크린샷/블로그로 대체 권장
