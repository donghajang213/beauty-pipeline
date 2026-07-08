# ─────────────────────────────────────────────────────────────
# 파일: terraform/cloudrun.tf
# 역할: 추천 API의 배포 인프라 — 이미지 저장소(AR) + 전용 SA + Cloud Run 서비스
# 왜 Cloud Run: 요청 없으면 인스턴스 0개 = 비용 0 (스케일 투 제로). GKE는 상시 비용 (PLAN 6장)
#
# 배포 순서 (닭-달걀: 서비스는 이미지가 있어야 생성됨):
#   1) terraform apply -target=google_artifact_registry_repository.images
#   2) docker build/push (api/README.md)
#   3) terraform apply (전체)
# ─────────────────────────────────────────────────────────────

# ── 컨테이너 이미지 저장소 ──
resource "google_artifact_registry_repository" "images" {
  repository_id = "images"
  format        = "DOCKER"
  location      = var.region
  description   = "beauty-pipeline 컨테이너 이미지"
  labels        = var.labels

  # 비용 안전장치: 오래된 이미지 자동 삭제 (태그 무관 최근 5개만 유지)
  cleanup_policies {
    id     = "keep-recent-5"
    action = "KEEP"
    most_recent_versions {
      keep_count = 5
    }
  }
  cleanup_policies {
    id     = "delete-others"
    action = "DELETE"
    condition {
      older_than = "2592000s" # 30일
    }
  }
}

# ── API 전용 서비스 계정: marts 읽기 + 쿼리 실행만 ──
resource "google_service_account" "api" {
  account_id   = "sa-recommendation-api"
  display_name = "Recommendation API (Cloud Run)"
  description  = "marts 조회 전용. raw/staging 접근 불가 — 계층 규칙을 IAM으로도 강제"
}

resource "google_bigquery_dataset_iam_member" "api_reads_marts" {
  dataset_id = google_bigquery_dataset.marts.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "api_runs_jobs" {
  project = var.project_id
  role    = "roles/bigquery.jobUser" # 쿼리 실행 권한 (프로젝트 단위만 가능한 역할)
  member  = "serviceAccount:${google_service_account.api.email}"
}

# ── Cloud Run 서비스 ──
resource "google_cloud_run_v2_service" "api" {
  name     = "recommendation-api"
  location = var.region
  labels   = var.labels

  template {
    service_account = google_service_account.api.email # 키 파일 없이 SA가 직접 붙음

    scaling {
      min_instance_count = 0 # 스케일 투 제로 — 안 쓰면 0원
      max_instance_count = 1 # 비용 안전장치: 폭주해도 1대까지만
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}/recommendation-api:${var.api_image_tag}"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
    }
  }
}

# 공개 데모: 인증 없이 호출 허용 (max 1 인스턴스 + 무료 티어로 비용 위험 제한)
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  name     = google_cloud_run_v2_service.api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "api_url" {
  description = "추천 API 공개 URL"
  value       = google_cloud_run_v2_service.api.uri
}
