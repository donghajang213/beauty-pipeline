"""
파일: ingestion/datago.py
역할: 공공데이터포털(data.go.kr) API 공용 클라이언트.
왜: 승인받은 API가 여러 개라도 호출 방식(인증키, 페이지네이션, 오류 형식)은 동일하다.
    API마다 requests 코드를 복붙하는 대신, 공통 로직(재시도/오류 처리)을 한 곳에 모은다.
    → 실무에서 말하는 "원천별 커넥터" 패턴의 최소 버전.
사용:
    client = DataGoKrClient(service_key)
    rows = client.fetch_all("https://apis.data.go.kr/1471000/...", page_size=100)
"""

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

# 재시도 정책: 네트워크는 "가끔 실패하는 게 정상"이므로 일시 오류는 재시도한다.
# 단, 무한 재시도는 장애를 키우므로 횟수 제한 + 점점 길게 대기(지수 백오프).
MAX_RETRIES = 3
BACKOFF_SECONDS = 2  # 1회차 2초 → 2회차 4초 → 3회차 8초


class DataGoKrError(Exception):
    """공공데이터포털 API가 오류를 반환했을 때 던지는 예외.

    전용 예외를 만드는 이유: 호출하는 쪽에서 '네트워크 문제'와
    'API가 거절함(키 만료 등)'을 구분해 다르게 대응할 수 있다.
    """


class DataGoKrClient:
    def __init__(self, service_key: str, timeout: int = 30):
        self.service_key = service_key
        # timeout: 응답을 이 시간(초) 이상 기다리지 않음 — 파이프라인 무한 대기 방지
        self.timeout = timeout
        # Session: 같은 서버에 여러 번 요청할 때 연결을 재사용해 빠르다
        self.session = requests.Session()

    def get_page(self, url: str, page_no: int, page_size: int, **extra_params: Any) -> dict:
        """한 페이지를 호출해 파싱된 dict를 돌려준다."""
        # 포털 공통 파라미터: serviceKey(인증), pageNo/numOfRows(페이지), type(형식)
        params = {
            "serviceKey": self.service_key,
            "pageNo": page_no,
            "numOfRows": page_size,
            "type": "json",
            **extra_params,  # API별 추가 검색 조건이 있으면 여기로
        }

        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                # 5xx = 서버 쪽 일시 장애일 가능성 → 재시도 대상
                if resp.status_code >= 500:
                    raise requests.HTTPError(f"서버 오류 {resp.status_code}")
                resp.raise_for_status()  # 4xx 등 나머지 HTTP 오류는 예외로

                # 주의: 포털은 인증 실패 시 type=json을 무시하고 XML 오류를 주기도 한다.
                # 그래서 JSON 파싱 실패를 "인증/등록 문제"의 신호로 처리한다.
                try:
                    return resp.json()
                except ValueError as e:
                    raise DataGoKrError(
                        f"JSON이 아닌 응답 (인증키 오류/미승인 API 가능성): {resp.text[:300]}"
                    ) from e

            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
                # 일시적일 수 있는 오류만 재시도. DataGoKrError(명백한 거절)는 재시도 안 함.
                last_error = e
                wait = BACKOFF_SECONDS**attempt
                logger.warning(
                    "호출 실패 (%d/%d회): %s — %d초 후 재시도", attempt, MAX_RETRIES, e, wait
                )
                time.sleep(wait)

        raise DataGoKrError(f"{MAX_RETRIES}회 재시도 후에도 실패: {last_error}")

    def fetch_all(self, url: str, page_size: int = 100, **extra_params: Any) -> list[dict]:
        """전체 페이지를 순회하며 모든 행(row)을 모아 돌려준다.

        페이지네이션 개념: API는 데이터를 한 번에 다 주지 않고 page 단위로 쪼개 준다.
        totalCount(전체 건수)에 도달할 때까지 pageNo를 올려가며 호출한다.
        """
        rows: list[dict] = []
        page_no = 1
        while True:
            data = self.get_page(url, page_no=page_no, page_size=page_size, **extra_params)
            body = _extract_body(data)

            items = body.get("items") or []
            # 어떤 API는 items가 {"item": [...]} 로 한 겹 더 싸여 온다 — 둘 다 대응
            if isinstance(items, dict):
                items = items.get("item") or []
            rows.extend(items)

            total = int(body.get("totalCount", 0))
            logger.info("page %d 수집: 누적 %d / 전체 %d건", page_no, len(rows), total)

            # 종료 조건: 전부 모았거나, 서버가 빈 페이지를 주면 멈춘다 (무한 루프 방지)
            if len(rows) >= total or not items:
                return rows
            page_no += 1


def _extract_body(data: dict) -> dict:
    """API마다 응답 껍데기가 달라서({"response": {...}} 유무 등) body를 찾아 통일한다."""
    if "response" in data:  # 구형 스타일: response > (header, body)
        resp = data["response"]
        _raise_if_error(resp.get("header", {}))
        return resp.get("body", {})
    if "header" in data:  # 식약처 스타일: header, body가 최상위
        _raise_if_error(data["header"])
        return data.get("body", {})
    return data  # 그 외 — 원형 반환 (probe로 구조 확인 후 분기 추가)


def _raise_if_error(header: dict) -> None:
    """공공데이터포털 공통 결과코드 검사. '00'만 정상이다."""
    code = str(header.get("resultCode", "00"))
    if code not in ("00", "0"):
        raise DataGoKrError(f"API 오류 코드 {code}: {header.get('resultMsg', '메시지 없음')}")
