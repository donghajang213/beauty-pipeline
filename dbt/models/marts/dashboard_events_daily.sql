/*
파일: dbt/models/marts/dashboard_events_daily.sql
역할: 대시보드(Looker Studio) 전용 일별 이벤트 KPI — 파이프라인의 "심장 박동" 지표.
왜 전용 뷰인가: BI 도구가 raw/staging을 직접 쿼리하게 두면 ① 스캔 비용 통제 불가
  ② 지표 정의가 차트마다 제각각. "지표는 마트에서 한 번만 정의"가 정석.
grain: 날짜 × 이벤트 타입 (1행 = 하루의 한 이벤트 타입 요약)
*/

with events as (
    select * from {{ ref('stg_events') }}
)

select
    date(event_ts)               as event_date,
    event_type,
    count(*)                     as events,
    count(distinct user_id)      as active_users,
    count(distinct product_id)   as touched_products,
    round(avg(rating), 2)        as avg_rating  -- rating 이벤트 외에는 null → 자동 제외
from events
group by event_date, event_type
