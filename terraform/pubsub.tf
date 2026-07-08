# ─────────────────────────────────────────────────────────────
# 파일: terraform/pubsub.tf
# 역할: 사용자 행동 이벤트 스트리밍 경로 — 토픽 → BigQuery 구독 → raw.events
# 설계 근거: docs/adr/001-event-pipeline.md (Dataflow 대신 BigQuery 구독)
#
# Pub/Sub 개념 요약:
#   토픽(topic)   = 이벤트가 발행되는 우체통
#   구독(subscription) = 우체통을 구독하는 수신자. 하나의 토픽에 여러 구독 가능
#   BigQuery 구독 = 수신자가 사람/서버가 아니라 "BigQuery 테이블"인 관리형 구독
# ─────────────────────────────────────────────────────────────

# 프로젝트 번호 조회용 (Pub/Sub 서비스 에이전트 이메일에 필요)
data "google_project" "this" {}

# ── 이벤트 토픽 ──
resource "google_pubsub_topic" "user_events" {
  name   = "user-events"
  labels = var.labels

  # 발행된 메시지를 구독이 없어도 1일간 보관 (구독 장애 시 유실 방지)
  message_retention_duration = "86400s"
}

# ── 이벤트가 도착할 raw 테이블 ──
# BigQuery 구독의 규약 컬럼: data(메시지 본문), 메타데이터(write_metadata=true 시)
resource "google_bigquery_table" "events" {
  dataset_id          = google_bigquery_dataset.raw.dataset_id
  table_id            = "events"
  deletion_protection = false # 학습용 — 프로덕션이면 true

  # 발행 시각 기준 일 파티션 — dbt가 "오늘 이벤트만" 싸게 읽는 기반
  time_partitioning {
    type  = "DAY"
    field = "publish_time"
  }

  schema = jsonencode([
    { name = "subscription_name", type = "STRING", mode = "NULLABLE" },
    { name = "message_id", type = "STRING", mode = "NULLABLE" },
    { name = "publish_time", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "data", type = "STRING", mode = "NULLABLE" }, # 이벤트 JSON 원문 — 파싱은 dbt가
    { name = "attributes", type = "STRING", mode = "NULLABLE" },
  ])

  labels = var.labels
}

# ── Pub/Sub 서비스 에이전트에게 테이블 쓰기 권한 ──
# BigQuery 구독은 "구글이 관리하는 Pub/Sub 로봇 계정"이 우리 테이블에 쓰는 방식이다.
resource "google_bigquery_dataset_iam_member" "pubsub_writes_raw" {
  dataset_id = google_bigquery_dataset.raw.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# ── BigQuery 구독 ──
resource "google_pubsub_subscription" "events_to_bq" {
  name   = "user-events-to-bq"
  topic  = google_pubsub_topic.user_events.id
  labels = var.labels

  bigquery_config {
    table          = "${var.project_id}.${google_bigquery_dataset.raw.dataset_id}.${google_bigquery_table.events.table_id}"
    write_metadata = true # message_id, publish_time 등 메타데이터 컬럼 채움
  }

  # 권한이 먼저 있어야 구독 생성이 성공한다 (생성 시 쓰기 검증을 함)
  depends_on = [google_bigquery_dataset_iam_member.pubsub_writes_raw]
}

# ── 이벤트 생성기용 서비스 계정: 이 토픽에 발행만 가능 ──
resource "google_service_account" "event_generator" {
  account_id   = "sa-event-generator"
  display_name = "Synthetic Event Generator"
  description  = "가상 사용자 행동 이벤트를 user-events 토픽에 발행. 발행 권한만 보유"
}

resource "google_pubsub_topic_iam_member" "generator_publishes" {
  topic  = google_pubsub_topic.user_events.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.event_generator.email}"
}
