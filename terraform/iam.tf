# ─────────────────────────────────────────────────────────────
# 파일: terraform/iam.tf
# 역할: 서비스 계정(Service Account)과 최소 권한 부여 (RULES.md 4.2)
#
# 서비스 계정 = "사람이 아닌 프로그램용 계정".
# 수집 파이프라인이 내 개인 계정(owner 권한)으로 돌면, 코드에 버그/침해가 생겼을 때
# 프로젝트 전체가 위험해진다 → 파이프라인엔 "딱 필요한 권한만 가진 로봇 계정"을 준다.
# 부여한 권한과 이유는 docs/iam.md 에도 기록한다.
# ─────────────────────────────────────────────────────────────

# ── 수집(ingestion)용 서비스 계정 ──
resource "google_service_account" "ingestion" {
  account_id   = "sa-ingestion" # 이메일 앞부분이 됨: sa-ingestion@{project}.iam.gserviceaccount.com
  display_name = "Data Ingestion Pipeline"
  description  = "식약처 API 수집 → GCS 저장 → BigQuery 적재. 이 경로에 필요한 권한만 보유"
}

# ── 권한 1: 데이터 레이크 버킷에 객체 쓰기/읽기 ──
# 주의: 프로젝트 전체가 아니라 "이 버킷 하나"에만 권한을 준다 (최소 권한의 핵심).
# roles/storage.objectAdmin = 객체 생성/읽기/삭제 가능. 버킷 설정 변경은 불가.
resource "google_storage_bucket_iam_member" "ingestion_writes_lake" {
  bucket = google_storage_bucket.data_lake.name # 다른 리소스 참조 → Terraform이 생성 순서를 자동 계산
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ingestion.email}"
}

# ── 권한 2: raw 데이터셋에 테이블 생성/데이터 적재 ──
# 데이터셋 단위 권한 — staging/mart 데이터셋에는 손댈 수 없다 (수집기가 가공 영역을 오염시키는 것 방지)
resource "google_bigquery_dataset_iam_member" "ingestion_edits_raw" {
  dataset_id = google_bigquery_dataset.raw.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ingestion.email}"
}

# ── 권한 3: BigQuery 작업(job) 실행 ──
# dataEditor는 "데이터를 담을 권한"일 뿐, 적재 작업(load job) 실행 권한은 별도다.
# jobUser는 프로젝트 단위로만 부여 가능한 역할이라 예외적으로 project 레벨에 부여.
resource "google_project_iam_member" "ingestion_runs_jobs" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}
