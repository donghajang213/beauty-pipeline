# ─────────────────────────────────────────────────────────────
# 파일: terraform/versions.tf
# 역할: Terraform 자체의 설정 — 버전 고정, state 저장 위치, 사용할 프로바이더 선언
# 이 파일이 없으면: 팀원마다 다른 버전을 써서 "내 컴퓨터에선 됐는데" 문제가 생긴다
# ─────────────────────────────────────────────────────────────

terraform {
  # Terraform 최소 버전. 팀 전체가 같은 동작을 보장받기 위해 고정한다.
  required_version = ">= 1.9"

  # ── state(상태 파일) 저장 위치 ──
  # state = "Terraform이 만든 리소스 목록/속성" 기록. 이게 곧 인프라의 장부다.
  # 로컬에 두면 PC 포맷 = 장부 유실, 팀 협업 불가 → 원격(GCS)에 둔다.
  # 이 버킷만은 Terraform이 스스로 만들 수 없어 gcloud로 수동 생성했다. (docs/setup/00-bootstrap.md)
  backend "gcs" {
    bucket = "beauty-pipeline-499600-tfstate" # state를 담을 버킷 (버전 관리 활성화됨)
    prefix = "core"                           # 버킷 안의 폴더 — 나중에 환경(dev/prod) 분리 시 prefix로 구분
  }

  # ── 프로바이더(provider) 선언 ──
  # 프로바이더 = Terraform과 클라우드 API 사이의 번역기.
  # "google" 프로바이더가 있어야 GCS 버킷, BigQuery 등 GCP 리소스 타입을 쓸 수 있다.
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0" # ~> 6.0 = "6.x는 허용, 7.0은 금지" — 메이저 업그레이드로 인한 파괴적 변경 방지
    }
  }
}

# 프로바이더 기본값 설정: 아래 리소스들에서 project/region을 매번 안 적어도 되게 한다.
provider "google" {
  project = var.project_id # variables.tf 에서 선언, terraform.tfvars 에서 값 주입
  region  = var.region
}
