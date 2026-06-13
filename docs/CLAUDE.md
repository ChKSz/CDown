# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 最高指令

所有项目相关文档以及你的回答必须使用简体中文！

## 项目概述

CDown 是一个基于 PyQt6 的网易云音乐下载器。它使用 ChKSz API 获取歌单信息，下载高音质音频文件（最高支持 jymaster/超清母带），并将元数据（封面、歌词、翻译）嵌入到下载的文件中。

## 项目结构

```
CDown/
├── src/                    # 源代码目录
│   ├── chksz_api.py       # API 客户端
│   ├── downloader.py      # 下载管理器
│   ├── metadata.py        # 元数据嵌入
│   └── progress_db.py     # 进度数据库
├── data/                   # 数据目录
│   ├── settings.json      # 用户设置
│   └── cdown_progress.db  # 下载进度数据库
├── docs/                   # 文档目录
│   ├── CLAUDE.md          # 本文件
│   └── chksz_api_doc.md   # API 参考文档
├── main.py                 # 主程序入口
├── requirements.txt        # 依赖列表
├── CDown.spec             # PyInstaller 配置
├── run.bat                # 运行脚本
├── build.bat              # 打包脚本
└── README.md              # 项目说明
```

## 开发命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python main.py
# 或使用
run.bat

# 打包成 EXE
pyinstaller CDown.spec
# 或使用
build.bat
```

## 架构说明

### 核心模块

- **main.py**: 主程序入口和 GUI 实现
  - `MainWindow`: 主窗口，管理 UI、歌单加载和下载调度
  - `DownloadManager`: 使用 threading.Semaphore 管理并发下载（可配置线程池大小）
  - Worker 线程: `PlaylistWorker`、`MusicInfoWorker`、`LyricWorker` 用于异步 API 调用
  - 设置持久化: 保存到 `data/settings.json`
  - 数据库: `data/cdown_progress.db` 用于跟踪下载进度

- **src/downloader.py**: 下载执行层
  - `DownloadWorker`: 处理流式下载，支持暂停/继续/取消
  - `DownloadTask`: 数据类，保存下载状态（歌曲信息、URL、进度、状态）
  - 使用 `.downloading` 临时文件支持断点续传，完成后重命名为最终文件

- **src/chksz_api.py**: ChKSz 音乐服务的 API 客户端
  - 基础 URL: `https://api.chksz.top/api`
  - 函数: `get_playlist()`、`get_music_info()`、`get_lyric()`、`download_cover()`、`search_songs()`
  - 音质等级: `jymaster`（超清母带，默认）> `hires` > `lossless` > `exhigh` > `standard`
  - API 详细文档见 `docs/chksz_api_doc.md`

- **src/metadata.py**: 音频元数据嵌入
  - 使用 mutagen 库嵌入标题、艺术家、专辑、封面和歌词
  - 格式特定处理器: `_embed_flac()`、`_embed_mp3()`、`_embed_m4a()`
  - 通过 `parse_lrc_to_uslt()` 将 LRC 格式歌词解析为纯文本

- **src/progress_db.py**: SQLite 持久化层
  - 表 `downloads` 包含歌曲元数据、下载进度和状态字段
  - 状态值: `pending`、`downloading`、`paused`、`completed`、`failed`

### 线程模型

- **下载 worker**: 由 `DownloadManager` 使用信号量控制并发（默认 5 线程）
- **Qt worker**: 独立的 `QThread` 子类用于 API 调用（`PlaylistWorker`、`MusicInfoWorker`、`LyricWorker`），避免阻塞 UI
- **协调机制**: 主线程通过 Qt 信号接收 worker 返回结果并更新 UI

### 下载流程

1. 用户输入歌单 ID → `PlaylistWorker` 从 API 获取歌单
2. GUI 扫描输出目录，查找已存在文件（`.mp3`、`.flac`、`.m4a`）和未完成下载（`.downloading`）
3. 用户点击下载 → `MusicInfoWorker` 解析实际下载 URL 和音质等级
4. `LyricWorker` 并行获取歌词
5. 通过 `download_cover()` 下载封面
6. `DownloadWorker` 流式下载文件并回调进度，保存到 `.downloading` 临时文件
7. 完成后：重命名临时文件，通过 `embed_metadata()` 嵌入元数据
8. 进度每 10% 保存一次到数据库，完成时最终保存

### 文件命名

音频文件命名格式: `{safe_filename(歌曲名 - 艺术家)}.{扩展名}`
- 扩展名: lossless/hires/jymaster 使用 `.flac`，standard/exhigh 使用 `.mp3`
- 安全文件名会将 `<>:"/\|?*` 替换为 `_`

## 音质等级

音质参数对应的格式和比特率:
- `jymaster` (超清母带): FLAC，最高音质，需要 SVIP
- `hires` (Hi-Res): FLAC 24-bit 高解析度
- `lossless` (无损): FLAC 无损
- `exhigh` (极高): MP3 320kbps
- `standard` (标准): MP3 128kbps

如果用户账号权限不足，API 会自动降级到可用音质。

## 设置配置

保存到 `data/settings.json`:
- `save_path`: 下载目录（默认: `~/Music/CDown`）
- `level`: 音质等级（默认: `jymaster (超清母带)`）
- `threads`: 并发下载线程数（默认: 5，范围: 1-20）
- `last_playlist`: 最后输入的歌单 ID
- `window_width`、`window_height`: 窗口尺寸

## 打包说明

### 打包成 EXE

```bash
# 方法一：使用 build.bat（推荐）
build.bat

# 方法二：手动使用 PyInstaller
pyinstaller CDown.spec

# 方法三：命令行直接打包
pyinstaller --name=CDown --onefile --windowed --noconfirm main.py
```

打包后的可执行文件位于 `dist/CDown.exe`
