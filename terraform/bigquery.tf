# ─────────────────────────────────────────────────────────────
# 파일: terraform/bigquery.tf
# 역할: 데이터 웨어하우스(BigQuery)의 데이터셋(= 스키마/폴더 개념) 정의
#
# 데이터셋을 계층으로 나누는 이유 (DW 설계의 표준 패턴, dbt와 짝을 이룸):
#   raw     : 원본 그대로 적재 (수집기가 쓰는 영역)
#   staging : 타입 정리/이름 통일 등 1차 정제 (dbt가 생성)
#   marts   : 비즈니스 질문에 답하는 최종 테이블 — 추천 결과 등 (dbt가 생성, API가 읽음)
# 데이터셋(그릇)은 Terraform이, 그 안의 테이블(내용물)은 dbt가 만든다 — 도구별 책임 분리.
# ─────────────────────────────────────────────────────────────

resource "google_bigquery_dataset" "raw" {
  dataset_id = "raw"      # BigQuery에서 테이블 주소는 `프로젝트.데이터셋.테이블` — 그중 가운데 부분
  location   = var.region # GCS 버킷과 같은 리전 (리전이 다르면 GCS→BQ 적재가 아예 실패한다)

  description = "원본 데이터 적재 영역 — 수집 파이프라인만 쓰기 가능, 사람은 읽기만"

  # 테이블 안 파티션의 기본 만료(밀리초). 90일 = raw 보관 정책을 GCS와 일치시킴 (비용 억제)
  default_partition_expiration_ms = 90 * 24 * 60 * 60 * 1000

  # destroy 시 테이블이 있어도 삭제 허용 — force_destroy와 같은 맥락 (실무 프로덕션에선 false)
  delete_contents_on_destroy = true

  labels = var.labels
}

resource "google_bigquery_dataset" "staging" {
  dataset_id  = "staging"
  location    = var.region
  description = "dbt 1차 정제 계층 — raw를 이름/타입 정리한 뷰. 사람이 직접 쿼리하지 않음"

  # staging은 뷰(view) 위주라 저장 비용이 거의 없다 — 파티션 만료 불필요
  delete_contents_on_destroy = true
  labels                     = var.labels
}

resource "google_bigquery_dataset" "marts" {
  dataset_id  = "marts"
  location    = var.region
  description = "비즈니스 마트 계층 — 추천 결과 등 최종 산출물. API/대시보드가 읽는 유일한 영역"

  delete_contents_on_destroy = true
  labels                     = var.labels
}
