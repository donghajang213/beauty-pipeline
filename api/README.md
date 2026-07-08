# api/ — 추천 서빙 계층 (FastAPI + Cloud Run)

> **무엇**: 파이프라인의 최종 산출물(marts.recommendations)을 REST API로 제공.
> **공개 URL**: https://recommendation-api-bfvsee2ydq-du.a.run.app (스케일 투 제로 — 첫 호출은 콜드스타트로 수 초)
> **왜 계산하지 않는가**: 추천 계산은 dbt가 미리 해뒀다(사전 계산 패턴). API는 읽기만 —
> 응답이 빠르고, 장애 지점이 적고, 권한도 marts 조회로 좁힐 수 있다.

## 엔드포인트

| 경로 | 설명 |
|---|---|
| `GET /health` | 생존 확인 (외부 의존성 없음) |
| `GET /recommendations/{skin_type}?limit=10` | 피부타입별 추천 상위 N (skin_type: dry/oily/combination/sensitive/normal) |
| `GET /docs` | 자동 생성 Swagger 문서 |

```bash
curl "https://recommendation-api-bfvsee2ydq-du.a.run.app/recommendations/dry?limit=3"
```

## 로컬 실행 / 테스트

```bash
uv run uvicorn api.main:app --reload --port 8000   # ADC로 BigQuery 인증
uv run pytest tests/test_api.py                     # BigQuery는 mock
```

## 배포 (이미지 갱신 시)

```bash
docker build -t asia-northeast3-docker.pkg.dev/beauty-pipeline-499600/images/recommendation-api:<태그> -f api/Dockerfile .
docker push  asia-northeast3-docker.pkg.dev/beauty-pipeline-499600/images/recommendation-api:<태그>
# terraform/variables.tf 의 api_image_tag 를 <태그>로 바꾸고 terraform apply
```

## 보안/비용 설계

- 전용 SA(`sa-recommendation-api`): **marts 조회 + 쿼리 실행만** — raw/staging은 IAM 차원에서 접근 불가
- 입력 검증: 피부타입은 Enum(5개 값), 나머지는 파라미터 바인딩 — SQL 인젝션 차단
- 공개(allUsers) 노출의 비용 안전장치: 최대 인스턴스 1 + 극소 스캔량 + 예산 알림
- 컨테이너는 non-root 실행, 시크릿 미포함 (인증은 Cloud Run이 SA로 처리 — 키 파일 없음)
