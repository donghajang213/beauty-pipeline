"""
파일: ingestion/streaming/event_generator.py
역할: 피부타입별 가상 사용자들의 행동 이벤트(조회/찜/구매/평점)를 만들어 Pub/Sub에 발행.
왜: 실제 기업의 클릭스트림 파이프라인과 동일한 구조를 합법적으로 재현 (ADR 001).
    스키마 정의 역시 ADR 001 결정 1을 따른다.
실행: uv run python -m ingestion.streaming.event_generator --count 300
흐름: 이 스크립트(발행) → Pub/Sub 토픽 → BigQuery 구독(관리형) → raw.events

행동 모델 (합성이지만 '그럴듯한' 분포):
  - 피부타입 분포: 복합성이 가장 흔하고 민감성이 가장 드묾
  - 자기 피부타입 타깃 제품을 볼 확률이 3배 (추천 mart가 이 신호를 찾아내는지 검증하는 장치)
  - 깔때기(funnel): view는 흔하고 purchase는 드묾. rating은 구매의 일부
"""

import argparse
import datetime as dt
import json
import logging
import random
import time
import uuid

from google.cloud import bigquery, pubsub_v1

logger = logging.getLogger(__name__)

TOPIC = "user-events"  # terraform/pubsub.tf 의 토픽 이름

SKIN_TYPE_WEIGHTS = {  # 국내 피부타입 분포를 흉내낸 가중치
    "combination": 0.35,
    "dry": 0.25,
    "oily": 0.20,
    "normal": 0.12,
    "sensitive": 0.08,
}
EVENT_TYPE_WEIGHTS = {"view": 0.65, "like": 0.15, "purchase": 0.12, "rating": 0.08}
AFFINITY_BOOST = 3  # 자기 피부타입 타깃 제품에 대한 선호 배수


def load_catalog(bq: bigquery.Client) -> list[dict]:
    """raw.products의 최신 스냅샷을 읽는다 (generate_catalog.py 선행 필요)."""
    query = f"""
        select product_id, target_skin_type
        from `{bq.project}.raw.products`
        where date(_PARTITIONTIME) = (
            select max(date(_PARTITIONTIME)) from `{bq.project}.raw.products`
        )
    """
    rows = [dict(r) for r in bq.query(query).result()]
    if not rows:
        raise RuntimeError("raw.products가 비어 있음 — generate_catalog를 먼저 실행하세요")
    return rows


def make_users(n: int, rng: random.Random) -> list[dict]:
    """가상 사용자 풀 — user_id와 피부타입만 있으면 충분하다 (이벤트에 비정규화되어 실림)."""
    types, weights = zip(*SKIN_TYPE_WEIGHTS.items(), strict=True)
    return [
        {"user_id": f"u_{i:05d}", "skin_type": rng.choices(types, weights)[0]} for i in range(n)
    ]


def pick_product(user: dict, catalog: list[dict], rng: random.Random) -> dict:
    """자기 피부타입 타깃 제품이 3배 잘 보이는 가중 선택."""
    weights = [
        AFFINITY_BOOST if p["target_skin_type"] in (user["skin_type"], "all") else 1
        for p in catalog
    ]
    return rng.choices(catalog, weights)[0]


def make_event(user: dict, product: dict, session_id: str, rng: random.Random) -> dict:
    """ADR 001 스키마 v1에 맞는 이벤트 한 건."""
    types, weights = zip(*EVENT_TYPE_WEIGHTS.items(), strict=True)
    event_type = rng.choices(types, weights)[0]

    event = {
        "event_id": str(uuid.uuid4()),  # at-least-once 배달 대비 중복 제거 키
        "event_type": event_type,
        "event_ts": dt.datetime.now(dt.UTC).isoformat(),
        "user_id": user["user_id"],
        "skin_type": user["skin_type"],
        "product_id": product["product_id"],
        "session_id": session_id,
        "rating": None,
    }
    if event_type == "rating":
        # 피부타입이 맞는 제품엔 후한 점수 — 추천 mart가 찾아낼 "숨겨진 정답"
        matched = product["target_skin_type"] in (user["skin_type"], "all")
        event["rating"] = rng.choices(
            [5, 4, 3, 2, 1], [5, 4, 2, 1, 1] if matched else [1, 2, 3, 4, 3]
        )[0]
    return event


def main() -> None:
    parser = argparse.ArgumentParser(description="가상 행동 이벤트 → Pub/Sub 발행")
    parser.add_argument("--count", type=int, default=300, help="발행할 이벤트 수")
    parser.add_argument("--users", type=int, default=200, help="가상 사용자 수")
    parser.add_argument("--rate", type=float, default=20.0, help="초당 발행 수 (기본 20/s)")
    parser.add_argument("--seed", type=int, default=None, help="시드 (기본: 매번 다름)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    rng = random.Random(args.seed)

    bq = bigquery.Client()
    catalog = load_catalog(bq)
    users = make_users(args.users, rng)
    logger.info("카탈로그 %d개 / 사용자 %d명 준비", len(catalog), len(users))

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(bq.project, TOPIC)

    futures = []
    for i in range(args.count):
        user = rng.choice(users)
        # 세션 = 사용자의 한 번의 방문. 단순화: 이벤트마다 4개 세션 중 하나에 귀속
        session_id = f"s_{user['user_id']}_{rng.randint(0, 3)}"
        event = make_event(user, pick_product(user, catalog, rng), session_id, rng)

        # publish는 비동기 — future를 모아뒀다가 마지막에 성공 확인 (유실 감지)
        payload = json.dumps(event, ensure_ascii=False).encode("utf-8")
        futures.append(publisher.publish(topic_path, payload))

        if (i + 1) % 100 == 0:
            logger.info("발행 %d / %d", i + 1, args.count)
        time.sleep(1.0 / args.rate)  # 현실적인 유입 속도 흉내 + API 폭주 방지

    # 전부 서버에 접수됐는지 확인 — 실패한 발행이 있으면 여기서 예외가 난다
    for f in futures:
        f.result(timeout=30)
    logger.info("발행 완료: %d건 → %s", len(futures), topic_path)


if __name__ == "__main__":
    main()
