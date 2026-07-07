/*
파일: dbt/models/staging/stg_regulation.sql
역할: raw.regulation → 성분×국가 규제 뷰
행의 의미(grain): "성분 하나 × 국가/규제 하나" — 같은 성분이 여러 행일 수 있음(정상).
  (2026-07-07 프로파일링: 7,257행 / 유니크 성분명 6,924 → 이름에 unique 테스트를 걸면 안 됨)
추천 로직에서의 쓰임: "이 성분이 들어간 제품은 민감성 피부에 주의" 같은 필터의 원천.
*/

with latest_snapshot as (
    select *
    from {{ source('raw', 'regulation') }}
    where date(_PARTITIONTIME) = (
        select max(date(_PARTITIONTIME)) from {{ source('raw', 'regulation') }}
    )
)

select
    INGR_STD_NAME  as ingredient_std_name,        -- 표준 성분명 (stg_ingredient와 조인 키 후보)
    INGR_ENG_NAME  as ingredient_name_en,
    PROH_NATIONAL  as prohibited_in_country,      -- 이 국가에서 사용 금지 (예: 'EU')
    LIMIT_NATIONAL as restricted_in_country,      -- 이 국가에서 사용 제한
    -- 파생 컬럼: 금지가 하나라도 있으면 true — 마트에서 반복 계산하지 않도록 여기서 한 번만
    (PROH_NATIONAL is not null) as is_prohibited_anywhere
from latest_snapshot
