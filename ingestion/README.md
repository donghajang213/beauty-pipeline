# ingestion/ — 데이터 수집 계층

> **무엇**: 외부 원천(식약처 공공 API)에서 데이터를 받아오는 코드.
> **왜 분리**: 수집은 "원형 그대로 가져오기"만 책임진다. 정제/변환은 dbt의 일.
> 계층을 섞으면 원천 장애와 변환 버그가 뒤엉켜 디버깅이 불가능해진다 (관심사 분리).

## 파일 구성

| 파일 | 역할 |
|---|---|
| `config.py` | .env/환경변수에서 설정·시크릿 로드 (fail-fast) |
| `datago.py` | 공공데이터포털 공용 클라이언트 — 재시도, 페이지네이션, 오류 통일 |
| `probe.py` | 새 API 탐침 도구 — 인증키/응답 구조를 눈으로 확인 |
| `sources.py` | 원천 레지스트리 — 검증된 API 이름/URL 명세 (여기 추가하면 수집기가 자동 인식) |
| `batch/fetch_to_gcs.py` | 배치 수집기: API → GCS raw (dt= 날짜 파티션, 재실행 멱등) |
| `batch/load_to_bq.py` | GCS raw → BigQuery 날짜 파티션 적재 (load job, 파티션 교체 멱등) |
| `streaming/generate_catalog.py` | 가상 카탈로그 300제품 (실제 성분명 기반, 시드 고정) → raw.products |
| `streaming/event_generator.py` | 피부타입별 가상 행동 이벤트 → Pub/Sub → (BigQuery 구독) → raw.events |

## 처음 실행하기

```bash
uv sync                          # .venv 생성 + 의존성 설치 (uv.lock 기준)
cp .env.example .env             # 인증키 채우기 (커밋 금지!)
uv run pytest                    # 단위 테스트
uv run python -m ingestion.probe --url "https://apis.data.go.kr/1471000/(엔드포인트)" --rows 3
```

## 설계 결정

- **재시도 + 지수 백오프**: 일시적 네트워크 오류는 2→4→8초 대기하며 3회 재시도.
  명백한 거절(잘못된 키 등)은 재시도하지 않는다 — 안 될 일을 반복하면 장애만 키운다.
- **fail-fast 설정 검증**: 인증키가 없으면 API 호출 전에 명확한 메시지로 즉시 실패.
- **응답 껍데기 통일**: 포털 API마다 응답 구조가 조금씩 달라 `_extract_body`에서 흡수한다.
