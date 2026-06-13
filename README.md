# CDown - 网易云音乐下载器

一个基于 PyQt6 的网易云音乐下载器，支持高音质下载（最高超清母带）和自动嵌入元数据。

## 功能特点

- ✨ 支持歌单批量下载
- 🎵 支持多种音质（超清母带/Hi-Res/无损/极高/标准）
- 📝 自动嵌入歌词（含翻译）和封面
- ⚡ 多线程并发下载（可配置）
- 💾 断点续传支持
- 🎨 美观的深色主题界面

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行应用

```bash
python main.py
```

## 打包成 EXE

### 方法一：使用 PyInstaller（推荐）

```bash
# 安装 PyInstaller（如果还没安装）
pip install pyinstaller

# 使用配置文件打包
pyinstaller CDown.spec

# 打包完成后，exe 文件位于 dist 目录下
```

### 方法二：手动打包命令

```bash
pyinstaller --name=CDown --onefile --windowed --noconfirm main.py
```

参数说明：
- `--name=CDown`: 生成的 exe 文件名
- `--onefile`: 打包成单个 exe 文件
- `--windowed`: 不显示控制台窗口
- `--noconfirm`: 覆盖已存在的输出文件

### 打包后的文件位置

打包完成后，可执行文件位于 `dist` 目录：
- `dist/CDown.exe` - 可执行文件

## 项目结构

```
CDown/
├── src/                    # 源代码目录
│   ├── __init__.py
│   ├── chksz_api.py       # API 客户端
│   ├── downloader.py      # 下载管理器
│   ├── metadata.py        # 元数据嵌入
│   └── progress_db.py     # 进度数据库
├── data/                   # 数据目录
│   ├── settings.json      # 用户设置
│   └── cdown_progress.db  # 下载进度数据库
├── docs/                   # 文档目录
│   ├── CLAUDE.md          # 项目架构文档
│   └── chksz_api_doc.md   # API 参考文档
├── main.py                 # 主程序入口
├── requirements.txt        # 依赖列表
├── CDown.spec             # PyInstaller 配置
└── README.md              # 本文件
```

## 使用说明

1. 输入网易云音乐歌单 ID（例如：5202687076）
2. 选择保存路径和音质
3. 点击"获取歌单"加载歌曲列表
4. 点击"全部下载"或单独下载某首歌曲
5. 下载完成后，音频文件会自动嵌入封面、歌词等元数据

## 音质说明

- **jymaster (超清母带)**: FLAC 格式，最高音质，需要 SVIP 会员
- **hires (Hi-Res)**: FLAC 24-bit 高解析度
- **lossless (无损)**: FLAC 无损格式
- **exhigh (极高)**: MP3 320kbps
- **standard (标准)**: MP3 128kbps

> 注意：如果账号权限不足，API 会自动降级到可用的最高音质。

## 配置说明

所有配置保存在 `data/settings.json`：

```json
{
  "save_path": "下载保存路径",
  "level": "音质等级",
  "threads": 5,
  "last_playlist": "上次输入的歌单ID",
  "window_width": 1000,
  "window_height": 700
}
```

## 技术栈

- **GUI**: PyQt6
- **HTTP 请求**: requests
- **音频元数据**: mutagen
- **数据库**: SQLite3
- **打包工具**: PyInstaller

## 常见问题

**Q: 打包后的 exe 文件很大怎么办？**
A: 这是正常的，因为包含了 Python 运行环境和所有依赖库。如果需要减小体积，可以使用 `--onedir` 模式打包成文件夹形式。

**Q: 下载失败或无法获取音质？**
A: 可能是账号权限不足或歌曲版权限制，尝试降低音质或更换歌曲。

**Q: 断点续传如何使用？**
A: 程序会自动识别未完成的下载（`.downloading` 文件），重新点击下载即可从断点继续。

## 许可证

本项目仅供学习交流使用，请勿用于商业用途。

## 鸣谢

- API 提供：[ChKSz API](https://api.chksz.top)
- UI 框架：PyQt6
- 元数据处理：mutagen
- [LINUX.DO](https://linux.do)
