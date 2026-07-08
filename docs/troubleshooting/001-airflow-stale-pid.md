# 001 — Airflow 웹서버가 조용히 안 뜨는 문제 (stale PID)

## 증상
- `localhost:8080` 연결 거부. 컨테이너는 Up, 스케줄러는 정상 동작 (DAG는 잘 돌아감)
- 로그에 치명적 에러 없이 웹서버 관련 출력만 없음

## 원인
전체 로그를 뒤져보니 한 줄:
```
webserver | Error: Already running on PID 32 (or pid file '/opt/airflow/airflow-webserver.pid' is stale)
```
PC 강제 종료로 웹서버가 **PID 파일을 정리하지 못한 채** 죽었고, 재시작한 웹서버가
그 파일을 보고 "이미 실행 중"으로 판단해 스스로 종료. `docker compose restart`는
컨테이너 파일시스템을 유지하므로 재시작해도 낡은 PID 파일이 계속 남는다.

## 해결
```powershell
docker compose exec airflow rm -f /opt/airflow/airflow-webserver.pid
docker compose restart airflow   # 이후 20초 만에 정상 기동
```

## 배운 점
- "에러 로그가 없다"가 아니라 **"있어야 할 로그(Listening at :8080)가 없다"** 를 찾아야 했다 — 부재도 신호다
- `restart`(FS 유지)와 `down`+`up`(FS 초기화)의 차이. 비정상 종료 뒤에는 잔여 상태(PID, lock)를 의심할 것
- 진단 순서: 컨테이너 상태 → 포트 → 프로세스가 실제로 리슨하는지 → 전체 로그에서 해당 컴포넌트 grep
