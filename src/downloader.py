import os
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
import requests


class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DownloadTask:
    song_id: str
    name: str
    artist: str
    album: str
    url: str
    file_path: str
    cover_url: str = ""
    total_size: int = 0
    downloaded: int = 0
    status: DownloadStatus = DownloadStatus.PENDING
    error: str = ""
    level: str = "jymaster"
    lrc: str = ""
    tlyric: str = ""


class DownloadWorker:
    def __init__(
        self,
        task: DownloadTask,
        on_progress: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
    ):
        self.task = task
        self.on_progress = on_progress
        self.on_complete = on_complete
        self._stop_event = threading.Event()
        self._paused = False
        self._lock = threading.Lock()

    def pause(self):
        with self._lock:
            self._paused = True
            self.task.status = DownloadStatus.PAUSED

    def resume(self):
        with self._lock:
            self._paused = False
            self.task.status = DownloadStatus.DOWNLOADING

    def stop(self):
        self._stop_event.set()

    def run(self):
        self.task.status = DownloadStatus.DOWNLOADING
        headers = {}
        temp_file = self.task.file_path + ".downloading"

        if os.path.exists(temp_file):
            self.task.downloaded = os.path.getsize(temp_file)
            headers["Range"] = f"bytes={self.task.downloaded}-"

        try:
            with requests.get(
                self.task.url, headers=headers, stream=True, timeout=30
            ) as resp:
                resp.raise_for_status()

                if self.task.total_size == 0:
                    content_length = resp.headers.get("Content-Length")
                    if content_length:
                        self.task.total_size = (
                            int(content_length) + self.task.downloaded
                        )

                mode = "ab" if self.task.downloaded > 0 else "wb"
                with open(temp_file, mode) as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if self._stop_event.is_set():
                            self.task.status = DownloadStatus.FAILED
                            self.task.error = "Cancelled"
                            return

                        while self._paused:
                            if self._stop_event.is_set():
                                return
                            time.sleep(0.1)

                        if chunk:
                            f.write(chunk)
                            self.task.downloaded += len(chunk)
                            if self.on_progress:
                                self.on_progress(self.task)

            if os.path.exists(temp_file):
                os.rename(temp_file, self.task.file_path)

            self.task.status = DownloadStatus.COMPLETED
            self.task.downloaded = self.task.total_size
            if self.on_complete:
                self.on_complete(self.task)

        except Exception as e:
            self.task.status = DownloadStatus.FAILED
            self.task.error = str(e)
