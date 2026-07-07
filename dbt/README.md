# dbt/ — 변환 계층 (Transform)

> **무엇**: BigQuery 안에서 raw → staging → marts 로 데이터를 정제·가공하는 SQL 모델들.
> **왜 dbt**: SELECT문만 쓰면 테이블/뷰 생성·의존성 순서·품질 테스트·문서화를 프레임워크가 처리한다.
> "SQL로 하는 데이터 모델링 + 테스트" — 데이터 엔지니어 JD 단골 항목의 실체.

## 계층 설계

| 계층 | 재료 | 책임 | 실체화 |
|---|---|---|---|
| raw (dbt 밖) | 식약처 API | 원형 보존 (ingestion이 적재) | 파티션 테이블 |
| staging | raw | 최신 스냅샷 선택, 컬럼명/타입 정리, 중복 제거 | 뷰 (저장비용 0) |
| marts (예정) | staging | 추천 로직 — 성분 필터, 피부타입별 집계 | 테이블 (조회 성능) |

## 실행 방법

```bash
# profiles.yml이 저장소 안에 있으므로 --profiles-dir 지정 필요
cd dbt
uv run dbt debug --profiles-dir .    # 연결 확인
uv run dbt run   --profiles-dir .    # 모델 생성/갱신
uv run dbt test  --profiles-dir .    # 품질 테스트
```

> ⚠️ **Windows 주의**: 한국어 Windows는 기본 인코딩이 cp949라서 dbt가 UTF-8 프로젝트 파일을
> 읽다 `UnicodeDecodeError`로 죽는다. 실행 전 `$env:PYTHONUTF8='1'` (파이썬 UTF-8 모드) 필수.

## 규칙

- 원천 테이블은 반드시 `{{ source(...) }}`, 다른 모델은 반드시 `{{ ref(...) }}` 로 참조
  (하드코딩하면 dbt가 의존성 그래프를 못 그린다)
- 테스트는 프로파일링으로 확인한 사실에만 건다 — 근거 없는 unique는 false alarm 공장
- staging은 뷰, marts는 테이블 — 바꾸려면 이유를 PR에 적을 것
