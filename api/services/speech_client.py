#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import requests
import time
import json
from typing import Optional, Dict, Any
from pathlib import Path


class ChatterboxTTSClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = base_url.rstrip('/')
    
    def submit_tts_task(self, text: str, language_id: str = "zh") -> Optional[str]:
        """提交TTS任务并返回task_id（同步快速提交）"""
        try:
            resp = requests.post(
                f"{self.base_url}/submit_tts_task",
                data={"text": text, "language_id": language_id},
                timeout=10
            )
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 0:
                    return result.get("task_id")
            print(f"TTS任务提交失败: {resp.text}")
            return None
        except Exception as e:
            print(f"提交TTS任务时发生异常: {e}")
            return None
    
    def get_tts_result(self, task_id: str, timeout_seconds: int = 30, poll_interval: float = 0.5) -> Optional[str]:
        """轮询获取TTS任务结果，返回音频文件本地路径或URL"""
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            try:
                status_resp = requests.get(f"{self.base_url}/get_tts_status?task_id={task_id}", timeout=5)
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    status = status_data.get("status")
                    
                    if status == "completed":
                        # 获取最终结果
                        result_resp = requests.get(f"{self.base_url}/get_tts_result?task_id={task_id}")
                        if result_resp.status_code == 200:
                            result_data = result_resp.json()
                            # 这里返回服务器上的音频URL，你可以选择下载或直接使用
                            output_url = result_data.get("result", {}).get("output_url")
                            if output_url:
                                return f"{self.base_url}{output_url}"  # 返回完整可访问URL
                    elif status == "failed":
                        print(f"TTS任务 {task_id} 处理失败")
                        return None
                    # 如果还在处理中，继续等待
                time.sleep(poll_interval)
            except Exception as e:
                print(f"轮询TTS结果时发生异常: {e}")
                break
        print(f"获取TTS结果超时 (任务ID: {task_id})")
        return None
    
    def synthesize_speech(self, text: str, language_id: str = "zh", timeout_seconds: int = 30) -> Optional[str]:
        """合成语音，返回音频URL"""
        task_id = self.submit_tts_task(text, language_id)
        if task_id:
            return self.get_tts_result(task_id, timeout_seconds=timeout_seconds)
        return None


class FunASRClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8002"):
        self.base_url = base_url.rstrip('/')
    
    def submit_asr_task(self, audio_file_path: str, recognition_mode: str = "default", callback_url: Optional[str] = None) -> Optional[str]:
        """提交音频文件进行识别，返回task_id"""
        try:
            with open(audio_file_path, 'rb') as f:
                files = {'file': f}
                data = {
                    'recognition_mode': recognition_mode,
                }
                if callback_url:
                    data['callback_url'] = callback_url
                
                resp = requests.post(
                    f"{self.base_url}/submit_task",
                    files=files,
                    data=data,
                    timeout=30
                )
                if resp.status_code == 200:
                    result = resp.json()
                    if result.get("code") == 0:
                        return result.get("task_id")
            print(f"ASR任务提交失败: {resp.text}")
            return None
        except Exception as e:
            print(f"提交ASR任务时发生异常: {e}")
            return None
    
    def get_asr_result(self, task_id: str) -> Optional[str]:
        """获取ASR识别结果文本"""
        try:
            resp = requests.get(f"{self.base_url}/get_task_result?task_id={task_id}", timeout=10)
            if resp.status_code == 200:
                result = resp.json()
                if result.get("status") == "completed":
                    result_data = result.get("result", {})
                    # 根据识别模式提取文本
                    if result.get("recognition_mode") == "meeting":
                        # 会议模式返回对话列表
                        dialogue = result_data.get("dialogue", [])
                        # 将所有对话拼接成文本
                        texts = [f"{item.get('speaker', '')}: {item.get('text', '')}" for item in dialogue]
                        return "\n".join(texts)
                    else:
                        # 标准模式直接返回文本
                        return result_data.get("text")
        except Exception as e:
            print(f"获取ASR结果时发生异常: {e}")
        return None


# 全局客户端实例
tts_client = ChatterboxTTSClient()
asr_client = FunASRClient()