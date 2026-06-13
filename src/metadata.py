import os
import re
from typing import Optional
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, USLT, TIT2, TPE1, TALB
from mutagen.mp4 import MP4
from mutagen import File as MutagenFile


def parse_lrc_to_uslt(lrc_text: str) -> str:
    if not lrc_text:
        return ""
    lines = lrc_text.strip().split("\n")
    cleaned = []
    for line in lines:
        cleaned.append(re.sub(r"\[\d{2}:\d{2}\.\d{2,}\]\s*", "", line))
    return "\n".join(cleaned)


def embed_metadata(
    file_path: str,
    name: str,
    artist: str,
    album: str,
    cover_data: Optional[bytes] = None,
    lrc_text: Optional[str] = None,
    tlyric_text: Optional[str] = None,
):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".flac":
        _embed_flac(file_path, name, artist, album, cover_data, lrc_text, tlyric_text)
    elif ext == ".mp3":
        _embed_mp3(file_path, name, artist, album, cover_data, lrc_text, tlyric_text)
    elif ext in (".m4a", ".mp4"):
        _embed_m4a(file_path, name, artist, album, cover_data, lrc_text, tlyric_text)
    else:
        audio = MutagenFile(file_path, easy=True)
        if audio is not None:
            audio["title"] = name
            audio["artist"] = artist
            audio["album"] = album
            audio.save()


def _embed_flac(
    file_path: str,
    name: str,
    artist: str,
    album: str,
    cover_data: Optional[bytes] = None,
    lrc_text: Optional[str] = None,
    tlyric_text: Optional[str] = None,
):
    audio = FLAC(file_path)
    audio["title"] = name
    audio["artist"] = artist
    audio["album"] = album

    if lrc_text:
        audio["lyrics"] = parse_lrc_to_uslt(lrc_text)
    if tlyric_text:
        existing = audio.get("lyrics", [""])[0]
        audio["lyrics"] = [
            existing + "\n\n--- Translation ---\n" + parse_lrc_to_uslt(tlyric_text)
        ]

    if cover_data:
        pic = Picture()
        pic.type = 3
        pic.mime = "image/jpeg"
        pic.desc = "Cover"
        pic.data = cover_data
        audio.clear_pictures()
        audio.add_picture(pic)

    audio.save()


def _embed_mp3(
    file_path: str,
    name: str,
    artist: str,
    album: str,
    cover_data: Optional[bytes] = None,
    lrc_text: Optional[str] = None,
    tlyric_text: Optional[str] = None,
):
    try:
        audio = ID3(file_path)
    except Exception:
        audio = ID3()

    audio["TIT2"] = TIT2(encoding=3, text=name)
    audio["TPE1"] = TPE1(encoding=3, text=artist)
    audio["TALB"] = TALB(encoding=3, text=album)

    if lrc_text:
        lyrics_text = parse_lrc_to_uslt(lrc_text)
        if tlyric_text:
            lyrics_text += "\n\n--- Translation ---\n" + parse_lrc_to_uslt(tlyric_text)
        audio["USLT"] = USLT(encoding=3, lang="chi", desc="", text=lyrics_text)

    if cover_data:
        audio["APIC"] = APIC(
            encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover_data
        )

    audio.save(file_path)


def _embed_m4a(
    file_path: str,
    name: str,
    artist: str,
    album: str,
    cover_data: Optional[bytes] = None,
    lrc_text: Optional[str] = None,
    tlyric_text: Optional[str] = None,
):
    audio = MP4(file_path)
    audio["\xa9nam"] = name
    audio["\xa9ART"] = artist
    audio["\xa9alb"] = album

    if lrc_text:
        audio["\xa9lyr"] = parse_lrc_to_uslt(lrc_text)

    if cover_data:
        from mutagen.mp4 import MP4Cover

        audio["covr"] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]

    audio.save()
