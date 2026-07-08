"""
파일: tests/test_event_generator.py
역할: 이벤트 생성기의 순수 로직(스키마, 분포 성질)을 GCP 없이 검증.
왜: 발행(Pub/Sub)은 구글 라이브러리 몫 — 우리가 책임지는 "이벤트 모양"과
    "행동 모델의 성질"만 시드 고정 난수로 결정적으로 테스트한다.
"""

import random

from ingestion.streaming.event_generator import make_event, make_users, pick_product
from ingestion.streaming.generate_catalog import build_catalog

REQUIRED_FIELDS = {
    "event_id",
    "event_type",
    "event_ts",
    "user_id",
    "skin_type",
    "product_id",
    "session_id",
    "rating",
}


def test_event_has_schema_v1_fields():
    """ADR 001 스키마 v1의 필드가 전부 있어야 한다 — 필드 누락은 하류(dbt) 파싱 실패."""
    rng = random.Random(1)
    user = {"user_id": "u_00001", "skin_type": "dry"}
    product = {"product_id": "p_0001", "target_skin_type": "dry"}
    event = make_event(user, product, "s_1", rng)
    assert set(event.keys()) == REQUIRED_FIELDS


def test_rating_only_on_rating_events():
    """rating 값은 rating 이벤트에만 존재해야 한다."""
    rng = random.Random(2)
    user = {"user_id": "u_00001", "skin_type": "oily"}
    product = {"product_id": "p_0001", "target_skin_type": "all"}
    for _ in range(200):
        event = make_event(user, product, "s_1", rng)
        if event["event_type"] == "rating":
            assert event["rating"] in {1, 2, 3, 4, 5}
        else:
            assert event["rating"] is None


def test_pick_product_prefers_skin_type_match():
    """자기 피부타입 타깃 제품이 유의미하게 더 자주 선택돼야 한다 (행동 모델의 핵심 성질)."""
    rng = random.Random(3)
    user = {"user_id": "u_00001", "skin_type": "dry"}
    catalog = [
        {"product_id": "match", "target_skin_type": "dry"},
        {"product_id": "other", "target_skin_type": "oily"},
    ]
    picks = [pick_product(user, catalog, rng)["product_id"] for _ in range(1000)]
    # 기대 비율 3:1 — 시드 고정이라 결과는 결정적. 넉넉한 하한(2배)으로 검증
    assert picks.count("match") > picks.count("other") * 2


def test_catalog_is_reproducible_with_seed():
    """같은 시드 = 같은 카탈로그 (멱등 재생성의 근거)."""
    names = [f"성분{i}" for i in range(50)]
    assert build_catalog(names, size=10, seed=42) == build_catalog(names, size=10, seed=42)


def test_users_reproducible_and_sized():
    rng1, rng2 = random.Random(7), random.Random(7)
    assert make_users(5, rng1) == make_users(5, rng2)
    assert len(make_users(5, random.Random(1))) == 5
