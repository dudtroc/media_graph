# 미디어 그래프 검색 기능 API

## 업데이트 로그  
| 날짜 | 내용 |
|------|------|
| 2025-01-27 | RabbitMQ + Redis + Celery 기반으로 리팩토링 |
| 2025-08-22 | 최초 업로드 |

---

## 개요
이 프로젝트는 RabbitMQ, Redis, Celery를 사용한 비동기 메시지 큐 시스템으로 미디어 그래프 검색 기능을 제공합니다.

## 아키텍처
- **API Server**: FastAPI 기반 REST API 서버
- **Message Queue**: RabbitMQ를 사용한 메시지 브로커
- **Result Backend**: Redis를 사용한 결과 저장소
- **Task Processing**: Celery 워커를 통한 비동기 작업 처리

## 환경 세팅

### 1. 환경 변수 설정
```bash
cp env.example .env
# .env 파일을 편집하여 API 키와 설정을 입력하세요
```

### 2. Docker 빌드 및 실행

**빌드 방법**:  
```bash
./docker_launch.sh -b
```

**실행 방법**:  
```bash
./docker_launch.sh -r
```

이 명령어는 다음 서비스들을 시작합니다:
- RabbitMQ (포트 5673, 관리 UI: 15673)
- Redis (포트 6380)
- API 서버 (포트 10103)
- Celery 워커

### 3. 서비스 접근
- **API 서버**: http://localhost:10103
- **RabbitMQ 관리 UI**: http://localhost:15673 (admin/admin123)

## API 엔드포인트

### Meta-to-SceneGraph
- `POST /api/v1/meta-to-scenegraph`: 메타데이터를 씬 그래프로 변환
- `GET /api/v1/meta-to-scenegraph/{jobid}`: 작업 상태 조회
- `DELETE /api/v1/meta-to-scenegraph/{jobid}`: 작업 취소

### Retrieval Graph
- `POST /api/v1/retrieve-scenegraph`: 씬 그래프 검색
- `GET /api/v1/retrieve-scenegraph/{jobid}`: 작업 상태 조회
- `DELETE /api/v1/retrieve-scenegraph/{jobid}`: 작업 취소

## 개발 환경에서 실행

### 로컬 개발 (Docker Compose 없이)
1. RabbitMQ와 Redis를 로컬에 설치
2. 환경 변수 설정
3. API 서버 실행:
```bash
python src/run.py
```
4. Celery 워커 실행:
```bash
celery -A src.contents_graph.celery_app worker --loglevel=info
```

## 명령어 및 옵션 설명
**옵션:**  
- --log_lev: 로그파일에 기록되는 로그 수준 설정 (default="INFO")
- --log_file: 로그파일 저장 경로 (default="/workspace/log/media-graph.log")
- --config_file: 설정 파일 경로 (default="/workspace/config/media-graph_config.json")
- --ip: API 서버 IP 주소 설정 (default="0.0.0.0")
- --port: API 서버 포트 번호 (default="10102")
