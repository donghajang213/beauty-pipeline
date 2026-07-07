# ─────────────────────────────────────────────────────────────
# 파일: terraform/variables.tf
# 역할: 이 Terraform 코드가 받는 "입력값" 선언 (함수의 매개변수 같은 것)
# 왜: 프로젝트 ID 같은 값을 코드에 하드코딩하면 다른 사람/환경에서 재사용 불가 (RULES.md 3장)
# 실제 값은 terraform.tfvars 에 넣는다 (git에 커밋하지 않음 → terraform.tfvars.example 참고)
# ─────────────────────────────────────────────────────────────

variable "project_id" {
  description = "GCP 프로젝트 ID"
  type        = string # 타입을 강제해서 잘못된 값이 들어오면 plan 단계에서 바로 실패하게 한다
}

variable "region" {
  description = "리소스를 만들 기본 리전 (서울 = asia-northeast3)"
  type        = string
  default     = "asia-northeast3" # default가 있으면 tfvars에서 생략 가능
}

variable "labels" {
  description = "모든 리소스에 붙일 공통 라벨 — 비용 대시보드에서 '이 프로젝트가 쓴 돈'을 필터링하는 용도"
  type        = map(string)
  default = {
    app        = "beauty-pipeline"
    managed_by = "terraform" # 콘솔에서 이 라벨이 없는 리소스 = 손으로 만든 것 = 규칙 위반 탐지
  }
}
