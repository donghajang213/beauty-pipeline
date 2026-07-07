# terraform/ — 인프라 코드 (IaC)

> **무엇**: 이 프로젝트의 모든 GCP 리소스를 정의하는 코드. 콘솔에서 클릭으로 만드는 대신 코드로 선언한다.
> **왜**: ① 재현 가능 — 명령 한 번으로 인프라 전체를 다시 만들 수 있다 ② 리뷰 가능 — 인프라 변경이 PR로 검토된다 ③ 추적 가능 — 누가 언제 무엇을 바꿨는지 git 히스토리에 남는다.

## 파일 구성

| 파일 | 역할 |
|---|---|
| `versions.tf` | Terraform/프로바이더 버전 고정, state 저장 위치(GCS) |
| `variables.tf` | 입력값 선언 (project_id 등) — 하드코딩 방지 |
| `storage.tf` | 데이터 레이크 GCS 버킷 (raw 원본 보관, 90일 수명) |
| `bigquery.tf` | BigQuery `raw` 데이터셋 (DW의 원본 계층) |
| `iam.tf` | 수집용 서비스 계정 + 최소 권한 (버킷/데이터셋 단위) |
| `outputs.tf` | 생성된 리소스 주소 출력 (다른 코드가 참조) |
| `terraform.tfvars.example` | 입력값 예시 — 복사해서 `terraform.tfvars`(비커밋) 생성 |

## 실행 방법

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # project_id 채우기
terraform init      # 프로바이더 다운로드 + GCS backend 연결 (최초 1회)
terraform plan      # "무엇이 생기고/바뀌고/지워지는지" 미리보기 — 반드시 읽고 나서
terraform apply     # 실제 적용
```

## 핵심 개념 요약 (면접 대비)

- **선언형(declarative)**: "버킷을 만들어라"(명령)가 아니라 "버킷이 존재해야 한다"(상태)를 적는다.
  Terraform이 현재 상태와 비교해 필요한 작업만 수행한다 → 몇 번을 실행해도 결과가 같다(멱등성).
- **state**: Terraform의 장부. 실제 클라우드 ↔ 코드 사이의 대조 기준. GCS에 원격 저장 + 버전 관리.
- **plan → apply 분리**: 변경 사항을 사람이 검토한 뒤 적용. CI에서는 PR에 plan 결과를 붙여 리뷰한다.
- **의존성 그래프**: `google_storage_bucket.data_lake.name` 처럼 리소스를 참조하면
  Terraform이 생성 순서(버킷 먼저 → IAM 바인딩 나중)를 자동으로 계산한다.
