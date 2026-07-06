"""
파일: ingestion/config.py
역할: 설정/시크릿을 코드와 분리해서 한 곳에서 읽는다.
왜: 인증키를 코드에 하드코딩하면 ① git에 유출 ② 키 교체 시 코드 수정 필요.
    "코드는 공개돼도 안전하고, 값은 환경마다 주입한다"가 12-Factor App 원칙.
사용: from ingestion.config import get_settings
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# .env 파일 내용을 OS 환경변수로 로드한다.
# 이미 진짜 환경변수가 있으면 그것이 우선 (Cloud Run 배포 시엔 .env 없이 환경변수로 주입).
load_dotenv()


@dataclass(frozen=True)  # frozen=True: 생성 후 값 변경 불가 — 설정이 도중에 바뀌는 버그 예방
class Settings:
    """파이프라인 전역 설정. 필드가 늘어나면 여기에 추가한다."""

    data_go_kr_service_key: str  # 공공데이터포털 인증키 (Decoding 키)


def get_settings() -> Settings:
    """환경변수를 읽어 Settings 객체를 만든다.

    필수 값이 없으면 즉시 명확한 에러로 실패시킨다(fail-fast).
    없는 채로 진행하면 API 호출 단계에서 알 수 없는 인증 오류로 나타나 디버깅이 어렵다.
    """
    key = os.getenv("DATA_GO_KR_SERVICE_KEY")
    if not key or key == "여기에_디코딩_인증키":
        raise RuntimeError(
            "DATA_GO_KR_SERVICE_KEY가 설정되지 않았습니다. "
            ".env.example을 .env로 복사하고 공공데이터포털 인증키를 넣어주세요."
        )
    return Settings(data_go_kr_service_key=key)
