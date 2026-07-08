/*
파일: dbt/models/staging/stg_manufacturer.sql
역할: raw.manufacturer → 제조업체 뷰
하는 일: 이름 정리 + 타입 교정(식별자→문자열, YYYYMMDD→DATE) + 완전 중복 제거
(2026-07-07 프로파일링: 32,318행 중 175건이 전 컬럼 동일한 완전 중복 — 원천 품질 문제)
*/

with latest_snapshot as (
    select *
    from {{ source('raw', 'manufacturer') }}
    where date(_PARTITIONTIME) = (
        select max(date(_PARTITIONTIME)) from {{ source('raw', 'manufacturer') }}
    )
)

select
    -- autodetect가 INT64로 추론했지만 의미상 "식별자"다 (연산 대상 아님) → 문자열로 교정.
    -- 이런 의미 기반 타입 정리가 staging 계층의 존재 이유.
    cast(ENTP_SEQ as string) as company_seq,   -- 업체 일련번호 (유니크 키 → 테스트로 검증)
    ENTP_NAME                as company_name,
    BOSS_NAME                as ceo_name,
    INDUTY                   as industry,      -- 업종 (예: '화장품제조')
    FACTORY_ADDR             as factory_address,
    -- 주의: 사업자등록번호는 앞자리 0이 가능한 식별자 — INT64로 읽힌 순간 이미 소실됐을 수
    -- 있어 10자리로 복원(lpad)한다
    lpad(cast(BIZRNO as string), 10, '0') as business_reg_no,
    -- safe.parse_date: 'YYYYMMDD' → DATE. 형식이 깨진 값은 에러 대신 NULL
    safe.parse_date('%Y%m%d', cast(ENTP_PERMIT_DATE as string)) as permit_date
from latest_snapshot
-- 완전 중복 제거: 모든 컬럼이 같은 행이라 어떤 걸 남겨도 무방
qualify row_number() over (partition by ENTP_SEQ) = 1
