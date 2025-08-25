import os
import torch
import json
import re
import asyncio
import logger_init
import torchvision.transforms as T
from PIL import Image
from torchvision.transforms.functional import InterpolationMode
from transformers import AutoModel, AutoTokenizer, AutoConfig
from contents_graph.queue_manager import internvl_queue
from contents_graph.safety_policy import get_policy
from contents_graph.request_manager  import set_status, set_result, get_task, set_progress, TaskStatus, TaskStatusCode

class InternvlWorker:
    def __init__(self, config: dict, root_path:str, device: str = "cuda:0", worker_id: str = "internvl-0"):
        self.logger = logger_init.get_logger()
        self.worker_id = worker_id
        self.device = device
        self.root_path = root_path
        self.model_name = config.get("MODEL", "OpenGVLab/InternVL3-8B")
        self.max_tokens = config.get("MAX_TOKENS", 256)
        self.temperature = config.get("TEMPERATURE", 0.0)
        self.top_p = config.get("TOP_P", 1.0)
        self.top_k = config.get("TOP_K", 0)
        self.do_sample = config.get("DO_SAMPLE", True)

        self.logger.info(f"[{self.worker_id}] Loading model...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True, use_fast=False)
        self.model = AutoModel.from_pretrained(self.model_name, torch_dtype="auto", load_in_8bit=False, low_cpu_mem_usage=True, use_flash_attn=True, trust_remote_code=True).eval().to(self.device) 
        self.hyperparameters = {
            "max_new_tokens": self.max_tokens,
            "do_sample": self.do_sample,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
        }
        self.decoder_config = config.get("DECODER", None)
        self.category_unification_map = config.get("CATEGORY_UNIFICATION_MAP", None)
        self.allowed_categories = config.get("ALLOW_CATEGORIES", [
            "blood", "drug", "alcohol", "injury", "violence", "self-harm", "smoking", "tattoo", "weapon", "insulting_gesture",
            "sexual", "nudity",
            "excrement", "vomit",
            "na"
        ])

        self.logger.info(f"[{self.worker_id}] loaded and ready.")

    def build_transform(self, input_size):
        IMAGENET_MEAN = (0.485, 0.456, 0.406)
        IMAGENET_STD = (0.229, 0.224, 0.225)
        MEAN, STD = IMAGENET_MEAN, IMAGENET_STD
        transform = T.Compose([
            T.Lambda(lambda img: img.convert('RGB') if img.mode != 'RGB' else img),
            T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
            T.ToTensor(),
            T.Normalize(mean=MEAN, std=STD)
        ])
        return transform

    def find_closest_aspect_ratio(self, aspect_ratio, target_ratios, width, height, image_size):
        best_ratio_diff = float('inf')
        best_ratio = (1, 1)
        area = width * height
        for ratio in target_ratios:
            target_aspect_ratio = ratio[0] / ratio[1]
            ratio_diff = abs(aspect_ratio - target_aspect_ratio)
            if ratio_diff < best_ratio_diff:
                best_ratio_diff = ratio_diff
                best_ratio = ratio
            elif ratio_diff == best_ratio_diff:
                if area > 0.5 * image_size * image_size * ratio[0] * ratio[1]:
                    best_ratio = ratio
        return best_ratio

    def dynamic_preprocess(self, image, min_num=1, max_num=12, image_size=448, use_thumbnail=False):
        orig_width, orig_height = image.size
        aspect_ratio = orig_width / orig_height

        # calculate the existing image aspect ratio
        target_ratios = set(
            (i, j) for n in range(min_num, max_num + 1) for i in range(1, n + 1) for j in range(1, n + 1) if
            i * j <= max_num and i * j >= min_num)
        target_ratios = sorted(target_ratios, key=lambda x: x[0] * x[1])

        # find the closest aspect ratio to the target
        target_aspect_ratio = self.find_closest_aspect_ratio(
            aspect_ratio, target_ratios, orig_width, orig_height, image_size)

        # calculate the target width and height
        target_width = image_size * target_aspect_ratio[0]
        target_height = image_size * target_aspect_ratio[1]
        blocks = target_aspect_ratio[0] * target_aspect_ratio[1]

        # resize the image
        resized_img = image.resize((target_width, target_height))
        processed_images = []
        for i in range(blocks):
            box = (
                (i % (target_width // image_size)) * image_size,
                (i // (target_width // image_size)) * image_size,
                ((i % (target_width // image_size)) + 1) * image_size,
                ((i // (target_width // image_size)) + 1) * image_size
            )
            # split the image
            split_img = resized_img.crop(box)
            processed_images.append(split_img)
        assert len(processed_images) == blocks
        if use_thumbnail and len(processed_images) != 1:
            thumbnail_img = image.resize((image_size, image_size))
            processed_images.append(thumbnail_img)
        return processed_images
    
    def load_video(self, keyframes,  input_size=448, max_num=12):
        pixel_values_list, num_patches_list = [], []
        transform = self.build_transform(input_size=input_size)

        for i, frame_info in enumerate(keyframes):
            img = frame_info["image"]
            # img = img.convert('RGB')
            self.logger.debug(f"[{self.worker_id}] Processing frame {i+1}/{len(keyframes)}: {img.mode}")
            # img = img.convert('RGB') if img.mode != 'RGB' else img
            # img.save(f"tmp_frame_{i}.jpg")
            img = self.dynamic_preprocess(img, image_size=input_size, use_thumbnail=True, max_num=max_num)
            pixel_values = [transform(tile) for tile in img]
            pixel_values = torch.stack(pixel_values)
            num_patches_list.append(pixel_values.shape[0])
            pixel_values_list.append(pixel_values)
        pixel_values = torch.cat(pixel_values_list)
        return pixel_values, num_patches_list
            

    def load_image(self, img, input_size=448, max_num=12):
        # image = Image.open(image_file).convert('RGB')
        image = Image.fromarray(img).convert('RGB')
        transform = self.build_transform(input_size=input_size)
        images = self.dynamic_preprocess(image, image_size=input_size, use_thumbnail=True, max_num=max_num)
        pixel_values = [transform(image) for image in images]
        pixel_values = torch.stack(pixel_values)
        return pixel_values

    def parse_vlm_output(self, output_text):
        """
        VLM의 출력에서 JSON 데이터를 추출하여 파이썬 딕셔너리로 반환합니다.
        
        Args:
            output_text: VLM에서 반환된 출력 문자열 또는 리스트
            
        Returns:
            dict: 파싱된 JSON 데이터
        """
        # 출력이 리스트인 경우 첫 번째 요소를 사용
        if isinstance(output_text, list) and len(output_text) > 0:
            text = output_text[0]
        else:
            text = output_text
        
        # JSON 블록 추출
        json_pattern = r'```json\n(.*?)\n```'
        match = re.search(json_pattern, text, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"JSON 파싱 오류: {e}")
                return None
        else:
            # JSON 블록이 없는 경우 다른 방식으로 시도
            # 중괄호로 감싸진 부분 찾기
            bracket_pattern = r'\{.*\}'
            match = re.search(bracket_pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError as e:
                    print(f"JSON 파싱 오류: {e}")
                    return None
        
        print("JSON 데이터를 찾을 수 없습니다.")
        return None

    def category_filtering(self, categories):
        """
        카테고리 통합 규칙을 적용합니다.
        예: explicit_sexual, implicit_sexual -> sexual
        예: explicit_nudity, implicit_nudity -> nudity
        예: physical_violence, sexual_violence -> violence
        """
        # 카테고리 이름 통일 적용
        unified_categories = []
        for cat in categories:
            unified = self.category_unification_map.get(cat, cat)
            unified = unified.strip().lower()
            if unified and unified in self.allowed_categories:
                unified_categories.append(unified)

        # 'na' 제거 조건: 다른 유효 카테고리가 있으면 'na' 제거
        filtered_categories = [c for c in unified_categories if c != 'na']

        if not filtered_categories:
            return ['na']
        else:
            return filtered_categories

    async def run(self):
        while True:
            task = await internvl_queue.get()
            await self.handle_task(task)

    async def handle_task(self, in_task: dict):
        task_id = in_task["task_id"]
        task = get_task(task_id)
        if not task or task["cancelled"]:
            set_status(task_id, TaskStatus.CANCELLED)
            return
        
        if task["status"] != TaskStatusCode.RUNNING:
            return 

        loop = asyncio.get_event_loop()

        try:
            policy = in_task["policy"]
            keyframes = in_task["keyframes"]
            shot_id = in_task["shot_id"]
            start_time = in_task["start_time"]
            end_time = in_task["end_time"]

            data = task["data"]
            shot_list = data["shotList"]
            
            instruction = get_policy(policy)
                
            response_json = None      

            # 비디오 처리 방식으로 진행 
            pixel_values, num_patches_list = await loop.run_in_executor(
                None, lambda: self.load_video(keyframes, max_num=1)
            )

            pixel_values = await loop.run_in_executor(
                None, lambda: pixel_values.to(torch.bfloat16).cuda()
            )

            video_prefix = ''.join([f'Frame{i+1}: <image>\n' for i in range(len(num_patches_list))])
            question = video_prefix + instruction

            def inference():
                with torch.inference_mode():
                    return self.model.chat(
                        self.tokenizer,
                        pixel_values,
                        question,
                        self.hyperparameters,
                        num_patches_list=num_patches_list
                    )
            response = await loop.run_in_executor(None, inference)
            self.logger.debug(f"Decoded response: {response}")

            response_json = self.parse_vlm_output(response)
            if response_json is None:
                raise ValueError(f"Failed to parse VLM output: {response}")

            # 결과
            result = {
                        "startTime": start_time, 
                        "endTime": end_time, 
                        "label": self.category_filtering(response_json['categories']), 
                        "description": response_json['description']
                    }
            
            set_result(task_id, result)
            task = get_task(task_id)
            progress = float(len(task["result"])) / float(len(shot_list))
            set_progress(task_id, progress)
            
            self.logger.info(f"[{self.worker_id}] task {task_id}, progress: {progress:.2f} ({len(task['result'])}/{len(shot_list)})")

            if progress >= 1.0:
                set_status(task_id, TaskStatus.COMPLETED)
                self.logger.info(f"[{self.worker_id}] Finished task {task_id}, progress: {progress:.2f}")

            
        except Exception as e:
            self.logger.error(f"[{self.worker_id}] Error: {e}")
            set_status(task_id, TaskStatus.FAILED, str(e))