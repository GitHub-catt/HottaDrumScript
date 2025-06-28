import json
import mido
import os

# GM MIDI鼓声映射到项目鼓声名称
# 参考: https://computermusicresource.com/GM.Percussion.KeyMap.html
GM_DRUM_MAP = {
    # Bass Drum
    35: 'bass_drum', 36: 'bass_drum',
    # Snare
    38: 'snare', 40: 'snare',
    # Hi-Hat
    42: 'close_hi_hat', 44: 'close_hi_hat', 46: 'close_hi_hat', # Closed, Pedal, Open
    # Toms
    41: 'floor_tom', 43: 'floor_tom', # Low Floor Tom, High Floor Tom
    45: 'low_tom', 47: 'low_tom', # Low Tom, Low-Mid Tom
    48: 'high_tom', 50: 'high_tom', # Hi-Mid Tom, High Tom
    # Cymbals
    49: 'crash_cymbal', 57: 'crash_cymbal', # Crash Cymbal 1, 2
    51: 'ride_cymbal', 59: 'ride_cymbal', # Ride Cymbal 1, 2
    53: 'ride_cymbal' # Ride Bell
}

def convert_midi_to_score(midi_file_path: str, output_json_path: str = None) -> dict:
    """
    将MIDI文件中的鼓音轨转换为项目特定的鼓谱JSON格式。

    :param midi_file_path: 输入的MIDI文件路径。
    :param output_json_path: (可选) 输出的JSON文件路径。如果提供，将保存转换后的鼓谱。
    :return: 一个包含鼓谱数据的字典。
    """
    try:
        midi_file = mido.MidiFile(midi_file_path)
    except Exception as e:
        print(f"错误: 无法加载MIDI文件 '{midi_file_path}'. {e}")
        return None

    ticks_per_beat = midi_file.ticks_per_beat or 480
    tempo = 500000  # 默认为120 BPM

    notes = []
    current_time_ms = 0
    
    # 查找鼓轨道 (通常是通道 9, 在mido中是0-indexed)
    drum_track = None
    for i, track in enumerate(midi_file.tracks):
        is_drum_track = any(msg.channel == 9 for msg in track if hasattr(msg, 'channel'))
        if is_drum_track:
            drum_track = track
            print(f"在轨道 {i} 上找到鼓音轨。")
            break
    
    if not drum_track:
        print("警告: 在MIDI文件中未找到鼓音轨(通道10)。将尝试解析第一个轨道。")
        drum_track = midi_file.tracks[0]

    for msg in drum_track:
        # 将delta-time(ticks)转换为毫秒
        current_time_ms += mido.tick2second(msg.time, ticks_per_beat, tempo) * 1000

        if msg.type == 'set_tempo':
            tempo = msg.tempo
        
        if msg.type == 'note_on' and msg.velocity > 0:
            if msg.channel == 9: # 确保是鼓通道
                drum_note_name = GM_DRUM_MAP.get(msg.note)
                if drum_note_name:
                    notes.append({
                        "time": round(current_time_ms),
                        "note": [drum_note_name]
                    })

    if not notes:
        print("警告: 未能从MIDI文件中提取任何有效的鼓点。")
        return None

    # 合并同时发生的音符
    if not notes:
        return {"title": os.path.basename(midi_file_path), "bpm": round(60000000 / tempo), "notes": []}

    merged_notes = []
    
    notes.sort(key=lambda x: x['time'])
    
    time_grouped_notes = {}
    for note in notes:
        t = note["time"]
        if t not in time_grouped_notes:
            time_grouped_notes[t] = []
        time_grouped_notes[t].append(note["note"][0])

    for t, note_list in time_grouped_notes.items():
        unique_notes = sorted(list(set(note_list)))
        merged_notes.append({"time": t, "note": unique_notes})

    merged_notes.sort(key=lambda x: x['time'])
    
    # 将时间戳转换为相对第一个音符的时间
    first_note_time = merged_notes[0]['time'] if merged_notes else 0
    for note in merged_notes:
        note['time'] -= first_note_time

    score = {
        "title": os.path.splitext(os.path.basename(midi_file_path))[0],
        "bpm": round(60000000 / tempo),
        "notes": merged_notes
    }

    if output_json_path:
        try:
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(score, f, ensure_ascii=False, indent=2)
            print(f"鼓谱已成功保存到: {output_json_path}")
        except Exception as e:
            print(f"错误: 无法保存鼓谱文件 '{output_json_path}'. {e}")

    return score

if __name__ == '__main__':
    # 使用方法示例：批量转换MIDI目录下的所有文件
    MIDI_INPUT_DIR = 'MIDI'
    JSON_OUTPUT_DIR = 'scores'

    # 确保目录存在
    if not os.path.isdir(MIDI_INPUT_DIR):
        print(f"错误: MIDI输入目录 '{MIDI_INPUT_DIR}' 不存在或不是一个目录。")
        print("请创建 'MIDI' 目录并将你的 .mid 或 .midi 文件放入其中。")
    else:
        if not os.path.exists(JSON_OUTPUT_DIR):
            os.makedirs(JSON_OUTPUT_DIR)
            print(f"创建输出目录: {JSON_OUTPUT_DIR}")

        # 查找所有MIDI文件
        midi_files_to_convert = [
            f for f in os.listdir(MIDI_INPUT_DIR)
            if f.lower().endswith(('.mid', '.midi')) and os.path.isfile(os.path.join(MIDI_INPUT_DIR, f))
        ]

        if not midi_files_to_convert:
            print(f"在 '{MIDI_INPUT_DIR}' 目录中未找到MIDI文件。")
        else:
            print(f"找到 {len(midi_files_to_convert)} 个MIDI文件。开始转换...")
            successful_conversions = 0
            for filename in midi_files_to_convert:
                input_path = os.path.join(MIDI_INPUT_DIR, filename)
                output_filename = os.path.splitext(filename)[0] + '.json'
                output_path = os.path.join(JSON_OUTPUT_DIR, output_filename)

                print(f"\n--- 正在转换 '{input_path}' ---")
                converted_score = convert_midi_to_score(input_path, output_path)
                if converted_score:
                    successful_conversions += 1

            print(f"\n--- 批量转换完成 ---")
            print(f"成功转换 {successful_conversions}/{len(midi_files_to_convert)} 个文件。")
            print(f"转换后的文件位于 '{JSON_OUTPUT_DIR}' 目录。") 