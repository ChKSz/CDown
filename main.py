import os
import sys
import json
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QProgressBar,
    QFileDialog,
    QMessageBox,
    QComboBox,
    QSpinBox,
    QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from src import chksz_api
from src.chksz_api import get_playlist, get_music_info, get_lyric, download_cover
from src.downloader import DownloadTask, DownloadStatus, DownloadWorker
from src.metadata import embed_metadata
from src.progress_db import ProgressDB


APP_NAME = "CDown"
APP_VERSION = "1.0.0"
SETTINGS_FILE = str(Path(__file__).parent / "data" / "settings.json")


def load_settings() -> dict:
    defaults = {
        "save_path": str(Path.home() / "Music" / "CDown"),
        "level": "jymaster (超清母带)",
        "threads": 5,
        "last_playlist": "",
        "window_width": 1000,
        "window_height": 700,
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                defaults.update(saved)
        except Exception:
            pass
    return defaults


def save_settings(**kwargs):
    current = load_settings()
    current.update(kwargs)
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class PlaylistWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, playlist_id: str):
        super().__init__()
        self.playlist_id = playlist_id

    def run(self):
        try:
            resp = get_playlist(self.playlist_id)
            if resp.get("code") == 200 or "data" in resp:
                data = resp.get("data", resp)
                tracks = data.get("tracks", [])
                playlist_name = data.get("name", "Unknown")
                creator = data.get("creator", {}).get("nickname", "Unknown")
                cover_url = data.get("coverImgUrl", "")
                self.finished.emit(
                    [
                        {
                            "playlist_name": playlist_name,
                            "creator": creator,
                            "cover_url": cover_url,
                            "tracks": tracks,
                        }
                    ]
                )
            else:
                self.error.emit(resp.get("msg", "获取歌单失败"))
        except Exception as e:
            self.error.emit(str(e))


class MusicInfoWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, song_id: str, level: str):
        super().__init__()
        self.song_id = song_id
        self.level = level

    def run(self):
        try:
            resp = get_music_info(self.song_id, self.level)
            if resp.get("code") == 200 and "data" in resp:
                self.finished.emit(resp["data"])
            else:
                self.error.emit(resp.get("msg", "获取音乐信息失败"))
        except Exception as e:
            self.error.emit(str(e))


class LyricWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, song_id: str):
        super().__init__()
        self.song_id = song_id

    def run(self):
        try:
            resp = get_lyric(self.song_id)
            if resp.get("code") == 200 and "data" in resp:
                self.finished.emit(resp["data"])
            else:
                self.finished.emit({})
        except Exception:
            self.finished.emit({})


