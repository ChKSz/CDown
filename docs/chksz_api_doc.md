# ChKSz API 快速参考文档

网易云音乐相关接口，四个核心 API 的用法、请求地址、参数说明及返回格式。

---

## 音质等级参考（level 参数）

适用于音乐解析接口的 `level` 参数：

| level | 名称 | 说明 |
| :--- | :--- | :--- |
| `standard` | 标准音质 | 128kbps MP3 |
| `exhigh` | 极高音质（HQ） | 320kbps MP3 |
| `lossless` | 无损音质 | FLAC |
| `hires` | Hi-Res 音质 | FLAC 24bit 高解析度 |
| `jyeffect` | 高清环绕声 | 空间音频效果 |
| `sky` | 沉浸环绕声 | 杜比全景声效果（Dolby Atmos） |
| `jymaster` | 超清母带 | 最高音质，需 SVIP 会员（**默认值**） |

> 若账号权限不足，网易云 API 会自动降级返回可用音质。

---

### 1. 网易云搜索歌曲 API

用于通过关键词快速检索网易云曲库，支持分页查询，返回标准化的歌曲列表信息。

- **请求地址**: `https://api.chksz.top/api/163_search`
- **请求方式**: GET / POST
- **返回格式**: JSON
- **调用权限**: 公共/免费

**请求参数:**

| 参数名 | 必选 | 类型 | 说明 |
| :--- | :---: | :--- | :--- |
| `keyword` | **是** | string | 搜索关键词 (例如: 陈奕迅) |
| `limit` | 否 | int | 返回数量 (默认 100) |
| `offset` | 否 | int | 偏移量 (默认 0) |

**请求示例:**

```http
GET https://api.chksz.top/api/163_search?keyword=陈奕迅&limit=3
```

**返回示例:**

```json
{
    "code": 200,
    "msg": "success",
    "data": {
        "songs": [
            {
                "id": 1315196858,
                "name": "海底",
                "artists": "一支榴莲",
                "album": "独",
                "picUrl": "https://p1.music.126.net/...",
                "duration": 234000
            }
        ],
        "total": 100
    }
}
```

---

### 2. 网易SVIP音乐信息解析 API

用于解析网易云音乐的音频播放地址及歌曲信息，最高支持超清母带（jymaster）音质（由赞助SVIP会员提供支持）。

- **请求地址**: `https://api.chksz.top/api/163_music`
- **请求方式**: GET / POST
- **返回格式**: JSON / Text / audio
- **调用权限**: 公共/免费

**请求参数:**

| 参数名 | 必选 | 类型 | 说明 |
| :--- | :---: | :--- | :--- |
| `id` | **是** | string | 网易云歌曲ID (例如: 1315196858) |
| `level` | 否 | string | 音质等级，默认 `jymaster`。可选值见上方音质等级表 |
| `type` | 否 | string | 返回类型，默认 `json`。可选值: `json`、`text`、`down` |

**type 参数说明:**

| type | 说明 |
| :--- | :--- |
| `json` | 返回 JSON 格式完整信息（默认） |
| `text` | 仅返回纯文本音频 URL |
| `down` | 302 跳转到音频地址，可直接播放或下载 |

**请求示例:**

```http
GET https://api.chksz.top/api/163_music?id=1315196858
GET https://api.chksz.top/api/163_music?id=1315196858&level=lossless
GET https://api.chksz.top/api/163_music?id=1315196858&type=text
GET https://api.chksz.top/api/163_music?id=1315196858&type=down
```

**JSON 返回示例:**

```json
{
    "code": 200,
    "msg": "success",
    "data": {
        "id": 1315196858,
        "url": "https://m801.music.126.net/20260124123456/...",
        "br": 999000,
        "level": "jymaster",
        "size": 34567890,
        "md5": "a1b2c3d4e5f6...",
        "name": "海底",
        "artist": "一支榴莲",
        "album": "独",
        "picUrl": "https://p1.music.126.net/..."
    }
}
```

---

### 3. 网易云歌词获取 API

通过输入歌曲ID，获取该歌曲的歌词以及翻译歌词。

- **请求地址**: `https://api.chksz.top/api/163_lyric`
- **请求方式**: GET / POST
- **返回格式**: JSON
- **调用权限**: 公共/免费

**请求参数:**

| 参数名 | 必选 | 类型 | 说明 |
| :--- | :---: | :--- | :--- |
| `id` | **是** | string | 歌曲 ID (例如: 1315196858) |

**请求示例:**

```http
GET https://api.chksz.top/api/163_lyric?id=1315196858
```

**返回示例:**

```json
{
    "code": 200,
    "msg": "success",
    "data": {
        "lrc": "[00:00.00] 作曲 : 柏林护士...",
        "tlyric": "...",
        "romalrc": "...",
        "klyric": ""
    }
}
```

---

### 4. 网易云歌单详情 API

通过歌单ID，获取网易云音乐歌单的详细信息，包括歌单封面、创作者信息以及完整歌曲列表。

- **请求地址**: `https://api.chksz.top/api/163_playlist`
- **请求方式**: GET / POST
- **返回格式**: JSON
- **调用权限**: 公共/免费

**请求参数:**

| 参数名 | 必选 | 类型 | 说明 |
| :--- | :---: | :--- | :--- |
| `id` | **是** | string | 网易云歌单ID (例如: 5202687076) |

**请求示例:**

```http
GET https://api.chksz.top/api/163_playlist?id=5202687076
```

**返回示例:**

```json
{
    "data": {
        "id": 5202687076,
        "name": "歌单名称",
        "coverImgUrl": "https://p1.music.126.net/...",
        "trackCount": 100,
        "creator": {
            "nickname": "创建者昵称"
        },
        "tracks": [
            {
                "id": 123456,
                "name": "歌曲名称",
                "ar": [
                    { "name": "歌手" }
                ],
                "al": {
                    "name": "专辑名称",
                    "picUrl": "https://p1.music.126.net/..."
                }
            }
        ]
    }
}
```
