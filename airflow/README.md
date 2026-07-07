# airflow/ — 오케스트레이션 계층

> **무엇**: 배치 파이프라인(fetch → load → dbt)을 매일 자동 실행하는 Airflow 구성.
> **왜 Airflow**: 작업 순서 보장 + 실패 재시도 + 실행 이력/로그를 코드(DAG)로 관리 —
> "cron + 셸 스크립트"와의 차이는 실패가 **보이고**(UI), **복구 가능**(태스크 단위 재실행)하다는 것.
> **왜 로컬 Docker**: 관리형(Cloud Composer)은 월 수십만 원 상시 비용 — 크레딧 예산과 불균형 (PLAN.md 6장).

## 구성

| 파일 | 역할 |
|---|---|
| `Dockerfile` | 공식 Airflow 이미지 + 파이프라인 의존성 |
| `docker-compose.yml` | standalone 모드 1컨테이너 (웹UI+스케줄러+SQLite) |
| `dags/beauty_daily.py` | 매일 02:00 KST: 원천 3개 fetch→load → dbt run→test |

> 참고: DAG 그래프는 원천 3개가 병렬이지만, standalone(SQLite)은 **SequentialExecutor**라
> 실제 실행은 순차다. 병렬이 필요해지면 PostgreSQL+LocalExecutor로 전환 — 지금은
> "그래프 설계는 병렬 가능하게, 실행 환경은 최소로"가 의도된 선택.

## 실행

```powershell
cd airflow
docker compose up -d --build      # 첫 실행 (이미지 빌드 포함, 수 분)
# UI: http://localhost:8080  (id: admin / pw: 컨테이너 안 standalone_admin_password.txt)
docker compose exec airflow cat /opt/airflow/standalone_admin_password.txt
docker compose logs -f airflow    # 로그 보기
docker compose down               # 종료 (이력은 컨테이너 삭제 시 소멸 — 학습용이므로 허용)
```

## 인증 설계 (면접 포인트)

컨테이너에 **서비스 계정 키 파일을 만들지 않는다.** 호스트의 ADC(`gcloud auth application-default login` 결과)를
읽기 전용 마운트해서 재사용 — 키 파일 발급은 유출 사고의 최대 원인이므로 피할 수 있으면 피한다.
(클라우드 배포 시에는 워크로드에 서비스 계정을 직접 연결 — 그때도 키 파일은 없다)

## 재시도 전략 (실전에서 배운 값)

- 코드 레벨(datago.py): 2→4→8초 백오프 3회 — **순간적인** 네트워크 흔들림 흡수
- Airflow 레벨(DAG): 5분 간격 3회 — **몇 분짜리** 회선 단절/서버 점검 흡수
- 두 층이 겹쳐서 "짧은 장애는 코드가, 긴 장애는 오케스트레이터가" 나눠 맡는다
