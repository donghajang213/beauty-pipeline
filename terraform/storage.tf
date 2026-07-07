# ─────────────────────────────────────────────────────────────
# 파일: terraform/storage.tf
# 역할: 데이터 레이크 (GCS 버킷) — 파이프라인의 "원본 보관소"
#
# 데이터 레이크 개념: API에서 받은 데이터를 가공 없이 원형 그대로(raw) 먼저 저장한다.
# 왜? 가공 로직에 버그가 있어도 원본이 남아있으면 언제든 재처리(backfill)할 수 있다.
# 흐름: 식약처 API → [이 버킷 raw/] → BigQuery → dbt
# ─────────────────────────────────────────────────────────────

# resource "리소스타입" "내부이름" — 내부이름은 Terraform 코드 안에서 부르는 별명 (실제 GCP 이름 아님)
resource "google_storage_bucket" "data_lake" {
  # 버킷 이름은 전 세계에서 유일해야 해서 프로젝트 ID를 접두사로 쓴다
  name     = "${var.project_id}-data-lake"
  location = var.region # 서울 리전 — BigQuery와 같은 리전이어야 적재가 빠르고 리전 간 전송비가 없다

  # 접근 제어를 버킷 단위로 통일 (객체별 ACL 금지). 보안 감사에서 항상 권장되는 설정.
  uniform_bucket_level_access = true

  # 실수로 public 공개되는 것 원천 차단 (DevSecOps 기본기)
  public_access_prevention = "enforced"

  # 비용 안전장치: raw 데이터는 매일 쌓이므로, 오래된 것은 자동 삭제해 저장 비용을 억제
  lifecycle_rule {
    condition {
      age = 90 # 90일 지난 객체는
    }
    action {
      type = "Delete" # 자동 삭제
    }
  }

  # terraform destroy 시 객체가 들어있어도 버킷을 지울 수 있게 허용.
  # ⚠️ 실무 프로덕션에서는 false(기본값)가 맞다 — 여기선 크레딧 종료 시 깔끔한 철거가 더 중요.
  force_destroy = true

  labels = var.labels
}
