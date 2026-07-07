/*
파일: dbt/models/staging/stg_ingredient.sql
역할: raw.ingredient → 정돈된 성분 사전 뷰
하는 일: ① 최신 스냅샷만 선택 ② 식약처 원어 컬럼명 → 명확한 영문명 ③ 중복 제거
(2026-07-07 프로파일링: 21,833행 중 성분명 중복 1건 발견 → 중복 제거 + unique 테스트로 방어)
*/

with latest_snapshot as (
    -- raw에는 날짜별 스냅샷이 쌓인다 — staging은 항상 "가장 최신 하루치"만 본다
    select *
    from {{ source('raw', 'ingredient') }}
    where date(_PARTITIONTIME) = (
        select max(date(_PARTITIONTIME)) from {{ source('raw', 'ingredient') }}
    )
),

renamed as (
    select
        INGR_KOR_NAME         as ingredient_name_kr,   -- 성분명(한글)
        INGR_ENG_NAME         as ingredient_name_en,   -- 성분명(영문)
        INGR_SYNONYM          as synonyms,             -- 이명(異名) 목록
        CAS_NO                as cas_no,               -- CAS 번호(화학물질 국제 식별자, 없을 수 있음)
        ORIGIN_MAJOR_KOR_NAME as origin_major_kr       -- 주요 기원(식물/광물 등)
    from latest_snapshot
)

select *
from renamed
-- 같은 성분명이 여러 행이면 1행만 남긴다 (qualify = 윈도 함수 결과로 행 필터링하는 BigQuery 문법)
qualify row_number() over (
    partition by ingredient_name_kr
    order by ingredient_name_en nulls last
) = 1
