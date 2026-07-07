# ─────────────────────────────────────────────────────────────
# 파일: terraform/outputs.tf
# 역할: apply 후 "만들어진 리소스의 주소"를 출력 (함수의 반환값 같은 것)
# 왜: 수집 스크립트가 버킷 이름/SA 이메일을 하드코딩하지 않고 이 출력값을 받아 쓰게 한다.
#     `terraform output data_lake_bucket` 처럼 CLI로도 조회 가능.
# ─────────────────────────────────────────────────────────────

output "data_lake_bucket" {
  description = "데이터 레이크 버킷 이름 (수집 스크립트의 업로드 대상)"
  value       = google_storage_bucket.data_lake.name
}

output "raw_dataset_id" {
  description = "원본 적재용 BigQuery 데이터셋 ID"
  value       = google_bigquery_dataset.raw.dataset_id
}

output "ingestion_sa_email" {
  description = "수집 파이프라인 서비스 계정 이메일 (로컬 개발 시 impersonation 대상)"
  value       = google_service_account.ingestion.email
}
