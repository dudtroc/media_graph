# ------------------------------------------------------------
# Dockerfile: Media Graph API with Celery, RabbitMQ, Redis
# ------------------------------------------------------------
FROM nvidia/cuda:12.4.0-runtime-ubuntu20.04

# 기본 환경 변수
ENV DEBIAN_FRONTEND=noninteractive
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

USER root

# 패키지 업데이트 및 필수 도구 설치 (Python 3.10 PPA 추가)
RUN apt-get update && apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y \
    bash build-essential git curl wget unzip \
    vim cmake ninja-build pkg-config \
    libgl1 ca-certificates python3.10 python3.10-dev libpython3.10-dev \
    python-is-python3 python3.10-venv python3-pip \
    libsndfile1-dev zlib1g-dev \
    libjpeg-dev libpng-dev libtiff-dev libfreetype6-dev \
    libxft-dev libfftw3-dev libopenblas-dev liblapack-dev \
    gfortran libhdf5-dev pkg-config

# 최신 pip 설치 후 파이썬 패키지 설치
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10 && \
    python3.10 -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

RUN /opt/venv/bin/pip install --upgrade pip
RUN /opt/venv/bin/pip install --no-cache-dir setuptools wheel packaging

# 작업 디렉토리 및 포트
WORKDIR /workspace

# Python 경로 설정
ENV PYTHONPATH="/workspace:/workspace/src"

# 필요한 디렉토리 생성
RUN mkdir -p /workspace/log /workspace/config

# 전체 프로젝트 복사
COPY . /workspace/

# 프로젝트 복사 후 패키지 설치 (마지막에 실행)
RUN /opt/venv/bin/pip install --no-cache-dir -r /workspace/requirements-pytorch.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r /workspace/requirements.txt

EXPOSE 10102
CMD ["bash"]