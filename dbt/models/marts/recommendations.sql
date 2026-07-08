/*
파일: dbt/models/marts/recommendations.sql
역할: 피부타입별 화장품 추천 테이블 — 이 프로젝트의 최종 산출물(추천 API가 읽는 테이블).

추천 공식 (ML 아님 — 설명 가능한 규칙 기반, PLAN 2장):
  score = 조회×1 + 찜×3 + 구매×5 + 평균평점×2
  (행동의 "비용"이 클수록 강한 선호 신호라는 가정. 가중치는 마트 안에서만 바꾸면 됨)

규제 필터 (실제 식약처 데이터가 일하는 부분):
  - 금지 성분 포함 제품 → 전원 제외
  - 사용제한 성분 포함 제품 → 민감성(sensitive) 피부에게만 제외
*/

with events as (
    select * from {{ ref('stg_events') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

-- 제품별 규제 플래그: key_ingredients를 펼쳐 규제 목록과 대조
product_risk as (
    select
        p.product_id,
        logical_or(r.prohibited_in_country is not null) as has_prohibited_ingredient,
        logical_or(r.restricted_in_country is not null) as has_restricted_ingredient
    from products as p
    cross join unnest(p.key_ingredients) as ingredient_name
    inner join {{ ref('stg_regulation') }} as r
        on ingredient_name = r.ingredient_std_name
    group by p.product_id
),

-- 피부타입 × 제품 단위로 행동을 집계해 점수화
scores as (
    select
        skin_type,
        product_id,
        countif(event_type = 'view')     as views,
        countif(event_type = 'like')     as likes,
        countif(event_type = 'purchase') as purchases,
        avg(rating)                      as avg_rating,
        countif(event_type = 'view') * 1
        + countif(event_type = 'like') * 3
        + countif(event_type = 'purchase') * 5
        + coalesce(avg(rating), 0) * 2   as score
    from events
    group by skin_type, product_id
)

select
    s.skin_type,
    s.product_id,
    p.product_name,
    p.category,
    p.target_skin_type,
    p.price_krw,
    s.views,
    s.likes,
    s.purchases,
    round(s.avg_rating, 2) as avg_rating,
    round(s.score, 2)      as score,
    coalesce(risk.has_restricted_ingredient, false) as has_restricted_ingredient,
    -- 피부타입 안에서의 추천 순위 (API는 rank <= N 으로 읽는다)
    row_number() over (partition by s.skin_type order by s.score desc) as rank,
    -- 테스트용 유일 키 (한 피부타입에 같은 제품이 두 줄이면 집계 버그)
    concat(s.skin_type, '|', s.product_id) as rec_key
from scores as s
inner join products as p using (product_id)
left join product_risk as risk using (product_id)
-- 규제 필터: 금지 성분은 전원 제외, 제한 성분은 민감성 피부만 제외
where coalesce(risk.has_prohibited_ingredient, false) = false
  and not (s.skin_type = 'sensitive' and coalesce(risk.has_restricted_ingredient, false))
