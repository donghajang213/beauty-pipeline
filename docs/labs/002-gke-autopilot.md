# 실습 002 — GKE Autopilot에 추천 API 배포 (만들고 → 기록하고 → 지우기)

> **목적**: JD 단골 "Kubernetes 경험"을 실물로 — 같은 컨테이너 이미지를 Cloud Run과
> GKE 양쪽에 배포해 보고, 언제 무엇을 쓰는지 판단 근거를 만든다.
> **원칙**: 실습 종료 즉시 클러스터 삭제 (상시 비용 0 복귀).

## Cloud Run vs GKE — 같은 이미지, 다른 세계

| | Cloud Run (본편) | GKE Autopilot (실습) |
|---|---|---|
| 운영 주체 | 구글이 거의 전부 | 우리가 선언(YAML)으로 제어 |
| 비용 | 요청 없으면 0 | 클러스터가 떠 있는 동안 과금 |
| 쓰는 때 | 단순 HTTP 서빙 (우리 케이스) | 사이드카/배치/내부망/세밀한 제어 |

## 무엇을 했나

1. Autopilot 클러스터 `beauty-lab` 생성 (노드 관리까지 구글에 위임하는 모드)
2. [labs/gke/deployment.yaml](../../labs/gke/deployment.yaml): Deployment(자기치유) + Service(LoadBalancer) + KSA
3. **Workload Identity**: KSA ↔ GCP SA(sa-recommendation-api) 연결 — GKE에서도 키 파일 없이 BigQuery 접근 (Cloud Run·CD와 같은 키리스 원칙의 3번째 적용)
4. 공인 IP로 실제 추천 응답 확인 → 자기치유 실험(Pod 강제 삭제 → 자동 재생성) → 클러스터 삭제

## 실행 기록 (실측, 2026-07-09)

- 클러스터 생성 약 8분 → `kubectl apply` → Pod가 Pending에서 시작 (Autopilot이 요청량에 맞는
  노드를 그 순간 프로비저닝 — "Pod가 오면 노드가 생긴다"가 과금 모델의 핵심)
- 공인 IP(LoadBalancer)로 실제 추천 응답 확인 — Workload Identity로 키 파일 없이 BigQuery 조회
- **자기치유 실험**: `kubectl delete pod` 직후 **7초 만에** 새 Pod 자동 생성 (7z6fz → bv4pc)
- 총 가동 약 30분, 비용: Autopilot 무료 티어(월 1클러스터 관리비 면제) + Pod 0.25vCPU 30분 ≈ **수십 원**
- 철거: 클러스터 삭제 + 실습용 Workload Identity 바인딩 제거 — 상시 리소스 0 복귀

## 배운 것 / 면접 포인트

- 같은 이미지가 그대로 양쪽에 뜬다 — **컨테이너의 이식성이 곧 인프라 선택의 자유**
- liveness(살아있나) vs readiness(트래픽 받을 준비 됐나) 프로브의 역할 차이
- "우리 서비스는 Cloud Run으로 충분한데 왜?" → 세밀한 제어가 필요해지는 시점(사이드카,
  장시간 배치, 내부 서비스망)에 GKE로 — 도구 선택의 근거를 실물로 확인
