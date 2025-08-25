import openai
import json
import os
import time

from io import BytesIO
from openai import OpenAI
from PIL import Image

import concurrent.futures


import openai
import json
import time
from io import BytesIO
from PIL import Image
import concurrent.futures
from openai import OpenAI
from datetime import datetime


class OpenAIAssistantClient:
    def __init__(self, api_key, model="gpt-4o", assistant_name="", instruction_path=None):
        self.api_key = api_key
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.timeout = 120  # 타임아웃을 2분으로 증가

        if instruction_path is not None:
            try:
                with open(instruction_path, "r", encoding="utf-8") as file:
                    instruction = file.read()
            except FileNotFoundError:
                raise ValueError(f"지정한 파일 경로를 찾을 수 없습니다: {instruction_path}")
            except Exception as e:
                raise RuntimeError(f"지침 파일을 읽는 중 오류 발생: {e}")
        else:
            raise ValueError("instruction_path를 반드시 지정해야 합니다.")

        # 기존 assistant가 있는지 확인
        existing_assistant = self._find_existing_assistant(assistant_name)
        
        if existing_assistant:
            # 기존 assistant가 있으면 instruction만 업데이트
            self.assistant = self.client.beta.assistants.update(
                assistant_id=existing_assistant.id,
                instructions=instruction,
                model=self.model
            )
            print(f"기존 assistant '{assistant_name}'의 instruction을 업데이트했습니다.")
        else:
            # 새로운 assistant 생성
            self.assistant = self.client.beta.assistants.create(
                name=assistant_name,
                instructions=instruction,
                model=self.model,
                response_format="auto",  # Assistant API only supports 'auto'
            )
            print(f"새로운 assistant '{assistant_name}'을 생성했습니다.")

    def _find_existing_assistant(self, assistant_name):
        """동일한 이름의 assistant가 있는지 확인하고 반환"""
        if not assistant_name:
            return None
            
        try:
            # 모든 assistant 목록을 가져와서 이름으로 검색
            assistants = self.client.beta.assistants.list()
            for assistant in assistants.data:
                if assistant.name == assistant_name:
                    return assistant
            return None
        except Exception as e:
            print(f"기존 assistant 검색 중 오류 발생: {e}")
            return None

    def _init_thread(self):
        return self.client.beta.threads.create()

    def _process_image(self, img):
        if isinstance(img, str):  # file path
            return open(img, "rb")
        elif isinstance(img, Image.Image):
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            buffered.name = "image.png"
            buffered.seek(0)
            return buffered
        elif isinstance(img, bytes):
            buffered = BytesIO(img)
            buffered.name = "image.png"
            buffered.seek(0)
            return buffered
        return img

    def _run(self, prompt, image=None):
        thread = self._init_thread()

        # 메시지 구성
        if image:
            input_file = self.client.files.create(
                file=self._process_image(image), purpose="vision"
            )
            msg_content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_file",
                    "image_file": {"file_id": input_file.id, "detail": "auto"},
                },
            ]
        else:
            msg_content = [{"type": "text", "text": prompt}]

        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=msg_content,
        )

        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant.id,
            temperature=1.0,
        )

        # Polling
        max_wait_time = 120  # 최대 2분 대기
        start_time = time.time()
        
        while True:
            if time.time() - start_time > max_wait_time:
                return f"[ERROR] Run timeout after {max_wait_time}s"
                
            run_status = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=run.id
            )
            if run_status.status == "completed":
                break
            elif run_status.status in ["queued", "in_progress"]:
                time.sleep(2)
            elif run_status.status == "failed":
                error_msg = f"[ERROR] Run failed: {run_status.status}"
                if hasattr(run_status, 'last_error') and run_status.last_error:
                    error_msg += f" - {run_status.last_error.message}"
                return error_msg
            elif run_status.status == "cancelled":
                return f"[ERROR] Run cancelled: {run_status.status}"
            elif run_status.status == "expired":
                return f"[ERROR] Run expired: {run_status.status}"
            else:
                return f"[ERROR] Unknown run status: {run_status.status}"

        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        result = messages.data[0].content[0].text.value.strip()
        self.client.beta.threads.delete(thread.id)
        return result

    def __call__(self, prompt, image=None):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self._run, prompt, image)
            try:
                result = future.result(timeout=self.timeout)
                # 에러 메시지인지 확인
                if result.startswith("[ERROR]"):
                    print(f"API 호출 에러: {result}")
                    return ""
                return result
            except concurrent.futures.TimeoutError:
                print(f"API 호출 타임아웃 (timeout={self.timeout}s)")
                return ""
            except Exception as e:
                print(f"API 호출 예외: {str(e)}")
                return ""

    def run_batch_job(self, prompts, output_file="output/batch_output.jsonl"):
        jsonl_filename = "output/batch_input.jsonl"
        with open(jsonl_filename, "w", encoding="utf-8") as f:
            for prompt in prompts:
                # ✅ custom_id: timestamp 기반 생성
                timestamp_id = datetime.now().strftime("%Y%m%d%H%M%S%f")  # 예: 20250529104530123456
                request = {
                    "custom_id": f"req_{timestamp_id}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                    }
                }
                f.write(json.dumps(request) + "\n")
        
        # 이후는 동일
        uploaded_file = self.client.files.create(
            file=open(jsonl_filename, "rb"),
            purpose="batch"
        )
        print(f"Uploaded file ID: {uploaded_file.id}")

        batch_job = self.client.batches.create(
            input_file_id=uploaded_file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h"
        )
        print(f"Batch job ID: {batch_job.id}")

        while True:
            status = self.client.batches.retrieve(batch_job.id)
            print(f"Batch job status: {status.status}")
            if status.status == "completed":
                break
            elif status.status in ["failed", "expired"]:
                raise RuntimeError(f"Batch job failed with status: {status.status}")
            time.sleep(5)

        result_file = self.client.files.retrieve(status.output_file_id)
        result_content = self.client.files.content(result_file.id)

        # 바이너리 응답을 bytes로 변환하여 저장
        with open(output_file, "wb") as f:
            f.write(result_content.read())
        print(f"Batch results saved to {output_file}")

        # 원본 응답 내용을 문자열로 반환
        with open(output_file, "r", encoding="utf-8") as f:
            return f.read()
        

