"""
파일: ingestion/probe.py
역할: 승인받은 API가 실제로 호출되는지 "탐침(probe)" 검사하는 일회성 도구.
왜: 본 파이프라인을 만들기 전에 ① 인증키가 유효한지 ② 응답 구조(컬럼)가 어떤지 눈으로
    확인해야 한다. 실무에서도 새 원천을 붙일 땐 항상 이런 스파이크(spike) 검증을 먼저 한다.
사용:
    uv run python -m ingestion.probe --url "https://apis.data.go.kr/1471000/..." --rows 3
"""

import argparse
import json
import logging

from ingestion.config import get_settings
from ingestion.datago import DataGoKrClient


def main() -> None:
    # argparse: 스크립트를 CLI 도구로 만든다 — 값을 코드 수정 없이 인자로 바꿔가며 실험 가능
    parser = argparse.ArgumentParser(description="공공데이터포털 API 탐침 검사")
    parser.add_argument("--url", required=True, help="호출할 API 엔드포인트 URL")
    parser.add_argument("--rows", type=int, default=3, help="미리 볼 행 수 (기본 3)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    settings = get_settings()  # .env에서 인증키 로드 (없으면 여기서 친절한 에러)
    client = DataGoKrClient(settings.data_go_kr_service_key)

    # 첫 페이지만 소량 호출 — 탐침 단계에서 전체를 받을 이유가 없다
    data = client.get_page(args.url, page_no=1, page_size=args.rows)

    # ensure_ascii=False: 한글이 이 같은 코드로 깨져 보이지 않게
    print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])


if __name__ == "__main__":
    main()
