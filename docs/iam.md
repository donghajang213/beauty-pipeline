# IAM 권한 대장

> RULES.md 4.2: 서비스 계정별로 부여한 권한과 이유를 기록한다.
> 원칙: 최소 권한 — 프로젝트 레벨 광범위 역할(owner/editor) 금지, 가능한 한 리소스 단위로 부여.

## sa-ingestion (수집 파이프라인)

정의 위치: [terraform/iam.tf](../terraform/iam.tf)

| 역할 | 부여 범위 | 이유 |
|---|---|---|
| `roles/storage.objectAdmin` | `{project}-data-lake` 버킷만 | 원본 데이터 업로드(쓰기)와 재처리 시 읽기. 버킷 설정 변경은 불가 |
| `roles/bigquery.dataEditor` | `raw` 데이터셋만 | 원본 테이블 생성/적재. staging/mart 오염 방지를 위해 데이터셋 단위 |
| `roles/bigquery.jobUser` | 프로젝트 (예외) | load job 실행 권한. 이 역할은 프로젝트 단위로만 부여 가능해 예외 허용 |

## 사람 계정

| 계정 | 역할 | 비고 |
|---|---|---|
| alja4097@gmail.com | 프로젝트 소유자 | 부트스트랩/관리용. 파이프라인 실행에는 사용하지 않는다 |
