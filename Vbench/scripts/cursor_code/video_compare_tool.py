"""
视频对比工具 (Video Comparison Tool)

功能：
- 多视频同时播放比较
- 支持2/3/4/6/8/9宫格布局
- 高质量视频显示（4K->2K）
- GUI控制界面
"""

import sys
import os
from pathlib import Path
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QComboBox, QFileDialog, QGridLayout,
    QGroupBox, QSpinBox, QMessageBox, QListWidget, QListWidgetItem,
    QSplitter
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap, QFont
import time


class VideoLoader:
    """视频加载器 - 扫描文件夹并组织视频"""
    
    SUPPORTED_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v']
    
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.video_groups = {}
        self.load_videos()
    
    def load_videos(self):
        """扫描根目录下的所有子文件夹和视频"""
        if not self.root_path.exists():
            raise ValueError(f"路径不存在: {self.root_path}")
        
        # 遍历子文件夹
        for subfolder in self.root_path.iterdir():
            if subfolder.is_dir():
                videos = []
                for video_file in subfolder.iterdir():
                    if video_file.suffix.lower() in self.SUPPORTED_FORMATS:
                        videos.append(video_file)
                
                if videos:
                    # 按文件名排序
                    videos.sort(key=lambda x: x.name)
                    self.video_groups[subfolder.name] = videos
        
        print(f"找到 {len(self.video_groups)} 个视频组")
        for group_name, videos in self.video_groups.items():
            print(f"  {group_name}: {len(videos)} 个视频")
    
    def get_group_names(self):
        """获取所有组名"""
        return sorted(self.video_groups.keys())
    
    def get_videos(self, group_name):
        """获取指定组的视频列表"""
        return self.video_groups.get(group_name, [])
    
    def get_video_at_index(self, group_name, index):
        """获取指定组的第index个视频"""
        videos = self.get_videos(group_name)
        if 0 <= index < len(videos):
            return videos[index]
        return None
    
    def get_video_count(self, group_name):
        """获取指定组的视频数量"""
        return len(self.get_videos(group_name))


class VideoPlayer:
    """单个视频播放器"""
    
    def __init__(self, video_path, target_height=1080):
        self.video_path = str(video_path)
        self.target_height = target_height
        self.cap = None
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30
        self.is_opened = False
        
        self.open_video()
    
    def open_video(self):
        """打开视频文件"""
        self.cap = cv2.VideoCapture(self.video_path)
        if self.cap.isOpened():
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
            self.is_opened = True
            print(f"打开视频: {Path(self.video_path).name}")
            print(f"  总帧数: {self.total_frames}, FPS: {self.fps:.2f}")
        else:
            print(f"无法打开视频: {self.video_path}")
            self.is_opened = False
    
    def read_frame(self):
        """读取当前帧"""
        if not self.is_opened:
            return None
        
        ret, frame = self.cap.read()
        if ret:
            self.current_frame += 1
            # 调整大小以保持高质量
            frame = self.resize_frame(frame)
            return frame
        return None
    
    def seek(self, frame_number):
        """跳转到指定帧"""
        if self.is_opened:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            self.current_frame = frame_number
    
    def resize_frame(self, frame):
        """调整帧大小以保持高质量"""
        h, w = frame.shape[:2]
        
        # 如果高度大于目标高度，则缩放
        if h > self.target_height:
            scale = self.target_height / h
            new_w = int(w * scale)
            new_h = self.target_height
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        return frame
    
    def reset(self):
        """重置到开始"""
        self.seek(0)
    
    def close(self):
        """关闭视频"""
        if self.cap:
            self.cap.release()
            self.is_opened = False
    
    def get_progress(self):
        """获取播放进度 (0-1)"""
        if self.total_frames > 0:
            return self.current_frame / self.total_frames
        return 0.0


class MultiVideoPlayer:
    """多视频同步播放器"""
    
    def __init__(self, video_paths, target_height=1080):
        self.video_paths = video_paths
        self.target_height = target_height
        self.players = []
        self.init_players()
    
    def init_players(self):
        """初始化所有播放器"""
        self.close_all()
        self.players = []
        
        for video_path in self.video_paths:
            if video_path:
                player = VideoPlayer(video_path, self.target_height)
                self.players.append(player)
            else:
                self.players.append(None)
    
    def read_all_frames(self):
        """读取所有视频的当前帧"""
        frames = []
        for player in self.players:
            if player and player.is_opened:
                frame = player.read_frame()
                frames.append(frame)
            else:
                frames.append(None)
        return frames
    
    def seek_all(self, frame_number):
        """所有视频跳转到指定帧"""
        for player in self.players:
            if player:
                player.seek(frame_number)
    
    def reset_all(self):
        """所有视频重置"""
        for player in self.players:
            if player:
                player.reset()
    
    def close_all(self):
        """关闭所有视频"""
        for player in self.players:
            if player:
                player.close()
        self.players = []
    
    def get_max_frames(self):
        """获取最长视频的帧数"""
        max_frames = 0
        for player in self.players:
            if player:
                max_frames = max(max_frames, player.total_frames)
        return max_frames
    
    def get_average_fps(self):
        """获取平均帧率"""
        fps_list = [p.fps for p in self.players if p]
        return sum(fps_list) / len(fps_list) if fps_list else 30


