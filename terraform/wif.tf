# ─────────────────────────────────────────────────────────────
# 파일: terraform/wif.tf
# 역할: GitHub Actions → GCP 키리스 인증 (Workload Identity Federation)
#
# 왜 WIF인가 (면접 단골):
#   구식: 서비스 계정 키(JSON)를 GitHub Secrets에 저장 → 영구 자격증명이라 유출 시 치명적
#   WIF: GitHub가 워크플로마다 발급하는 단기 OIDC 토큰을 GCP가 검증하고,
#        "우리 저장소에서 온 요청"에만 배포용 SA를 잠깐 빌려준다 — 훔칠 키 자체가 없다.
# ─────────────────────────────────────────────────────────────

# ── 신원 풀: 외부 신원(GitHub)을 받아들이는 컨테이너 ──
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions"
}

# ── 공급자: GitHub OIDC 토큰을 어떻게 검증·해석할지 ──
resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub OIDC"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com" # GitHub의 토큰 발급처
  }

  # 토큰의 클레임 → GCP 속성 매핑
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  # ⚠️ 필수 안전장치: 이 조건이 없으면 "아무 GitHub 저장소나" 이 풀을 통과할 수 있다
  attribute_condition = "assertion.repository == \"donghajang213/beauty-pipeline\""
}

# ── 배포 전용 서비스 계정 ──
resource "google_service_account" "deployer" {
  account_id   = "sa-github-deployer"
  display_name = "GitHub Actions Deployer"
  description  = "CD 파이프라인 — 이미지 푸시와 Cloud Run 배포만 가능"
}

# 우리 저장소의 워크플로가 deployer SA를 "빌려 쓸" 수 있게 허용
resource "google_service_account_iam_member" "github_impersonates_deployer" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/donghajang213/beauty-pipeline"
}

# ── deployer의 권한: 딱 배포에 필요한 3가지 ──
# 1) 이미지 푸시 — images 저장소에만
resource "google_artifact_registry_repository_iam_member" "deployer_pushes_images" {
  repository = google_artifact_registry_repository.images.name
  location   = var.region
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deployer.email}"
}

# 2) Cloud Run 서비스 갱신 — recommendation-api 서비스에만
resource "google_cloud_run_v2_service_iam_member" "deployer_updates_api" {
  name     = google_cloud_run_v2_service.api.name
  location = var.region
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.deployer.email}"
}

# 3) 배포 시 API 런타임 SA를 서비스에 붙일 권한 (actAs)
resource "google_service_account_iam_member" "deployer_acts_as_api_sa" {
  service_account_id = google_service_account.api.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}

output "wif_provider" {
  description = "GitHub Actions 워크플로의 workload_identity_provider 값"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deployer_sa_email" {
  value = google_service_account.deployer.email
}
