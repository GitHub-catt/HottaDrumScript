import json
import yaml
import xml.etree.ElementTree as ET
import os

class ScoreParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.extension = os.path.splitext(self.file_path)[1].lower()

    def parse(self):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"乐谱文件不存在: {self.file_path}")

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                if self.extension == '.json':
                    return self._parse_json(f)
                elif self.extension in ['.yaml', '.yml']:
                    return self._parse_yaml(f)
                elif self.extension == '.xml':
                    return self._parse_xml(f)
                else:
                    raise ValueError(f"不支持的乐谱文件格式: {self.extension}")
        except Exception as e:
            print(f"解析乐谱文件时出错: {e}")
            return None

    def _parse_json(self, file_handle):
        return json.load(file_handle)

    def _parse_yaml(self, file_handle):
        return yaml.safe_load(file_handle)

    def _parse_xml(self, file_handle):
        try:
            tree = ET.parse(file_handle)
            root = tree.getroot()
            
            score_data = {
                "title": root.find('title').text if root.find('title') is not None else "Untitled",
                "bpm": int(root.find('bpm').text) if root.find('bpm') is not None else 120,
                "notes": []
            }
            
            for note_element in root.findall('notes/note'):
                time = note_element.find('time').text
                note_names = [n.text for n in note_element.findall('note_name')]
                
                score_data["notes"].append({
                    "time": int(time),
                    "note": note_names
                })
            return score_data
        except ET.ParseError as e:
            print(f"XML 解析错误: {e}")
            return None

def parse_score(file_path):
    """
    一个便捷的函数，用于解析给定路径的乐谱文件。
    """
    parser = ScoreParser(file_path)
    return parser.parse()

if __name__ == '__main__':
    # 此部分用于测试
    # 1. 创建一个示例XML乐谱文件用于测试
    xml_content = """
<score>
    <title>示例XML节奏</title>
    <bpm>120</bpm>
    <notes>
        <note>
            <time>0</time>
            <note_name>bass_drum</note_name>
            <note_name>close_hi_hat</note_name>
        </note>
        <note>
            <time>500</time>
            <note_name>snare</note_name>
        </note>
    </notes>
</score>
"""
    xml_test_file = 'test_score.xml'
    with open(xml_test_file, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    # 2. 测试解析功能
    print("--- 测试JSON解析 ---")
    json_score = parse_score('scores/example_score.json')
    if json_score:
        print(f"标题: {json_score.get('title')}")
        print(f"BPM: {json_score.get('bpm')}")
        print(f"音符数量: {len(json_score.get('notes', []))}")
        print("-" * 20)

    print("--- 测试XML解析 ---")
    xml_score = parse_score(xml_test_file)
    if xml_score:
        print(f"标题: {xml_score.get('title')}")
        print(f"BPM: {xml_score.get('bpm')}")
        print(f"音符数量: {len(xml_score.get('notes', []))}")
        print("-" * 20)
    
    # 3. 清理测试文件
    os.remove(xml_test_file) 