"""
파일: ingestion/config.py
역할: 설정/시크릿을 코드와 분리해서 한 곳에서 읽는다.
왜: 인증키를 코드에 하드코딩하면 ① git에 유출 ② 키 교체 시 코드 수정 필요.
    "코드는 공개돼도 안전하고, 값은 환경마다 주입한다"가 12-Factor App 원칙.

시크릿 탐색 순서 (Phase 3에서 Secret Manager 추가):
  1) 환경변수/.env — 로컬 개발의 빠른 경로
  2) Secret Manager — 클라우드 실행 환경의 정석 경로 (SA에 secretAccessor만 있으면 됨)
  이 순서 덕에 로컬은 .env로 간편하게, 배포 환경은 파일 없이 IAM만으로 동작한다.
사용: from ingestion.config import get_settings
"""

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# .env 파일 내용을 OS 환경변수로 로드한다.
# 이미 진짜 환경변수가 있으면 그것이 우선 (배포 환경에선 .env 없이 환경변수/SM으로 주입).
load_dotenv()

# terraform/secrets.tf 에서 만든 시크릿의 "이름" — 값이 아니라 금고 칸의 라벨이다 (B105 오탐)
DATA_GO_KR_SECRET_ID = "data-go-kr-service-key"  # nosec B105


@dataclass(frozen=True)  # frozen=True: 생성 후 값 변경 불가 — 설정이 도중에 바뀌는 버그 예방
class Settings:
    """파이프라인 전역 설정. 필드가 늘어나면 여기에 추가한다."""

    data_go_kr_service_key: str  # 공공데이터포털 인증키 (Decoding 키)
    gcs_raw_bucket: str | None = None  # 데이터 레이크 버킷 이름 (terraform output data_lake_bucket)


def _from_secret_manager(secret_id: str) -> str | None:
    """Secret Manager에서 최신 버전 값을 읽는다. 실패하면 None (호출부가 최종 에러 처리).

    import를 함수 안에서 하는 이유: 로컬 개발(.env 경로)에서는 이 라이브러리가
    없어도/느려도 영향이 없도록 — 실제로 필요할 때만 로드한다.
    """
    try:
        import google.auth
        from google.cloud import secretmanager

        _, project = google.auth.default()
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project}/secrets/{secret_id}/versions/latest"
        value = client.access_secret_version(name=name).payload.data.decode("utf-8")
        logger.info("시크릿 '%s'를 Secret Manager에서 로드", secret_id)
        return value
    except Exception as e:  # 인증 없음/권한 없음/미존재 — 모두 "여기엔 없다"로 취급
        logger.debug("Secret Manager 조회 실패(%s): %s", secret_id, e)
        return None


def get_settings() -> Settings:
    """설정을 조립한다. 필수 값이 어디에도 없으면 즉시 명확한 에러(fail-fast)."""
    key = os.getenv("DATA_GO_KR_SERVICE_KEY") or _from_secret_manager(DATA_GO_KR_SECRET_ID)
    if not key or key == "여기에_디코딩_인증키":
        raise RuntimeError(
            "DATA_GO_KR_SERVICE_KEY를 찾지 못했습니다. "
            "로컬: .env.example을 .env로 복사해 키 입력 / "
            "클라우드: 실행 SA에 secret 'data-go-kr-service-key' 접근 권한 필요"
        )
    return Settings(
        data_go_kr_service_key=key,
        gcs_raw_bucket=os.getenv(
            "GCS_RAW_BUCKET"
        ),  # 없어도 됨 — GCS를 쓰는 코드가 사용 시점에 검증
    )
