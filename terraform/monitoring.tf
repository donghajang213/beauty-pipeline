# ─────────────────────────────────────────────────────────────
# 파일: terraform/monitoring.tf
# 역할: "사람보다 먼저 아는" 알림 체계 — 가동 감시(uptime) + 오류율(5xx)
# 원칙: 알림은 "받으면 행동할 것"에만 건다. 소음이 많은 알림은 곧 무시되는 알림이다.
#
# 알림 지도 (전체 감시 체계에서 이 파일의 위치):
#   비용 초과   → 예산 알림 (Phase 0, gcloud로 설정 — 월 ₩216,000 / 25~100%)
#   API 다운    → uptime check (이 파일) — 5분마다 /health 호출
#   API 오류    → 5xx 알림 (이 파일)
#   DAG 실패    → ⚠️ 미구현 한계: Airflow가 로컬 Docker라 Cloud Monitoring이 못 본다.
#                 현재는 Airflow UI에서 확인. 클라우드 이전(Composer/GKE) 시 해결 —
#                 로컬 실행 선택(비용)의 트레이드오프로 문서화 (PLAN 6장)
# ─────────────────────────────────────────────────────────────

# ── 알림 수신 채널: 이메일 ──
resource "google_monitoring_notification_channel" "email" {
  display_name = "운영 알림 (이메일)"
  type         = "email"
  labels = {
    email_address = "alja4097@gmail.com"
  }
}

# ── 가동 감시: 전 세계에서 5분마다 /health 를 호출 ──
resource "google_monitoring_uptime_check_config" "api_health" {
  display_name = "recommendation-api /health"
  timeout      = "10s"
  period       = "300s" # 5분 — 무료 한도 안에서 충분한 주기

  http_check {
    path         = "/health"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      # Cloud Run URL의 호스트 부분 — 서비스 출력값에서 https:// 를 뗀 것
      host = trimprefix(google_cloud_run_v2_service.api.uri, "https://")
    }
  }
}

# ── 알림 1: API가 죽었다 (uptime check 실패) ──
resource "google_monitoring_alert_policy" "api_down" {
  display_name = "[beauty] 추천 API 다운"
  combiner     = "OR"

  conditions {
    display_name = "uptime check 연속 실패"
    condition_threshold {
      # uptime check 결과 지표 — check_passed가 false면 실패
      filter = <<-EOT
        resource.type = "uptime_url"
        AND metric.type = "monitoring.googleapis.com/uptime_check/check_passed"
        AND metric.labels.check_id = "${google_monitoring_uptime_check_config.api_health.uptime_check_id}"
      EOT

      comparison      = "COMPARISON_GT"
      threshold_value = 1      # 실패(=0이 아닌 집계값) 판정용 — 아래 aggregation과 세트
      duration        = "300s" # 5분간 지속되면 알림 (콜드스타트 순간 실패 1번은 무시)

      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_FALSE" # 기간 내 "실패 횟수"를 센다
        group_by_fields      = ["resource.label.host"]
      }
      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  documentation {
    content = "추천 API /health 가 5분 이상 응답하지 않습니다. Cloud Run 콘솔에서 recommendation-api 리비전 로그를 확인하세요."
  }
}

# ── 알림 2: API가 오류를 뱉는다 (5xx 응답 발생) ──
resource "google_monitoring_alert_policy" "api_5xx" {
  display_name = "[beauty] 추천 API 5xx 발생"
  combiner     = "OR"

  conditions {
    display_name = "5xx 응답 발생"
    condition_threshold {
      filter = <<-EOT
        resource.type = "cloud_run_revision"
        AND resource.labels.service_name = "${google_cloud_run_v2_service.api.name}"
        AND metric.type = "run.googleapis.com/request_count"
        AND metric.labels.response_code_class = "5xx"
      EOT

      comparison      = "COMPARISON_GT"
      threshold_value = 0 # 5xx는 정상 상태에서 0이어야 한다 — 1건이라도 나면 알림
      duration        = "0s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  documentation {
    content = "추천 API가 5xx를 반환했습니다. BigQuery 권한/마트 존재 여부, Cloud Run 로그를 확인하세요."
  }
}
