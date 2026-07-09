# ─────────────────────────────────────────────────────────────
# 파일: terraform/secrets.tf
# 역할: Secret Manager — 시크릿의 "금고"를 코드로 정의 (RULES.md 4.1)
#
# ⚠️ 핵심 원칙: Terraform은 시크릿의 "그릇(secret)"만 만들고, "값(version)"은 절대 넣지 않는다.
#   값을 TF 코드에 쓰면 → git에 유출 / TF에서 참조만 해도 → state 파일에 평문 저장.
#   값 주입은 gcloud로 수동 1회 (docs/setup/00-bootstrap.md에 기록):
#     gcloud secrets versions add data-go-kr-service-key --data-file=<키 파일>
# ─────────────────────────────────────────────────────────────

resource "google_secret_manager_secret" "data_go_kr_key" {
  secret_id = "data-go-kr-service-key"
  labels    = var.labels

  replication {
    user_managed {
      replicas {
        location = var.region # 데이터와 같은 리전에 단일 복제 (기본 automatic은 멀티리전)
      }
    }
  }
}

# 수집 파이프라인만 이 시크릿을 읽을 수 있다 — 시크릿 단위 최소 권한
resource "google_secret_manager_secret_iam_member" "ingestion_reads_key" {
  secret_id = google_secret_manager_secret.data_go_kr_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ingestion.email}"
}
