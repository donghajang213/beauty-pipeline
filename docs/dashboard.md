# 대시보드 만들기 — Looker Studio 가이드 (10분, 클릭 작업)

> Looker Studio는 코드/Terraform으로 만들 수 없어 이 부분만 직접 클릭이 필요하다.
> 데이터 쪽 준비(dbt 마트)는 끝났으므로 연결과 차트 배치만 하면 된다.

## 데이터 원천 (dbt가 준비해 둔 것)

| 테이블 | 용도 |
|---|---|
| `marts.dashboard_events_daily` | 일별 이벤트 추이 (파이프라인 심장 박동) |
| `marts.recommendations` | 피부타입별 추천 순위 (최종 산출물 전시) |

## 만들기 순서

1. https://lookerstudio.google.com → **만들기 → 보고서**
2. 데이터 연결: **BigQuery** → `beauty-pipeline-499600` → `marts` → `dashboard_events_daily`
3. 추천 차트 4개 (차트 선택 후 오른쪽 "설정" 탭에서):
   - **시계열 차트**: 측정기준 `event_date` / 그 아래 **분류 측정기준** 칸에 `event_type` /
     측정항목 `events` → 이벤트 타입별 색깔 선 4개 = "매일 파이프라인이 살아있다"는 증거
   - **스코어카드 위젯 2개** (스코어카드는 숫자 1개짜리 위젯 — 분류 개념 없음):
     하나는 측정항목 `events`(합계), 다른 하나는 `active_users`(합계)
     ※ active_users 합계 = "일별 고유 사용자의 합" — 여러 날 활동한 사용자는 중복 집계.
       활동 수준 지표로 해석할 것 (전체 고유 사용자 수와 다름을 아는 게 지표 리터러시)
   - **표**: 상단 메뉴 "데이터 추가"로 `marts.recommendations` 연결 → 측정기준 `skin_type`,
     `rank`, `product_name`, 측정항목 `score`, 필터 `rank <= 5` → 최종 산출물 전시
4. 우측 상단 **공유 → 링크 사용 설정** → URL을 README와 포트폴리오_소개에 기록

## 팁

- 새로고침 주기는 기본(12시간)이면 충분 — 일 배치 데이터라 실시간 새로고침은 스캔 비용만 낭비
- 스크린샷 1장을 README에 넣으면 채용담당자가 3초 만에 "돌아가는 프로젝트"임을 인지한다
