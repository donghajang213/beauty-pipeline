/*
파일: dbt/models/staging/stg_products.sql
역할: raw.products(합성 카탈로그) → 최신 스냅샷 뷰
카탈로그는 이미 우리가 설계한 스키마라 이름 정리가 거의 불필요 — 최신 선택만 한다.
*/

with latest_snapshot as (
    select *
    from {{ source('raw', 'products') }}
    where date(_PARTITIONTIME) = (
        select max(date(_PARTITIONTIME)) from {{ source('raw', 'products') }}
    )
)

select
    product_id,
    product_name,
    category,
    target_skin_type,
    price_krw,
    key_ingredients  -- ARRAY<STRING> — 규제 조인 시 unnest 해서 사용
from latest_snapshot
