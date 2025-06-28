import sys
import os
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QStackedWidget, QListWidget, QMessageBox
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QFont

# 导入项目模块
from midi_converter import convert_midi_to_score
from score_parser import parse_score
from drum_player import DrumPlayer

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("幻塔鼓谱演奏工具")
        self.setGeometry(100, 100, 900, 600)

        # --- 播放器实例 ---
        self.player = None
        self.current_score_data = None
        self.current_score_file = None
        self.score_files = []

        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            self.player = DrumPlayer(config['key_mapping'])
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载配置文件或初始化播放器: {e}")
            # 在没有播放器的情况下禁用相关控件
            self.midi_page.setEnabled(False)
            self.scores_page.setEnabled(False)
            return

        # --- 主布局 ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- 左侧导航栏 ---
        left_panel = QFrame(self)
        left_panel.setObjectName("left_panel")
        left_panel.setFixedWidth(150)
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        left_panel_layout.setContentsMargins(10, 20, 10, 20)
        left_panel_layout.setSpacing(15)

        # --- 右侧内容区 ---
        right_panel = QWidget(self)
        right_panel.setObjectName("right_panel")
        right_panel_layout = QVBoxLayout(right_panel)
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

        # --- 导航按钮 ---
        self.midi_button = QPushButton("MIDI")
        self.scores_button = QPushButton("SCORES")
        
        left_panel_layout.addWidget(self.midi_button)
        left_panel_layout.addWidget(self.scores_button)

        # --- 页面切换器 ---
        self.stacked_widget = QStackedWidget()
        right_panel_layout.addWidget(self.stacked_widget)

        # --- MIDI 页面 ---
        self.midi_page = QWidget()
        self.midi_page_layout = QVBoxLayout(self.midi_page)
        self.midi_list_widget = QListWidget()
        self.convert_button = QPushButton("MIDI 转幻塔乐谱")
        self.midi_page_layout.addWidget(QLabel("<h3>MIDI 文件列表</h3>"))
        self.midi_page_layout.addWidget(self.midi_list_widget)
        self.midi_page_layout.addWidget(self.convert_button)
        
        # --- 乐谱页面 ---
        self.scores_page = QWidget()
        self.scores_page_layout = QVBoxLayout(self.scores_page)
        self.scores_list_widget = QListWidget()
        self.scores_page_layout.addWidget(QLabel("<h3>乐谱文件列表</h3>"))
        self.scores_page_layout.addWidget(self.scores_list_widget)

        # 底部控制栏
        controls_frame = QFrame()
        controls_frame.setObjectName("controls_frame")
        controls_frame.setFixedHeight(100)
        controls_layout = QVBoxLayout(controls_frame)
        
        self.current_song_label = QLabel("当前未播放")
        self.current_song_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.prev_button = QPushButton("◀")
        self.play_pause_button = QPushButton("▶")
        self.next_button = QPushButton("▶")
        self.loop_button = QPushButton("循环:关")
        self.variation_button = QPushButton("随机:关")
        
        self.prev_button.setFixedSize(40, 40)
        self.play_pause_button.setFixedSize(40, 40)
        self.next_button.setFixedSize(40, 40)
        
        buttons_layout.addWidget(self.prev_button)
        buttons_layout.addWidget(self.play_pause_button)
        buttons_layout.addWidget(self.next_button)
        buttons_layout.addSpacing(50)
        buttons_layout.addWidget(self.loop_button)
        buttons_layout.addWidget(self.variation_button)

        controls_layout.addWidget(self.current_song_label)
        controls_layout.addLayout(buttons_layout)
        
        self.scores_page_layout.addWidget(controls_frame)
        
        # 将页面添加到切换器
        self.stacked_widget.addWidget(self.midi_page)
        self.stacked_widget.addWidget(self.scores_page)

        # --- 样式表 ---
        self.set_stylesheet()

        # --- 信号连接 ---
        self.midi_button.clicked.connect(self.go_to_midi_page)
        self.scores_button.clicked.connect(self.go_to_scores_page)
        
        # 转换按钮
        self.convert_button.clicked.connect(self.convert_midis)

        # 播放控制按钮
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.next_button.clicked.connect(self.play_next)
        self.prev_button.clicked.connect(self.play_prev)
        self.loop_button.clicked.connect(self.toggle_loop)
        self.variation_button.clicked.connect(self.toggle_variation)

        # 列表双击播放
        self.scores_list_widget.itemDoubleClicked.connect(self.play_selected_score)
        
        # 定时器，用于检查播放是否结束
        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(500) # 每0.5秒检查一次
        self.playback_timer.timeout.connect(self.update_playback_status)

        # 初始化
        self.ensure_dirs_exist()
        self.load_midi_list()
        self.load_scores_list()

        # 默认显示乐谱页面
        self.scores_button.click()

    def ensure_dirs_exist(self):
        """确保MIDI和scores目录存在"""
        if not os.path.exists("MIDI"):
            os.makedirs("MIDI")
        if not os.path.exists("scores"):
            os.makedirs("scores")
            
    def go_to_midi_page(self):
        self.stacked_widget.setCurrentWidget(self.midi_page)
        self.load_midi_list()

    def go_to_scores_page(self):
        self.stacked_widget.setCurrentWidget(self.scores_page)
        self.load_scores_list()

    def load_midi_list(self):
        self.midi_list_widget.clear()
        try:
            midi_files = [f for f in os.listdir("MIDI") if f.lower().endswith(('.mid', '.midi'))]
            if midi_files:
                self.midi_list_widget.addItems(midi_files)
            else:
                self.midi_list_widget.addItem("MIDI目录为空")
        except FileNotFoundError:
            self.midi_list_widget.addItem("MIDI目录不存在")

    def load_scores_list(self):
        self.scores_list_widget.clear()
        try:
            score_files = [f for f in os.listdir("scores") if f.lower().endswith('.json')]
            if score_files:
                self.scores_list_widget.addItems(score_files)
            else:
                self.scores_list_widget.addItem("scores目录为空")
        except FileNotFoundError:
            self.scores_list_widget.addItem("scores目录不存在")
        
        self.score_files = [self.scores_list_widget.item(i).text() for i in range(self.scores_list_widget.count())]
        if self.score_files and "scores目录为空" in self.score_files:
            self.score_files = []

    def play_selected_score(self, item):
        """双击列表项时播放选中的乐谱"""
        self.play_score_by_filename(item.text())

    def play_score_by_filename(self, filename):
        if self.player.is_playing():
            self.player.stop()

        self.current_score_file = filename
        score_path = os.path.join("scores", self.current_score_file)
        self.current_score_data = parse_score(score_path)

        if self.current_score_data:
            self.player.play_score(self.current_score_data)
            self.update_playback_status() # 立即更新状态
            self.playback_timer.start()
        else:
            QMessageBox.warning(self, "播放失败", f"无法解析乐谱文件: {self.current_score_file}")
            self.current_score_file = None

    def toggle_play_pause(self):
        if self.player.is_playing():
            self.player.stop()
        else:
            if self.current_score_data:
                self.player.play_score(self.current_score_data)
            else:
                # 如果没有当前乐谱，播放列表中的第一个
                if self.scores_list_widget.count() > 0:
                    first_item = self.scores_list_widget.item(0)
                    if first_item and "目录为空" not in first_item.text():
                        self.scores_list_widget.setCurrentItem(first_item)
                        self.play_selected_score(first_item)

        self.update_playback_status()

    def play_next(self):
        if not self.score_files: return
        current_index = self.scores_list_widget.currentRow()
        next_index = (current_index + 1) % len(self.score_files)
        self.scores_list_widget.setCurrentRow(next_index)
        self.play_score_by_filename(self.score_files[next_index])

    def play_prev(self):
        if not self.score_files: return
        current_index = self.scores_list_widget.currentRow()
        prev_index = (current_index - 1 + len(self.score_files)) % len(self.score_files)
        self.scores_list_widget.setCurrentRow(prev_index)
        self.play_score_by_filename(self.score_files[prev_index])

    def toggle_loop(self):
        is_looping = self.player.toggle_loop()
        self.loop_button.setText(f"循环:{'开' if is_looping else '关'}")
        self.loop_button.setStyleSheet("background-color: #a8e6cf;" if is_looping else "background-color: #e0e0e0;")

    def toggle_variation(self):
        is_variating = self.player.toggle_variation()
        self.variation_button.setText(f"随机:{'开' if is_variating else '关'}")
        self.variation_button.setStyleSheet("background-color: #a8e6cf;" if is_variating else "background-color: #e0e0e0;")
        
    def update_playback_status(self):
        if self.player.is_playing():
            self.play_pause_button.setText("❚❚")
            self.current_song_label.setText(f"正在播放: {self.current_score_file}")
        else:
            self.play_pause_button.setText("▶")
            if self.current_score_file:
                 self.current_song_label.setText(f"已暂停: {self.current_score_file}")
            else:
                 self.current_song_label.setText("当前未播放")
            self.playback_timer.stop()

    def convert_midis(self):
        """转换MIDI文件"""
        midi_dir = "MIDI"
        scores_dir = "scores"
        
        score_files_no_ext = {os.path.splitext(f)[0] for f in os.listdir(scores_dir)}
        
        midis_to_convert = [
            f for f in os.listdir(midi_dir) 
            if f.lower().endswith(('.mid', '.midi')) and os.path.splitext(f)[0] not in score_files_no_ext
        ]

        if not midis_to_convert:
            QMessageBox.information(self, "提示", "没有新的MIDI文件需要转换。")
            return

        converted_count = 0
        for filename in midis_to_convert:
            input_path = os.path.join(midi_dir, filename)
            output_filename = os.path.splitext(filename)[0] + '.json'
            output_path = os.path.join(scores_dir, output_filename)
            
            if convert_midi_to_score(input_path, output_path):
                converted_count += 1
        
        QMessageBox.information(self, "转换完成", f"成功转换了 {converted_count} 个MIDI文件。")
        self.load_scores_list()
        self.load_midi_list()

    def set_stylesheet(self):
        self.setStyleSheet("""
            #left_panel {
                background-color: #f0f0f0;
            }
            #right_panel {
                background-color: #ffffff;
            }
            #controls_frame {
                background-color: #fafafa;
                border-top: 1px solid #e0e0e0;
            }
            QPushButton {
                background-color: #e0e0e0;
                color: #333;
                border: none;
                padding: 10px;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d5d5d5;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #fdfdfd;
            }
            QLabel {
                font-size: 16px;
                color: #555;
            }
            #play_pause_button {
                font-size: 20px;
                border-radius: 20px; /* 圆形 */
            }
            #prev_button, #next_button {
                font-size: 20px;
                border-radius: 20px; /* 圆形 */
            }
        """)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 