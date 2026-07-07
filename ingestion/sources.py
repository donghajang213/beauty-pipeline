"""
파일: ingestion/sources.py
역할: 수집 대상 원천(source)의 명세를 한 곳에 모은 "원천 레지스트리".
왜: URL을 fetch 스크립트에 하드코딩하면 원천이 늘 때마다 코드 수정이 필요하다.
    레지스트리에 항목만 추가하면 수집기가 자동으로 다루게 한다 (설정과 로직의 분리).
    이름(key)은 GCS 경로(raw/{이름}/...)와 BigQuery 테이블 이름으로도 쓰인다.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    name: str  # 영문 스네이크케이스 — GCS 경로/테이블명에 쓰이므로 한글·공백 금지
    url: str  # 오퍼레이션까지 포함한 전체 호출 URL (probe로 검증된 것만 등록)
    description: str  # 사람용 설명


# 2026-07-06 probe로 실호출 검증 완료 (docs/weekly/2026-07-06.md)
SOURCES: dict[str, Source] = {
    "ingredient": Source(
        name="ingredient",
        url=(
            "https://apis.data.go.kr/1471000/"
            "CsmtcsIngdCpntInfoService01/getCsmtcsIngdCpntInfoService01"
        ),
        description="식약처 화장품 원료성분정보 (약 21,833건)",
    ),
    "regulation": Source(
        name="regulation",
        url=(
            "https://apis.data.go.kr/1471000/"
            "CsmtcsReglMaterialInfoService/getCsmtcsReglMaterialInfoService"
        ),
        description="식약처 화장품 규제정보 — 사용제한/금지 원료 (약 7,257건)",
    ),
    "manufacturer": Source(
        name="manufacturer",
        url=("https://apis.data.go.kr/1471000/CsmtcsMfcrtrInfoService01/getCsmtcsMfcrtrInfoList01"),
        description="식약처 화장품 제조업체 정보 (약 32,307건)",
    ),
}
