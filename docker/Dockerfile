# ------------------------------------------------------------
# Dockerfile: FFmpeg 5.1.2 + CUDA + scale_npp + PyNvCodec (VPF) 지원 환경
# ------------------------------------------------------------
FROM nvidia/cuda:12.4.0-devel-ubuntu20.04

# 기본 환경 변수
ENV DEBIAN_FRONTEND=noninteractive
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,video,utility
ENV CMAKE_POLICY_VERSION_MINIMUM=3.5

USER root

# 패키지 업데이트 및 필수 도구 설치 (Python 3.10 PPA 추가)
RUN apt-get update && apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y \
    bash build-essential git curl wget unzip \
    vim cmake ninja-build pkg-config yasm \
    libgl1 ca-certificates python3.10 python3.10-dev libpython3.10-dev \
    python-is-python3 python3.10-venv python3-pip \
    libsndfile1-dev libx264-dev libx265-dev libnuma-dev \
    libvpx-dev libfdk-aac-dev libopus-dev libass-dev \
    libfreetype6-dev libvorbis-dev libxcb1-dev libxcb-shm0-dev \
    libxcb-xfixes0-dev texinfo zlib1g-dev nasm \
    libdrm-dev libva-dev libvdpau-dev libxext-dev libxfixes-dev \
    libavfilter-dev libavformat-dev libavcodec-dev \
    libswresample-dev libavutil-dev

# 최신 pip 설치 후 파이썬 패키지 설치
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10 && \
    python3.10 -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"
ENV PATH="/usr/local/cuda-12.4/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/cuda-12.4/lib64:${LD_LIBRARY_PATH}"

RUN /opt/venv/bin/pip install --upgrade pip
RUN /opt/venv/bin/pip install --no-cache-dir setuptools wheel packaging

# 핵심 의존성 먼저 설치 (torch 등)
RUN /opt/venv/bin/pip install --no-cache-dir \
    torch==2.6.0+cu124 torchvision==0.21.0+cu124 torchaudio==2.6.0+cu124 \
    --index-url https://download.pytorch.org/whl/cu124

# flash-attn을 별도로 설치 (torch 의존성 해결 후)
RUN /opt/venv/bin/pip install --no-cache-dir flash-attn==2.7.4.post1 --find-links https://github.com/Dao-AILab/flash-attention/releases

# requirements.txt 파일을 복사하고 나머지 라이브러리 설치
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

# 라이브러리 경로 설정
ENV LIBRARY_PATH=/usr/local/cuda/lib64/stubs:${LIBRARY_PATH}
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64/stubs:/usr/local/lib:${LD_LIBRARY_PATH}
ENV CUDA_PATH=/usr/local/cuda

# FFmpeg 5.1.2 소스 빌드
RUN mkdir -p /opt/ffmpeg && cd /opt/ffmpeg && \
    git clone -b n5.1.2 https://git.ffmpeg.org/ffmpeg.git ffmpeg && \
    cd ffmpeg && \
    ./configure \
        --prefix=/usr/local \
        --pkg-config-flags="--static" \
        --extra-cflags="-I/usr/local/cuda/include" \
        --extra-ldflags="-L/usr/local/cuda/lib64/stubs -L/usr/local/lib -lnppig -lnppicc -lnppc -lnppidei -lnppif -lnppisu -lnpps" \
        --enable-cuda \
        --enable-cuvid \
        --enable-nvenc \
        --enable-nvdec \
        --enable-libnpp \
        --enable-cuda-nvcc \
        --enable-nonfree \
        --enable-gpl \
        --enable-libx264 \
        --enable-libx265 \
        --enable-libfdk-aac \
        --enable-libvpx \
        --enable-libass \
        --enable-libfreetype \
        --enable-libopus \
        --enable-libvorbis \
        --enable-shared && \
    make -j"$(nproc)" && make install && ldconfig

# 작업 디렉토리 및 포트
WORKDIR /workspace
EXPOSE 10102
CMD ["bash"]