<!-- published: (발행 후 URL 기록) -->

# 6만 건 공공데이터를 GCS에서 BigQuery, dbt까지 — 그리고 3번의 인터넷 단절에서 배운 멱등성

## 배경

[지난 글](001 링크로 교체)에서 GCP 인프라(Terraform)와 예산 알림, 그리고 식약처 화장품 API 3종의 수집기를 만들었다. 이번 글은 그 데이터가 **데이터 레이크(GCS) → 데이터 웨어하우스(BigQuery) → 변환 계층(dbt)** 으로 흘러가는 과정이다. 파이프라인으로 치면 ②저장 → ③적재 → ④변환 구간.

## 적재: 스트리밍 인서트 대신 load job을 쓴 이유

GCS의 JSONL을 BigQuery로 넣는 방법은 크게 두 가지다.

| 방법 | 비용 | 우리 상황 |
|---|---|---|
| 스트리밍 인서트 | 유료 (GB당 과금) | 이미 파일이 레이크에 있는데 굳이? |
| **load job** | **무료** | ✅ 채택 |

적재 대상은 `raw.{원천}` 테이블의 **날짜 파티션**이다. 여기서 배운 BigQuery 문법 하나 — 파티션 데코레이터:

```python
# "테이블$YYYYMMDD" = 그 날짜 칸만 지목한다
destination = f"raw.ingredient$20260707"
job_config = bigquery.LoadJobConfig(
    write_disposition="WRITE_TRUNCATE",  # 그 파티션만 통째로 교체
    ...
)
```

`WRITE_TRUNCATE`를 파티션 데코레이터와 함께 쓰면 "오늘 칸만 갈아끼우기"가 된다. 재실행해도 중복이 없고(멱등), 어제까지의 스냅샷 이력은 그대로 남는다.

## 실전 검증: 인터넷이 3번 끊겼다

이번 주 수집 작업 중 집 인터넷이 **세 번** 끊겼다. 한 번은 32,318건 중 31,800건(98%!)을 받은 지점에서, 한 번은 업로드 직전 인증 단계에서.

그런데 복구 작업은 매번 똑같았다: **같은 명령을 다시 실행.** 그게 전부다.

가능했던 이유는 처음부터 넣어둔 두 가지 설계 덕분이다.

1. **전량 수집 후 원자적 업로드**: 수집 도중에는 GCS에 아무것도 쓰지 않는다. 끝까지 받고 나서 한 번에 업로드하므로 "반쯤 쓰인 파일"이 존재할 수 없다.
2. **같은 날짜 = 같은 경로 덮어쓰기**: 몇 번을 다시 돌려도 결과는 하나다.

> 면접에서 "멱등성이 왜 중요한가요?"라고 물으면 이제 이론이 아니라 이 경험으로 답할 수 있다:
> **장애 복구 절차가 '재실행' 한 단어로 줄어든다.**

## 변환: dbt로 staging 계층 만들기

raw 테이블의 컬럼은 `INGR_KOR_NAME` 같은 식약처 원어에 전부 문자열 타입이다. 이대로 분석하면 모든 쿼리에 정제 로직이 반복된다. dbt로 **staging 뷰**를 만들어 한 곳에서 정리했다.

```sql
select
    INGR_KOR_NAME as ingredient_name_kr,
    ...
    -- 'YYYYMMDD' 문자열 → 진짜 DATE (깨진 값은 에러 대신 NULL)
    safe.parse_date('%Y%m%d', ENTP_PERMIT_DATE) as permit_date
from {{ source('raw', 'manufacturer') }}
where date(_PARTITIONTIME) = (select max(date(_PARTITIONTIME)) from ...)
```

### 테스트는 "희망사항"이 아니라 "확인된 사실"에 건다

dbt의 품질 테스트를 걸기 전에 프로파일링부터 했다:

- `ingredient`: 21,833행 중 유니크 성분명 21,832 → **중복 1건 발견**. staging에서 제거하고 `unique` 테스트로 재발 방어.
- `regulation`: 7,257행 중 유니크 성분명 6,924 → 중복이 많다? 데이터를 보니 같은 성분이 **국가별로 한 행씩**("EU에서 금지") 있는 구조. 즉 이 테이블의 행 단위(grain)는 "성분×국가"이고, 여기에 unique를 걸면 정상 데이터가 불량 판정을 받는다.

같은 "중복"이라도 하나는 제거 대상, 하나는 데이터의 의미였다. **테스트 목록보다 프로파일링이 먼저**라는 걸 배웠다.

## 삽질 기록 (Windows 특집)

1. `zoneinfo.ZoneInfoNotFoundError: Asia/Seoul` — Windows에는 IANA 시간대 DB가 없다. `tzdata` 패키지 추가로 해결.
2. dbt가 `UnicodeDecodeError: 'cp949' codec...`으로 사망 — 한국어 Windows 기본 인코딩(cp949)이 UTF-8 프로젝트 파일과 충돌. `PYTHONUTF8=1` 환경변수로 해결.
3. dbt-bigquery 설치 시 의존성 충돌 — 기존 `google-cloud-storage>=3.12` 핀과 dbt의 `<3.2` 요구가 충돌. 하한을 느슨하게 풀고 정확한 버전은 uv.lock에 맡겼다.

## 배운 것

- 멱등성은 이론이 아니라 **장애 복구 비용**의 문제다
- 데이터 품질 테스트는 프로파일링(사실 확인) 다음이다 — grain을 모르고 걸면 false alarm 공장
- 다음 글: Airflow로 fetch → load → dbt를 매일 자동 실행 (Phase 1 완결편)

---
*이 프로젝트의 전체 코드: [GitHub](https://github.com/donghajang213/beauty-pipeline)*