class VideoDisplayWidget(QLabel):
    """视频显示控件"""
    
    def __init__(self, title="Video", parent=None):
        super().__init__(parent)
        self.title = title
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("QLabel { background-color: black; color: white; }")
        self.setMinimumSize(320, 180)
        self.setText(f"{title}\n(未加载)")
    
    def update_frame(self, frame):
        """更新显示帧"""
        if frame is None:
            self.setText(f"{self.title}\n(无画面)")
            return
        
        # OpenCV BGR -> RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        
        # 转换为QImage
        qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # 缩放以适应窗口，保持宽高比
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self.setPixmap(scaled_pixmap)


class VideoCompareMainWindow(QMainWindow):
    """主窗口"""
    
    LAYOUT_CONFIGS = {
        "1x1": (1, 1),
        "1x2": (1, 2),
        "2x1": (2, 1),
        "2x2": (2, 2),
        "1x3": (1, 3),
        "3x1": (3, 1),
        "2x3": (2, 3),
        "3x2": (3, 2),
        "2x4": (2, 4),
        "4x2": (4, 2),
        "3x3": (3, 3),
    }
    
    def __init__(self):
        super().__init__()
        self.video_loader = None
        self.multi_player = None
        self.current_video_index = 0
        self.is_playing = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        self.selected_groups = []
        self.display_widgets = []
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("视频对比工具 - Video Comparison Tool")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：视频选择面板
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # 右侧：视频显示和控制
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        
        main_layout.addWidget(splitter)
        
        # 状态栏
        self.statusBar().showMessage("请选择视频文件夹")
    
    def create_left_panel(self):
        """创建左侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 文件夹选择
        folder_group = QGroupBox("视频文件夹")
        folder_layout = QVBoxLayout()
        
        self.folder_label = QLabel("未选择文件夹")
        self.folder_label.setWordWrap(True)
        folder_layout.addWidget(self.folder_label)
        
        btn_select_folder = QPushButton("选择文件夹")
        btn_select_folder.clicked.connect(self.select_folder)
        folder_layout.addWidget(btn_select_folder)
        
        folder_group.setLayout(folder_layout)
        layout.addWidget(folder_group)
        
        # 视频组选择
        group_select = QGroupBox("选择对比组")
        group_layout = QVBoxLayout()
        
        self.group_list = QListWidget()
        self.group_list.setSelectionMode(QListWidget.MultiSelection)
        self.group_list.itemSelectionChanged.connect(self.on_group_selection_changed)
        group_layout.addWidget(self.group_list)
        
        btn_load_videos = QPushButton("加载选中的视频")
        btn_load_videos.clicked.connect(self.load_selected_videos)
        group_layout.addWidget(btn_load_videos)
        
        group_select.setLayout(group_layout)
        layout.addWidget(group_select)
        
        # 视频列表
        video_list_group = QGroupBox("当前视频列表")
        video_list_layout = QVBoxLayout()
        
        self.video_list_label = QLabel("未加载视频")
        self.video_list_label.setWordWrap(True)
        video_list_layout.addWidget(self.video_list_label)
        
        video_list_group.setLayout(video_list_layout)
        layout.addWidget(video_list_group)
        
        layout.addStretch()
        return panel
    
    def create_right_panel(self):
        """创建右侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 布局选择
        layout_control = QHBoxLayout()
        layout_control.addWidget(QLabel("布局:"))
        
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(self.LAYOUT_CONFIGS.keys())
        self.layout_combo.setCurrentText("2x2")
        self.layout_combo.currentTextChanged.connect(self.change_layout)
        layout_control.addWidget(self.layout_combo)
        
        layout_control.addWidget(QLabel("显示高度:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(480, 2160)
        self.height_spin.setValue(1080)
        self.height_spin.setSuffix(" px")
        self.height_spin.setSingleStep(180)
        layout_control.addWidget(self.height_spin)
        
        layout_control.addStretch()
        layout.addLayout(layout_control)
        
        # 视频显示区域
        self.video_display_widget = QWidget()
        self.video_grid_layout = QGridLayout(self.video_display_widget)
        self.video_grid_layout.setSpacing(2)
        layout.addWidget(self.video_display_widget, stretch=1)
        
        # 初始化显示布局
        self.setup_display_grid()
        
        # 进度条
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("进度:"))
        
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        progress_layout.addWidget(self.progress_slider)
        
        self.time_label = QLabel("00:00 / 00:00")
        progress_layout.addWidget(self.time_label)
        
        layout.addLayout(progress_layout)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.btn_prev = QPushButton("⏮ 上一个")
        self.btn_prev.clicked.connect(self.prev_video)
        control_layout.addWidget(self.btn_prev)
        
        self.btn_play = QPushButton("▶ 播放")
        self.btn_play.clicked.connect(self.toggle_play)
        control_layout.addWidget(self.btn_play)
        
        self.btn_next = QPushButton("下一个 ⏭")
        self.btn_next.clicked.connect(self.next_video)
        control_layout.addWidget(self.btn_next)
        
        self.btn_reset = QPushButton("🔄 重置")
        self.btn_reset.clicked.connect(self.reset_videos)
        control_layout.addWidget(self.btn_reset)
        
        control_layout.addStretch()
        
        # 播放速度
        control_layout.addWidget(QLabel("速度:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "0.75x", "1x", "1.5x", "2x"])
        self.speed_combo.setCurrentText("1x")
        control_layout.addWidget(self.speed_combo)
        
        layout.addLayout(control_layout)
        
        return panel
    
    def setup_display_grid(self):
        """设置显示网格"""
        # 清除现有控件
        while self.video_grid_layout.count():
            item = self.video_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.display_widgets = []
        
        # 获取当前布局配置
        layout_name = self.layout_combo.currentText()
        rows, cols = self.LAYOUT_CONFIGS[layout_name]
        
        # 创建显示控件
        for i in range(rows):
            for j in range(cols):
                index = i * cols + j
                widget = VideoDisplayWidget(f"视频 {index + 1}")
                self.video_grid_layout.addWidget(widget, i, j)
                self.display_widgets.append(widget)
    
    def change_layout(self):
        """改变布局"""
        self.setup_display_grid()
        
        # 如果已加载视频，重新加载以适应新布局
        if self.multi_player:
            self.load_selected_videos()
    
    def select_folder(self):
        """选择文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择视频根目录")
        if folder:
            try:
                self.video_loader = VideoLoader(folder)
                self.folder_label.setText(f"已选择: {folder}")
                
                # 更新组列表
                self.group_list.clear()
                for group_name in self.video_loader.get_group_names():
                    count = self.video_loader.get_video_count(group_name)
                    item = QListWidgetItem(f"{group_name} ({count} 个视频)")
                    item.setData(Qt.UserRole, group_name)
                    self.group_list.addItem(item)
                
                self.statusBar().showMessage(
                    f"找到 {len(self.video_loader.get_group_names())} 个视频组"
                )
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载文件夹失败: {str(e)}")
    
    def on_group_selection_changed(self):
        """组选择改变"""
        selected_items = self.group_list.selectedItems()
        self.selected_groups = [item.data(Qt.UserRole) for item in selected_items]
    
    def load_selected_videos(self):
        """加载选中的视频进行对比"""
        if not self.video_loader:
            QMessageBox.warning(self, "警告", "请先选择视频文件夹")
            return
        
        if not self.selected_groups:
            QMessageBox.warning(self, "警告", "请至少选择一个视频组")
            return
        
        # 检查是否超过布局数量
        max_videos = len(self.display_widgets)
        if len(self.selected_groups) > max_videos:
            QMessageBox.warning(
                self, "警告",
                f"选择的组数 ({len(self.selected_groups)}) 超过当前布局容量 ({max_videos})。\n"
                f"只会加载前 {max_videos} 个组。"
            )
            self.selected_groups = self.selected_groups[:max_videos]
        
        # 停止当前播放
        self.stop_playing()
        
        # 获取每个组的第一个视频
        video_paths = []
        for group_name in self.selected_groups:
            video = self.video_loader.get_video_at_index(group_name, 0)
            video_paths.append(video)
        
        # 填充空位
        while len(video_paths) < len(self.display_widgets):
            video_paths.append(None)
        
        # 创建多视频播放器
        target_height = self.height_spin.value()
        self.multi_player = MultiVideoPlayer(video_paths, target_height)
        
        # 更新显示控件标题
        for i, (widget, group_name) in enumerate(zip(self.display_widgets, self.selected_groups)):
            widget.title = f"{group_name}"
        
        # 重置索引
        self.current_video_index = 0
        self.update_video_list()
        
        # 显示第一帧
        self.display_current_frame()
        
        self.statusBar().showMessage(f"已加载 {len(self.selected_groups)} 个视频组的第 1 个视频")
    
    def update_video_list(self):
        """更新视频列表显示"""
        if not self.video_loader or not self.selected_groups:
            return
        
        text = f"当前: 第 {self.current_video_index + 1} 个视频\n\n"
        for group_name in self.selected_groups:
            total = self.video_loader.get_video_count(group_name)
            video = self.video_loader.get_video_at_index(group_name, self.current_video_index)
            if video:
                text += f"{group_name}:\n  {video.name}\n"
            else:
                text += f"{group_name}:\n  (无视频)\n"
        
        self.video_list_label.setText(text)
    
    def display_current_frame(self):
        """显示当前帧"""
        if not self.multi_player:
            return
        
        frames = self.multi_player.read_all_frames()
        
        for widget, frame in zip(self.display_widgets, frames):
            widget.update_frame(frame)
        
        # 更新进度条
        if self.multi_player.players and self.multi_player.players[0]:
            progress = self.multi_player.players[0].get_progress()
            self.progress_slider.setValue(int(progress * 1000))
            
            # 更新时间
            player = self.multi_player.players[0]
            current_time = player.current_frame / player.fps
            total_time = player.total_frames / player.fps
            self.time_label.setText(
                f"{self.format_time(current_time)} / {self.format_time(total_time)}"
            )
    
    def format_time(self, seconds):
        """格式化时间"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def toggle_play(self):
        """切换播放/暂停"""
        if self.is_playing:
            self.stop_playing()
        else:
            self.start_playing()
    
    def start_playing(self):
        """开始播放"""
        if not self.multi_player:
            QMessageBox.warning(self, "警告", "请先加载视频")
            return
        
        self.is_playing = True
        self.btn_play.setText("⏸ 暂停")
        
        # 获取播放速度
        speed_text = self.speed_combo.currentText()
        speed = float(speed_text.replace('x', ''))
        
        # 计算定时器间隔
        fps = self.multi_player.get_average_fps()
        interval = int(1000 / (fps * speed))
        
        self.timer.start(interval)
        self.statusBar().showMessage("播放中...")
    
    def stop_playing(self):
        """停止播放"""
        self.is_playing = False
        self.btn_play.setText("▶ 播放")
        self.timer.stop()
        self.statusBar().showMessage("已暂停")
    
    def update_frame(self):
        """定时器更新帧"""
        if not self.multi_player:
            self.stop_playing()
            return
        
        # 检查是否到达结尾
        if self.multi_player.players and self.multi_player.players[0]:
            player = self.multi_player.players[0]
            if player.current_frame >= player.total_frames - 1:
                self.stop_playing()
                return
        
        self.display_current_frame()
    
    def reset_videos(self):
        """重置视频到开始"""
        if self.multi_player:
            self.stop_playing()
            self.multi_player.reset_all()
            self.display_current_frame()
            self.statusBar().showMessage("已重置到开始")
    
    def prev_video(self):
        """上一个视频"""
        if not self.video_loader or not self.selected_groups:
            return
        
        if self.current_video_index > 0:
            self.current_video_index -= 1
            self.reload_videos_at_index()
    
    def next_video(self):
        """下一个视频"""
        if not self.video_loader or not self.selected_groups:
            return
        
        # 检查是否有下一个
        max_count = max(
            self.video_loader.get_video_count(g) for g in self.selected_groups
        )
        
        if self.current_video_index < max_count - 1:
            self.current_video_index += 1
            self.reload_videos_at_index()
    
    def reload_videos_at_index(self):
        """重新加载指定索引的视频"""
        self.stop_playing()
        
        video_paths = []
        for group_name in self.selected_groups:
            video = self.video_loader.get_video_at_index(
                group_name, self.current_video_index
            )
            video_paths.append(video)
        
        # 填充空位
        while len(video_paths) < len(self.display_widgets):
            video_paths.append(None)
        
        # 关闭旧的播放器
        if self.multi_player:
            self.multi_player.close_all()
        
        # 创建新播放器
        target_height = self.height_spin.value()
        self.multi_player = MultiVideoPlayer(video_paths, target_height)
        
        self.update_video_list()
        self.display_current_frame()
        
        self.statusBar().showMessage(
            f"已加载第 {self.current_video_index + 1} 个视频"
        )
    
    def on_slider_pressed(self):
        """进度条按下"""
        self.stop_playing()
    
    def on_slider_released(self):
        """进度条释放"""
        if not self.multi_player:
            return
        
        # 跳转到指定位置
        progress = self.progress_slider.value() / 1000.0
        max_frames = self.multi_player.get_max_frames()
        frame_number = int(progress * max_frames)
        
        self.multi_player.seek_all(frame_number)
        self.display_current_frame()
    
    def closeEvent(self, event):
        """关闭事件"""
        self.stop_playing()
        if self.multi_player:
            self.multi_player.close_all()
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建主窗口
    window = VideoCompareMainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

