#!/usr/bin/env python3
# 测试语音服务客户端

from api.services.speech_client import tts_client, asr_client
import time

def test_tts():
    """测试TTS服务"""
    print("测试TTS服务...")
    text = "你好，这是一个测试语音"
    
    # 提交TTS任务
    task_id = tts_client.submit_tts_task(text)
    if not task_id:
        print("TTS任务提交失败")
        return False
    print(f"TTS任务提交成功，task_id: {task_id}")
    
    # 轮询获取结果
    max_wait_time = 30
    wait_interval = 1
    elapsed = 0
    audio_url = None
    
    while elapsed < max_wait_time:
        audio_url = tts_client.get_tts_result(task_id)
        if audio_url:
            break
        print(f"等待TTS结果... {elapsed}秒")
        time.sleep(wait_interval)
        elapsed += wait_interval
    
    if audio_url:
        print(f"TTS任务完成，音频URL: {audio_url}")
        return True
    else:
        print("TTS任务超时")
        return False

def test_asr():
    """测试ASR服务"""
    print("\n测试ASR服务...")
    # 注意：这里需要一个实际的音频文件路径
    audio_file = "test_audio.wav"
    
    try:
        # 提交ASR任务
        task_id = asr_client.submit_asr_task(audio_file)
        if not task_id:
            print("ASR任务提交失败")
            return False
        print(f"ASR任务提交成功，task_id: {task_id}")
        
        # 轮询获取结果
        max_wait_time = 30
        wait_interval = 1
        elapsed = 0
        text = None
        
        while elapsed < max_wait_time:
            text = asr_client.get_asr_result(task_id)
            if text:
                break
            print(f"等待ASR结果... {elapsed}秒")
            time.sleep(wait_interval)
            elapsed += wait_interval
        
        if text:
            print(f"ASR任务完成，识别结果: {text}")
            return True
        else:
            print("ASR任务超时")
            return False
    except Exception as e:
        print(f"ASR测试失败: {e}")
        return False

if __name__ == "__main__":
    print("开始测试语音服务客户端...")
    
    # 测试TTS
    tts_success = test_tts()
    
    # 测试ASR（需要实际的音频文件）
    asr_success = test_asr()
    
    print("\n测试完成！")
    print(f"TTS测试: {'成功' if tts_success else '失败'}")
    print(f"ASR测试: {'成功' if asr_success else '失败'}")