class OpenAIChatClient:
    def __init__(self, api_key, model="gpt-4o", timeout=120):
        self.api_key = api_key
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.timeout = timeout  # seconds

    def _run(self, prompt):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[ERROR] ChatCompletion failed: {str(e)}"

    def __call__(self, prompt):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self._run, prompt)
            try:
                result = future.result(timeout=self.timeout)
                if result.startswith("[ERROR]"):
                    print(f"API 호출 에러: {result}")
                    return ""
                return result
            except concurrent.futures.TimeoutError:
                print(f"API 호출 타임아웃 (timeout={self.timeout}s)")
                return ""
            except Exception as e:
                print(f"API 호출 예외: {str(e)}")
                return ""

    def run_batch_job(self, prompts, output_file="output/batch_output.jsonl"):
        jsonl_filename = "output/batch_input.jsonl"
        with open(jsonl_filename, "w", encoding="utf-8") as f:
            for prompt in prompts:
                timestamp_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
                request = {
                    "custom_id": f"req_{timestamp_id}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                    }
                }
                f.write(json.dumps(request) + "\n")

        uploaded_file = self.client.files.create(
            file=open(jsonl_filename, "rb"),
            purpose="batch"
        )
        print(f"Uploaded file ID: {uploaded_file.id}")

        batch_job = self.client.batches.create(
            input_file_id=uploaded_file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h"
        )
        print(f"Batch job ID: {batch_job.id}")

        while True:
            status = self.client.batches.retrieve(batch_job.id)
            print(f"Batch job status: {status.status}")
            if status.status == "completed":
                break
            elif status.status in ["failed", "expired"]:
                raise RuntimeError(f"Batch job failed with status: {status.status}")
            time.sleep(5)

        result_file = self.client.files.retrieve(status.output_file_id)
        result_content = self.client.files.content(result_file.id)

        with open(output_file, "wb") as f:
            f.write(result_content.read())
        print(f"Batch results saved to {output_file}")

        with open(output_file, "r", encoding="utf-8") as f:
            return f.read()