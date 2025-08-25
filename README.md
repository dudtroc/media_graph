# 미디어 콘텐츠 선정성, 폭력성 검출 기능 API

## 업데이트 로그  
| 날짜 | 내용 |
|------|------|
| 2025-06-17 | 최초 업로드 |

---

## 환경 세팅
### Docker 빌드 및 실행 
**주의 사항**  <br>
베이스 이미지는 `nvidia/cuda:12.4.0-runtime-ubuntu20.04` 이미지 사용 (변경 가능)  <br>
- 수정 경로: `docker/Dockerfile`  

실행 전에 docker_launch.sh 파일 내부에서 입력, 출력 폴더 경로 연결부분 본인 PC에 맞게 수정 필요  <br>
- 수정 위치: 38 line `-v /media/ktva/DATA10TB/kt_benchmark:/workspace/data`


1. **빌드 방법**:  
```bash
   ./docker_launch.sh -b
```

2. **실행 방법**:  
```bash
   ./docker_launch.sh -r
```

## 실행 방법  

```bash
python run.py [options]
```

## 명령어 및 옵션 설명
**옵션:**  
- --log_lev: 로그파일에 기록되는 로그 수준 설정 (default="INFO", help="NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL")
- --log_file: 로그파일 저장 경로 (default="/workspace/log/media-guard.log")
- --config_file: 검출 모델 파라미터 설정 파일 경로 (default="/workspace/config/media-guard_config.json)
- --ip: API 서버 IP 주소 설정 (default="0.0.0.0")
- --port: API 서버 포트 번호 (default="10102")
