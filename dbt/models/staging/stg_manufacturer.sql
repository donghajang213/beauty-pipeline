/*
파일: dbt/models/staging/stg_manufacturer.sql
역할: raw.manufacturer → 제조업체 뷰
하는 일: 이름 정리 + 문자열 'YYYYMMDD'를 진짜 DATE 타입으로 변환 (타입 정제의 예시)
*/

with latest_snapshot as (
    select *
    from {{ source('raw', 'manufacturer') }}
    where date(_PARTITIONTIME) = (
        select max(date(_PARTITIONTIME)) from {{ source('raw', 'manufacturer') }}
    )
)

select
    ENTP_SEQ     as company_seq,          -- 업체 일련번호 (유니크 키 후보 → 테스트로 검증)
    ENTP_NAME    as company_name,
    BOSS_NAME    as ceo_name,
    INDUTY       as industry,             -- 업종 (예: '화장품제조')
    FACTORY_ADDR as factory_address,
    BIZRNO       as business_reg_no,      -- 사업자등록번호
    -- safe.parse_date: 'YYYYMMDD' 문자열 → DATE. 형식이 깨진 값은 에러 대신 NULL
    -- (raw는 원형 보존, 타입 변환은 staging의 책임 — 이 줄이 그 원칙의 실체)
    safe.parse_date('%Y%m%d', ENTP_PERMIT_DATE) as permit_date
from latest_snapshot
