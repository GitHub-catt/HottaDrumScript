import pydirectinput
import time
import threading
import random
import math

# 在Windows上，pydirectinput通常不需要特殊配置。
# 确保游戏窗口是当前焦点窗口。
pydirectinput.PAUSE = 0.01  # 每次按键之间的微小延迟，可以根据游戏响应调整

class DrumPlayer:
    def __init__(self, key_mapping):
        self.key_mapping = key_mapping
        self.stop_event = threading.Event()
        self.playing_thread = None
        self.loop_enabled = False
        self.variation_enabled = False

    def toggle_loop(self):
        """切换循环模式并返回当前状态。"""
        self.loop_enabled = not self.loop_enabled
        return self.loop_enabled

    def toggle_variation(self):
        """切换变化模式并返回当前状态。"""
        self.variation_enabled = not self.variation_enabled
        return self.variation_enabled

    def _play_note_group(self, notes_to_play):
        """
        处理一组需要同时按下的音符。
        """
        keys_to_press = []
        for note in notes_to_play:
            key = self.key_mapping.get(note)
            if key:
                keys_to_press.append(key)
            else:
                print(f"警告: 在键位映射中未找到音符 '{note}'")

        if not keys_to_press:
            return

        # 按下所有按键
        for key in keys_to_press:
            pydirectinput.keyDown(key)
        
        # 短暂保持，模拟真实敲击
        time.sleep(0.05)

        # 释放所有按键
        for key in keys_to_press:
            pydirectinput.keyUp(key)

    def _play_score_task(self, score_data):
        """
        在后台线程中执行乐谱演奏，支持循环和节拍对齐。
        """
        print("开始演奏... 请将焦点切换到游戏窗口。")
        time.sleep(3) # 演奏前给予用户切换窗口的时间

        notes = sorted(score_data.get('notes', []), key=lambda x: x['time'])
        
        bpm = score_data.get('bpm', 120)
        measure_duration_ms = 240000 / bpm  # 4/4拍一个小节的毫秒数

        total_loop_duration_s = 0
        if notes:
            last_note_time_ms = notes[-1]['time']
            num_measures = math.floor(last_note_time_ms / measure_duration_ms) + 1
            total_loop_duration_s = (num_measures * measure_duration_ms) / 1000.0
        
        if total_loop_duration_s <= 0:
            print("警告：无法计算乐谱时长，循环功能可能不准确。")
            # 设定一个默认值以防万一
            total_loop_duration_s = (measure_duration_ms * 4) / 1000.0

        performance_start_time = time.perf_counter()
        loop_count = 0

        while not self.stop_event.is_set():
            notes_this_loop = notes
            if self.variation_enabled:
                notes_this_loop = [
                    note for note in notes 
                    if random.random() <= note.get('probability', 1.0)
                ]
            
            current_loop_offset_s = loop_count * total_loop_duration_s
            
            for note_event in notes_this_loop:
                if self.stop_event.is_set():
                    break

                event_time_ms = note_event['time']
                target_absolute_time = performance_start_time + current_loop_offset_s + (event_time_ms / 1000.0)
                
                sleep_duration = target_absolute_time - time.perf_counter()
                if sleep_duration > 0:
                    time.sleep(sleep_duration)

                if self.stop_event.is_set():
                    break
                    
                self._play_note_group(note_event['note'])

            if not self.loop_enabled or self.stop_event.is_set():
                break
            else:
                print("乐谱循环播放...")
                loop_count += 1
                time.sleep(0.001)

        if not self.stop_event.is_set():
            print("乐谱演奏完毕。")
        else:
            print("演奏已停止。")
        
        self.stop_event.clear()

    def play_score(self, score_data):
        """
        开始在一个新线程中演奏乐谱。
        """
        if self.is_playing():
            print("已经在演奏中。")
            return

        self.stop_event.clear()
        self.playing_thread = threading.Thread(target=self._play_score_task, args=(score_data,))
        self.playing_thread.start()

    def stop(self):
        """
        停止当前的演奏。
        """
        if not self.is_playing():
            return
            
        print("正在停止演奏...")
        self.stop_event.set()
        self.playing_thread.join() # 等待线程完全结束
        self.playing_thread = None
        print("已停止。")

    def is_playing(self):
        """
        检查当前是否正在演奏。
        """
        return self.playing_thread and self.playing_thread.is_alive()

if __name__ == '__main__':
    # 此部分用于测试
    import json
    
    # 1. 加载配置和示例乐谱
    with open('config.json', 'r') as f:
        config = json.load(f)
    key_map = config['key_mapping']
    
    with open('scores/example_score.json', 'r') as f:
        test_score = json.load(f)

    # 2. 创建播放器实例
    player = DrumPlayer(key_map)

    # 3. 模拟演奏流程
    print("测试开始：将在5秒后开始演奏示例乐谱。")
    print("请在5秒内手动打开一个记事本或文本编辑器来观察按键模拟。")
    time.sleep(5)

    player.play_score(test_score)

    # 等待一段时间，模拟用户在演奏过程中决定停止
    try:
        while player.is_playing():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n捕获到Ctrl+C，正在停止演奏...")
        player.stop()

    print("测试结束。") 