class DownloadManager:
    def __init__(self, max_threads: int = 5):
        self.max_threads = max_threads
        self.workers = {}
        self.lock = threading.Lock()
        self.semaphore = threading.Semaphore(max_threads)

    def add_task(self, task: DownloadTask, on_progress, on_complete):
        self.semaphore.acquire()
        worker = DownloadWorker(task, on_progress, on_complete)
        with self.lock:
            self.workers[task.song_id] = worker
        thread = threading.Thread(target=self._run_worker, args=(worker,), daemon=True)
        thread.start()

    def _run_worker(self, worker: DownloadWorker):
        try:
            worker.run()
        finally:
            with self.lock:
                self.workers.pop(worker.task.song_id, None)
            self.semaphore.release()

    def pause_task(self, song_id: str):
        with self.lock:
            worker = self.workers.get(song_id)
            if worker:
                worker.pause()

    def resume_task(self, song_id: str):
        with self.lock:
            worker = self.workers.get(song_id)
            if worker:
                worker.resume()

    def cancel_task(self, song_id: str):
        with self.lock:
            worker = self.workers.get(song_id)
            if worker:
                worker.stop()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.db = ProgressDB(str(Path(__file__).parent / "data" / "cdown_progress.db"))
        self.download_manager = DownloadManager(max_threads=self.settings["threads"])
        self.tasks = {}
        self.current_cover_data = {}

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(900, 600)
        self.resize(
            self.settings.get("window_width", 1000),
            self.settings.get("window_height", 700),
        )
        self.setStyleSheet(self._get_stylesheet())
        self._setup_ui()
        self._apply_settings()

    def closeEvent(self, event):
        save_settings(
            save_path=self._get_save_path(),
            level=self.level_combo.currentText(),
            threads=self.thread_spin.value(),
            last_playlist=self.playlist_input.text().strip(),
            window_width=self.width(),
            window_height=self.height(),
        )
        super().closeEvent(event)

    def _get_stylesheet(self):
        return """
            QMainWindow {
                background-color: #1a1a2e;
            }
            QWidget {
                background-color: #1a1a2e;
                color: #e0e0e0;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                font-size: 13px;
            }
            QLabel {
                color: #e0e0e0;
                background: transparent;
            }
            QLabel.title {
                font-size: 28px;
                font-weight: bold;
                color: #00d4ff;
            }
            QLabel.status {
                color: #8892a4;
                font-size: 12px;
            }
            QLabel.progress-text {
                color: #00d4ff;
                font-size: 13px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 20px;
                padding: 10px 18px;
                color: #e0e0e0;
                font-size: 13px;
                selection-background-color: #00d4ff;
                selection-color: #1a1a2e;
            }
            QLineEdit:focus {
                border-color: #00d4ff;
            }
            QPushButton {
                background-color: #0f3460;
                border: none;
                border-radius: 20px;
                padding: 10px 24px;
                color: #e0e0e0;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1a4a7a;
            }
            QPushButton:pressed {
                background-color: #0a2a50;
            }
            QPushButton:disabled {
                background-color: #0a1a30;
                color: #4a5568;
            }
            QPushButton.primary {
                background-color: #00d4ff;
                color: #1a1a2e;
            }
            QPushButton.primary:hover {
                background-color: #00b8e6;
            }
            QPushButton.primary:pressed {
                background-color: #0099cc;
            }
            QPushButton.danger {
                background-color: #e94560;
                color: white;
            }
            QPushButton.danger:hover {
                background-color: #c73e54;
            }
            QPushButton.success {
                background-color: #00c853;
                color: white;
            }
            QPushButton.success:hover {
                background-color: #00a844;
            }
            QComboBox {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 20px;
                padding: 10px 18px;
                color: #e0e0e0;
            }
            QComboBox:hover {
                border-color: #00d4ff;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 14px;
            }
            QComboBox QAbstractItemView {
                background-color: #16213e;
                color: #e0e0e0;
                selection-background-color: #0f3460;
                border: 1px solid #0f3460;
                border-radius: 12px;
                outline: none;
            }
            QSpinBox {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 20px;
                padding: 10px 18px;
                color: #e0e0e0;
            }
            QSpinBox:hover {
                border-color: #00d4ff;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #0f3460;
                border: none;
                border-radius: 10px;
                width: 20px;
                margin: 2px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #1a4a7a;
            }
            QTableWidget {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 16px;
                gridline-color: #0f3460;
                selection-background-color: #0f3460;
            }
            QTableWidget::item {
                padding: 8px;
                border-radius: 0;
            }
            QHeaderView::section {
                background-color: #0f3460;
                color: #00d4ff;
                padding: 12px;
                border: none;
                font-weight: bold;
                border-radius: 0;
            }
            QProgressBar {
                background-color: #0f3460;
                border-radius: 10px;
                height: 10px;
                text-align: center;
                color: transparent;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #00d4ff;
                border-radius: 10px;
            }
            QFrame.card {
                background-color: #16213e;
                border-radius: 20px;
                border: 1px solid #0f3460;
            }
            QScrollBar:vertical {
                background-color: #16213e;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #0f3460;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #1a4a7a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QMessageBox {
                background-color: #16213e;
            }
            QMessageBox QLabel {
                color: #e0e0e0;
            }
            QMessageBox QPushButton {
                min-width: 80px;
            }
        """

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        title = QLabel(f"{APP_NAME}")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        input_card = QFrame()
        input_card.setObjectName("card")
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(24, 20, 24, 20)
        input_layout.setSpacing(14)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("歌单ID:"))
        self.playlist_input = QLineEdit()
        self.playlist_input.setPlaceholderText("输入网易云歌单ID，例如: 5202687076")
        self.playlist_input.returnPressed.connect(self.fetch_playlist)
        row1.addWidget(self.playlist_input)

        self.fetch_btn = QPushButton("获取歌单")
        self.fetch_btn.setObjectName("primary")
        self.fetch_btn.clicked.connect(self.fetch_playlist)
        row1.addWidget(self.fetch_btn)
        input_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("保存路径:"))
        self.save_path_input = QLineEdit()
        self.save_path_input.setReadOnly(True)
        row2.addWidget(self.save_path_input)

        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.browse_folder)
        row2.addWidget(browse_btn)
        input_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("音质:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(
            [
                "jymaster (超清母带)",
                "hires (Hi-Res)",
                "lossless (无损)",
                "exhigh (极高)",
                "standard (标准)",
            ]
        )
        self.level_combo.currentTextChanged.connect(self._on_setting_changed)
        row3.addWidget(self.level_combo)

        row3.addWidget(QLabel("线程数:"))
        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 20)
        self.thread_spin.setValue(5)
        self.thread_spin.valueChanged.connect(self._on_setting_changed)
        row3.addWidget(self.thread_spin)

        row3.addStretch()
        input_layout.addLayout(row3)

        main_layout.addWidget(input_card)

        stats_row = QHBoxLayout()
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("status")
        stats_row.addWidget(self.status_label)
        stats_row.addStretch()
        self.progress_label = QLabel("0 / 0")
        self.progress_label.setObjectName("progress-text")
        stats_row.addWidget(self.progress_label)
        main_layout.addLayout(stats_row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["#", "歌曲", "歌手", "专辑", "进度", "操作"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Fixed
        )
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(5, 180)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        main_layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.download_all_btn = QPushButton("全部下载")
        self.download_all_btn.setObjectName("primary")
        self.download_all_btn.clicked.connect(self.download_all)
        btn_row.addWidget(self.download_all_btn)

        self.pause_all_btn = QPushButton("全部暂停")
        self.pause_all_btn.clicked.connect(self.pause_all)
        btn_row.addWidget(self.pause_all_btn)

        self.clear_btn = QPushButton("清除已完成")
        self.clear_btn.clicked.connect(self.clear_completed)
        btn_row.addWidget(self.clear_btn)

        btn_row.addStretch()
        main_layout.addLayout(btn_row)

    def _apply_settings(self):
        self.save_path_input.setText(self.settings["save_path"])
        idx = self.level_combo.findText(self.settings["level"])
        if idx >= 0:
            self.level_combo.setCurrentIndex(idx)
        self.thread_spin.setValue(self.settings["threads"])
        if self.settings["last_playlist"]:
            self.playlist_input.setText(self.settings["last_playlist"])

    def _on_setting_changed(self):
        save_settings(
            save_path=self._get_save_path(),
            level=self.level_combo.currentText(),
            threads=self.thread_spin.value(),
            last_playlist=self.playlist_input.text().strip(),
        )

    def _update_threads(self, value):
        self.download_manager.max_threads = value

    def browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "选择保存路径")
        if path:
            self.save_path_input.setText(path)
            self._on_setting_changed()

    def fetch_playlist(self):
        playlist_id = self.playlist_input.text().strip()
        if not playlist_id:
            QMessageBox.warning(self, "提示", "请输入歌单ID")
            return

        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("获取中...")
        self.status_label.setText("正在获取歌单...")

        self.worker = PlaylistWorker(playlist_id)
        self.worker.finished.connect(self._on_playlist_loaded)
        self.worker.error.connect(self._on_playlist_error)
        self.worker.start()

    def _scan_folder_for_existing(self, save_path: str, tracks: list) -> dict:
        existing = {}
        if not os.path.exists(save_path):
            return existing

        files = os.listdir(save_path)
        completed_names = set()
        downloading_names = {}

        for f in files:
            if f.endswith(".downloading"):
                base_name = f[: -len(".downloading")]
                downloading_names[base_name] = os.path.getsize(
                    os.path.join(save_path, f)
                )
            elif f.endswith((".mp3", ".flac", ".m4a")):
                base_name = os.path.splitext(f)[0]
                completed_names.add(base_name)

        for track in tracks:
            song_id = str(track["id"])
            name = track["name"]
            artists = " / ".join([a.get("name", "") for a in track.get("ar", [])])
            safe_name = self._safe_filename(f"{name} - {artists}")

            if safe_name in completed_names:
                existing[song_id] = "completed"
            elif safe_name in downloading_names:
                existing[song_id] = downloading_names[safe_name]

        return existing

    def _on_playlist_loaded(self, data_list):
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("获取歌单")

        if not data_list:
            self.status_label.setText("歌单为空")
            return

        data = data_list[0]
        tracks = data["tracks"]
        playlist_name = data["playlist_name"]

        self.status_label.setText(f"歌单: {playlist_name} ({len(tracks)} 首)")
        self.table.setRowCount(0)

        save_path = self._get_save_path()
        existing = self._scan_folder_for_existing(save_path, tracks)

        completed_count = 0
        downloading_count = 0

        for i, track in enumerate(tracks):
            row = self.table.rowCount()
            self.table.insertRow(row)

            song_id = str(track["id"])
            name = track["name"]
            artists = " / ".join([a.get("name", "") for a in track.get("ar", [])])
            album = track.get("al", {}).get("name", "")
            pic_url = track.get("al", {}).get("picUrl", "")

            self.table.setItem(row, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(row, 1, QTableWidgetItem(name))
            self.table.setItem(row, 2, QTableWidgetItem(artists))
            self.table.setItem(row, 3, QTableWidgetItem(album))

            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            self.table.setCellWidget(row, 4, progress_bar)

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)

            task = DownloadTask(
                song_id=song_id,
                name=name,
                artist=artists,
                album=album,
                url="",
                file_path="",
                cover_url=pic_url,
            )

            if song_id in existing:
                status = existing[song_id]
                if status == "completed":
                    task.status = DownloadStatus.COMPLETED
                    progress_bar.setValue(100)
                    label = QLabel("已存在")
                    label.setStyleSheet("color: #00c853;")
                    btn_layout.addWidget(label)
                    completed_count += 1
                else:
                    task.status = DownloadStatus.PENDING
                    task.downloaded = status
                    progress_label = QLabel("可续传")
                    progress_label.setStyleSheet("color: #ffa726;")
                    btn_layout.addWidget(progress_label)
                    dl_btn = QPushButton("续传")
                    dl_btn.setObjectName("primary")
                    dl_btn.clicked.connect(
                        lambda checked, sid=song_id, n=name, a=artists, al=album, pu=pic_url: (
                            self.download_single(sid, n, a, al, pu)
                        )
                    )
                    btn_layout.addWidget(dl_btn)
                    downloading_count += 1
            else:
                progress_bar.setValue(0)
                dl_btn = QPushButton("下载")
                dl_btn.setObjectName("primary")
                dl_btn.clicked.connect(
                    lambda checked, sid=song_id, n=name, a=artists, al=album, pu=pic_url: (
                        self.download_single(sid, n, a, al, pu)
                    )
                )
                btn_layout.addWidget(dl_btn)

            self.table.setCellWidget(row, 5, btn_widget)
            self.tasks[song_id] = task

        self.progress_label.setText(f"{completed_count} / {len(tracks)}")

        if completed_count > 0 or downloading_count > 0:
            self.status_label.setText(
                f"歌单: {playlist_name} | 已存在: {completed_count} | 可续传: {downloading_count} | 待下载: {len(tracks) - completed_count - downloading_count}"
            )

    def _on_playlist_error(self, error):
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("获取歌单")
        self.status_label.setText(f"错误: {error}")
        QMessageBox.critical(self, "错误", f"获取歌单失败: {error}")

    def _get_level(self) -> str:
        level_map = {
            "jymaster (超清母带)": "jymaster",
            "hires (Hi-Res)": "hires",
            "lossless (无损)": "lossless",
            "exhigh (极高)": "exhigh",
            "standard (标准)": "standard",
        }
        return level_map.get(self.level_combo.currentText(), "jymaster")

    def _get_save_path(self) -> str:
        return self.save_path_input.text().strip()

    def download_single(self, song_id, name, artist, album, cover_url):
        task = self.tasks.get(song_id)
        if not task:
            return

        if task.status in (DownloadStatus.DOWNLOADING, DownloadStatus.PENDING):
            return

        level = self._get_level()
        save_path = self._get_save_path()

        self._resolve_and_download(task, level, save_path)

    def _resolve_and_download(self, task: DownloadTask, level: str, save_path: str):
        def on_music_info(data):
            url = data.get("url", "")
            if not url:
                task.status = DownloadStatus.FAILED
                task.error = "无法获取下载链接"
                self._update_task_ui(task)
                return

            task.url = url
            task.level = data.get("level", level)
            task.total_size = data.get("size", 0)

            ext = (
                ".flac"
                if task.level in ("lossless", "hires", "jymaster", "jyeffect", "sky")
                else ".mp3"
            )
            safe_name = self._safe_filename(f"{task.name} - {task.artist}")
            task.file_path = os.path.join(save_path, f"{safe_name}{ext}")

            os.makedirs(save_path, exist_ok=True)

            lyric_worker = LyricWorker(task.song_id)
            lyric_worker.finished.connect(lambda lrc: self._on_lyric_loaded(task, lrc))
            lyric_worker.start()

            cover_data = download_cover(task.cover_url) if task.cover_url else None
            if cover_data:
                self.current_cover_data[task.song_id] = cover_data

            self.download_manager.add_task(
                task,
                on_progress=self._on_progress,
                on_complete=self._on_complete,
            )
            self._update_task_ui(task)
            self.db.save_task(task)

        def on_error(error):
            task.status = DownloadStatus.FAILED
            task.error = error
            self._update_task_ui(task)

        worker = MusicInfoWorker(task.song_id, level)
        worker.finished.connect(on_music_info)
        worker.error.connect(on_error)
        worker.start()

    def _on_lyric_loaded(self, task: DownloadTask, lrc_data: dict):
        task.lrc = lrc_data.get("lrc", "")
        task.tlyric = lrc_data.get("tlyric", "")

    def _safe_filename(self, name: str) -> str:
        for ch in r'<>:"/\|?*':
            name = name.replace(ch, "_")
        return name.strip()

    def download_all(self):
        save_path = self._get_save_path()
        level = self._get_level()

        pending_count = 0
        for song_id, task in self.tasks.items():
            if task.status in (DownloadStatus.PENDING, DownloadStatus.FAILED):
                self._resolve_and_download(task, level, save_path)
                pending_count += 1

        if pending_count == 0:
            QMessageBox.information(self, "提示", "没有可下载的歌曲")

    def pause_all(self):
        for song_id, task in self.tasks.items():
            if task.status == DownloadStatus.DOWNLOADING:
                self.download_manager.pause_task(song_id)
                self._update_task_ui(task)

    def clear_completed(self):
        completed = [
            sid for sid, t in self.tasks.items() if t.status == DownloadStatus.COMPLETED
        ]
        for sid in completed:
            del self.tasks[sid]

        for row in range(self.table.rowCount() - 1, -1, -1):
            item = self.table.item(row, 0)
            if item:
                song_id = None
                for sid, t in self.tasks.items():
                    if t.name == self.table.item(row, 1).text():
                        song_id = sid
                        break
                if song_id is None:
                    self.table.removeRow(row)

        self.db.clear_completed()
        self._update_stats()

    def _update_task_ui(self, task: DownloadTask):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item and item.text() == task.name:
                progress_bar = self.table.cellWidget(row, 4)
                btn_widget = self.table.cellWidget(row, 5)

                if isinstance(progress_bar, QProgressBar):
                    if task.status == DownloadStatus.COMPLETED:
                        progress_bar.setValue(100)
                    elif task.status == DownloadStatus.FAILED:
                        progress_bar.setValue(0)
                    elif task.total_size > 0:
                        progress_bar.setValue(
                            int(task.downloaded / task.total_size * 100)
                        )

                if isinstance(btn_widget, QWidget):
                    btn_layout = btn_widget.layout()
                    if btn_layout:
                        while btn_layout.count():
                            child = btn_layout.takeAt(0)
                            if child.widget():
                                child.widget().deleteLater()

                        if task.status == DownloadStatus.DOWNLOADING:
                            pause_btn = QPushButton("暂停")
                            pause_btn.clicked.connect(
                                lambda checked, sid=task.song_id: self._pause_task(sid)
                            )
                            btn_layout.addWidget(pause_btn)
                        elif task.status == DownloadStatus.PAUSED:
                            resume_btn = QPushButton("继续")
                            resume_btn.setObjectName("success")
                            resume_btn.clicked.connect(
                                lambda checked, sid=task.song_id: self._resume_task(sid)
                            )
                            btn_layout.addWidget(resume_btn)
                        elif task.status == DownloadStatus.COMPLETED:
                            label = QLabel("已完成")
                            label.setStyleSheet("color: #00c853;")
                            btn_layout.addWidget(label)
                        elif task.status == DownloadStatus.FAILED:
                            retry_btn = QPushButton("重试")
                            retry_btn.setObjectName("danger")
                            retry_btn.clicked.connect(
                                lambda checked, sid=task.song_id: self._retry_task(sid)
                            )
                            btn_layout.addWidget(retry_btn)
                        else:
                            dl_btn = QPushButton("下载")
                            dl_btn.setObjectName("primary")
                            dl_btn.clicked.connect(
                                lambda checked, sid=task.song_id: self._start_task(sid)
                            )
                            btn_layout.addWidget(dl_btn)

                break

        self._update_stats()

    def _pause_task(self, song_id):
        self.download_manager.pause_task(song_id)
        task = self.tasks.get(song_id)
        if task:
            self._update_task_ui(task)
            self.db.save_task(task)

    def _resume_task(self, song_id):
        self.download_manager.resume_task(song_id)
        task = self.tasks.get(song_id)
        if task:
            self._update_task_ui(task)
            self.db.save_task(task)

    def _retry_task(self, song_id):
        task = self.tasks.get(song_id)
        if task:
            task.status = DownloadStatus.PENDING
            task.error = ""
            task.downloaded = 0
            task.total_size = 0
            level = self._get_level()
            save_path = self._get_save_path()
            self._resolve_and_download(task, level, save_path)

    def _start_task(self, song_id):
        task = self.tasks.get(song_id)
        if task:
            level = self._get_level()
            save_path = self._get_save_path()
            self._resolve_and_download(task, level, save_path)

    def _on_progress(self, task: DownloadTask):
        self._update_task_ui(task)
        if task.total_size > 0:
            progress = task.downloaded / task.total_size * 100
            if int(progress) % 10 == 0:
                self.db.save_task(task)

    def _on_complete(self, task: DownloadTask):
        save_path = self._get_save_path()
        file_path = task.file_path

        if os.path.exists(file_path):
            try:
                cover_data = self.current_cover_data.get(task.song_id)
                embed_metadata(
                    file_path,
                    name=task.name,
                    artist=task.artist,
                    album=task.album,
                    cover_data=cover_data,
                    lrc_text=task.lrc,
                    tlyric_text=task.tlyric,
                )
            except Exception as e:
                print(f"嵌入标签失败 {task.name}: {e}")

        self._update_task_ui(task)
        self.db.save_task(task)
        self._update_stats()

    def _update_stats(self):
        total = len(self.tasks)
        completed = sum(
            1 for t in self.tasks.values() if t.status == DownloadStatus.COMPLETED
        )
        downloading = sum(
            1 for t in self.tasks.values() if t.status == DownloadStatus.DOWNLOADING
        )
        failed = sum(
            1 for t in self.tasks.values() if t.status == DownloadStatus.FAILED
        )

        self.progress_label.setText(f"{completed} / {total}")

        status_parts = []
        if downloading > 0:
            status_parts.append(f"{downloading} 下载中")
        if failed > 0:
            status_parts.append(f"{failed} 失败")
        if completed > 0:
            status_parts.append(f"{completed} 完成")

        if status_parts:
            self.status_label.setText(" | ".join(status_parts))
        else:
            self.status_label.setText("就绪")


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
