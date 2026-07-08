/*
파일: dbt/models/staging/stg_events.sql
역할: raw.events의 JSON 원문(data 컬럼)을 파싱해 정형 이벤트로 만들고, 중복을 제거.

스트리밍 staging의 2대 책임 (ADR 001):
1. JSON 파싱: BigQuery 구독은 메시지를 원문 그대로 넣는다(원형 보존) — 타입 부여는 여기서.
2. 중복 제거: Pub/Sub는 at-least-once(최소 1회) 배달 — 같은 event_id가 두 번 올 수 있는 게
   정상이므로, event_id 기준으로 1건만 남긴다. 이게 스트리밍의 "exactly-once는 소비자가
   만드는 것"이라는 원칙의 실체다.
*/

with parsed as (
    select
        json_value(data, '$.event_id')   as event_id,
        json_value(data, '$.event_type') as event_type,
        -- 이벤트 발생 시각(event_ts) ≠ 발행/적재 시각(publish_time) — 지연 분석엔 둘 다 필요
        timestamp(json_value(data, '$.event_ts'))        as event_ts,
        json_value(data, '$.user_id')    as user_id,
        json_value(data, '$.skin_type')  as skin_type,
        json_value(data, '$.product_id') as product_id,
        json_value(data, '$.session_id') as session_id,
        safe_cast(json_value(data, '$.rating') as int64) as rating,
        publish_time
    from {{ source('raw', 'events') }}
)

select *
from parsed
where event_id is not null  -- 파싱 불가 메시지는 버린다 (스키마 위반 이벤트)
-- 중복 제거: 같은 event_id가 여러 번 배달됐다면 가장 먼저 적재된 것만
qualify row_number() over (partition by event_id order by publish_time) = 1
