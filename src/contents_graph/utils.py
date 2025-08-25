import os
import json
import cv2
import time

import logger_init
from collections import Counter
from typing import List, Dict
from skimage.metrics import structural_similarity as ssim

# Reading json config file
def read_config(config_file):
    logger = logger_init.get_logger()
    try:
        with open(config_file) as f:
            server_config = json.load(f)
    except IOError:
        logger.error("Error reading the configuration file.")
        exit(1)

    return server_config

def get_files(directory, extensions=None):

    dest_files = []
    for root, _, files in os.walk(directory): 
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                dest_files.append(os.path.join(root, file))
    
    return dest_files

def get_video_info(video_path: str):
    # VideoCapture 객체 생성
    logger = logger_init.get_logger()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.info("동영상을 열 수 없습니다: {}".format(video_path))
        return None
    else:
        # FPS 정보 가져오기
        fps = cap.get(cv2.CAP_PROP_FPS)
        logger.debug(f"FPS: {fps}")

        # 총 프레임 수 가져오기
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        # 동영상 길이 계산 (초 단위)
        duration = frame_count / fps if fps > 0 else 0
        logger.debug(f"총 프레임 수: {frame_count}")
        logger.debug(f"동영상 길이: {duration:.2f}초")

        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        return  {"fps": fps,
                "total_frame_num": frame_count,
                "duration": duration,
                "frame_width": frame_width,
                "frame_height": frame_height
                }
    
def frame_to_time_string(frame_number, fps):
    # 초 단위로 변환
    total_seconds = frame_number / fps
    
    # 시간, 분, 초, 밀리초 계산
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int((total_seconds - int(total_seconds)) * 10)  # 1초를 10단위로 분할
    
    # 형식에 맞게 문자열 생성
    time_string = f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds}"
    
    return time_string

def sample_video_frames(video_path, start_frame, end_frame, fps, output_dir):
    """
    주어진 비디오 구간에서 지정한 FPS로 프레임을 샘플링하여 이미지로 저장합니다.

    Args:
        video_path (str): 비디오 파일 경로
        start_frame (int): 시작 프레임 번호
        end_frame (int): 끝 프레임 번호
        fps (float): 초당 추출할 프레임 수
        output_dir (str): 저장할 디렉토리 경로

    Returns:
        List[str]: 저장된 이미지 경로 리스트
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if start_frame < 0 or end_frame >= total_frames or start_frame >= end_frame:
        raise ValueError("Invalid start or end frame number")

    os.makedirs(output_dir, exist_ok=True)

    interval = int(video_fps / fps) if fps < video_fps else 1  # 프레임 건너뛰기 간격
    sampled_images = []
    frame_index = start_frame

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    time.sleep(0.001)  # 비디오 파일이 열릴 때까지 대기

    while frame_index <= end_frame:
        ret, frame = cap.read()
        if not ret:
            break

        if (frame_index - start_frame) % interval == 0:
            filename = f"frame_{frame_index:06d}.jpg"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, frame)
            sampled_images.append((frame_index, filepath))

        frame_index += 1

    cap.release()
    return sampled_images

def summarize_shot_assessment(json_list: List[Dict]) -> Dict:
    if not json_list:
        return None  # 비어있는 경우 처리

    unsafe_list = [(i, j) for i, j in enumerate(json_list) if j["rating"] == "Unsafe"]
    safe_list = [(i, j) for i, j in enumerate(json_list) if j["rating"] == "Safe"]

    # 1. Unsafe가 1개만 있는 경우
    if len(unsafe_list) == 1:
        idx, result = unsafe_list[0]
        return {
            "result": result
        }

    # 2. Unsafe가 여러 개 있는 경우 → category voting + 첫 번째 기준
    if len(unsafe_list) > 1:
        category_votes = Counter(j["category"] for _, j in unsafe_list)
        top_category, count = category_votes.most_common(1)[0]
        # 동률이면 순서대로 첫 번째 매칭되는 것 사용
        for idx, item in unsafe_list:
            if item["category"] == top_category:
                return {
                    "result": {
                        "frame_number": item["frame_number"],
                        "rating": "Unsafe",
                        "category": top_category,
                        "rationale": item["rationale"]
                    }
                }

    # Unsafe 없음 = 모두 Safe
    safe_non_na = [(i, j) for i, j in safe_list if j["category"] != "NA: None applying"]

    # 3. Safe만 있고 NA 제외하고 category voting
    if safe_non_na:
        category_votes = Counter(j["category"] for _, j in safe_non_na)
        top_category, count = category_votes.most_common(1)[0]
        for idx, item in safe_non_na:
            if item["category"] == top_category:
                return {
                    "result": {
                        "frame_number": item["frame_number"],
                        "rating": "Safe",
                        "category": top_category,
                        "rationale": item["rationale"]
                    }
                }

    # 4. 모두 Safe이고, 모두 NA인 경우 → 첫 NA 사용
    idx, result = safe_list[0]
    return {
        "result": result
    }   


def load_config(config_path: str) -> dict:
    """
    Loads the configuration from a JSON file.
    :param config_path: Path to the JSON configuration file.
    :return: Configuration as a dictionary.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            config = json.load(config_file)
            print(f"Configuration loaded successfully from {config_path}")
            return config
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON from {config_path}: {e}")
    

def compute_ssim_diff(f1, f2):
    f1_gray = cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY)
    f2_gray = cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY)
    score, _ = ssim(f1_gray, f2_gray, full=True)
    return 1 - score  # 변화량 = 1 - 유사도

def extract_keyframes_ssim(video_path, shot_ranges, output_dir,
                           ssim_threshold=0.05, min_frame_gap=10, max_frames_per_shot=5):
    cap = cv2.VideoCapture(video_path)
    os.makedirs(output_dir, exist_ok=True)

    sampled_images = []

    for idx, (start_frame, end_frame) in enumerate(shot_ranges):
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        last_saved_frame = None
        keyframes = []
        prev_frame = None
        frame_indices = []

        for f in range(start_frame, end_frame):
            ret, frame = cap.read()
            if not ret:
                break

            if prev_frame is None:
                prev_frame = frame
                frame_indices.append(f)
                keyframes.append(frame)
                last_saved_frame = f
                continue

            diff = compute_ssim_diff(prev_frame, frame)
            if diff > ssim_threshold and (f - last_saved_frame) > min_frame_gap:
                keyframes.append(frame)
                frame_indices.append(f)
                last_saved_frame = f

            prev_frame = frame

            # 제한 수 초과 시 중단
            if len(keyframes) >= max_frames_per_shot:
                break

        # 변화가 너무 적어 아무 프레임도 선택되지 않은 경우 → 중간 프레임 하나 저장
        if len(keyframes) == 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, (start_frame + end_frame) // 2)
            ret, frame = cap.read()
            if ret:
                keyframes = [frame]
                frame_indices = [ (start_frame + end_frame) // 2 ]

        # 저장
        for i, (kf, frame_num) in enumerate(zip(keyframes, frame_indices)):
            out_path = os.path.join(output_dir, f'shot_{idx:04d}_f{frame_num}.jpg')
            cv2.imwrite(out_path, kf)
            sampled_images.append((frame_num, out_path))

    cap.release()
    return sampled_images