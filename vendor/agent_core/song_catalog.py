# Vendored from SummerTianYi/anime-agent-mvp services/agent-core/agent_core/song_catalog.py at main-repo commit 746a54f.
# Do not edit freely: changes must be mirrored back through INTEGRATION.md's contract. Protocol-frozen file.
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


MUSIC_QUERY_MARKERS = (
    "歌",
    "曲",
    "唱过",
    "作品",
    "专辑",
    "音乐",
    "producer",
    "p主",
)


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", normalized)


@dataclass(frozen=True, slots=True)
class Song:
    title: str
    aliases: tuple[str, ...]
    vocalists: tuple[str, ...]
    creators: tuple[str, ...]
    release_year: int | None
    album: str
    tags: tuple[str, ...]
    significance: str
    sources: tuple[str, ...]
    representative_rank: int
    original: bool

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Song":
        return cls(
            title=str(payload["title"]),
            aliases=tuple(str(value) for value in payload.get("aliases", [])),
            vocalists=tuple(str(value) for value in payload.get("vocalists", [])),
            creators=tuple(str(value) for value in payload.get("creators", [])),
            release_year=(
                int(payload["release_year"])
                if payload.get("release_year") is not None
                else None
            ),
            album=str(payload.get("album", "")),
            tags=tuple(str(value) for value in payload.get("tags", [])),
            significance=str(payload.get("significance", "")),
            sources=tuple(str(value) for value in payload.get("sources", [])),
            representative_rank=int(payload.get("representative_rank", 9999)),
            original=bool(payload.get("original", False)),
        )

    def prompt_line(self) -> str:
        parts = [f"《{self.title}》"]
        if self.creators:
            parts.append(f"创作者：{'、'.join(self.creators)}")
        if self.vocalists:
            parts.append(f"演唱：{'、'.join(self.vocalists)}")
        if self.release_year:
            parts.append(f"发行/投稿年份：{self.release_year}")
        if self.album:
            parts.append(f"专辑：{self.album}")
        if self.significance:
            parts.append(self.significance)
        return "；".join(parts)


class SongCatalog:
    def __init__(self, path: Path | None = None) -> None:
        catalog_path = path or Path(__file__).with_name("data") / "luotianyi_original_songs.json"
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.songs = tuple(
            song
            for song in (Song.from_dict(item) for item in payload)
            if song.original
        )

    def search(self, query: str, limit: int = 6) -> list[Song]:
        normalized_query = _normalize(query)
        if not normalized_query:
            return []

        scored: list[tuple[int, Song]] = []
        for song in self.songs:
            score = self._score(song, normalized_query)
            if score > 0:
                scored.append((score, song))

        if not scored and self._is_music_query(query):
            return sorted(self.songs, key=lambda item: item.representative_rank)[:limit]

        scored.sort(key=lambda item: (-item[0], item[1].representative_rank))
        return [song for _, song in scored[:limit]]

    @staticmethod
    def _is_music_query(query: str) -> bool:
        lowered = query.casefold()
        return any(marker in lowered for marker in MUSIC_QUERY_MARKERS)

    @staticmethod
    def _score(song: Song, query: str) -> int:
        title = _normalize(song.title)
        if title and title in query:
            return 120

        alias_score = max(
            (100 for alias in song.aliases if _normalize(alias) in query),
            default=0,
        )
        creator_score = max(
            (45 for creator in song.creators if _normalize(creator) in query),
            default=0,
        )
        tag_score = sum(
            12
            for tag in song.tags
            if tag not in {"原创", "代表作"} and _normalize(tag) in query
        )
        return alias_score + creator_score + tag_score

    @staticmethod
    def format_context(songs: list[Song]) -> str:
        if not songs:
            return ""
        lines = ["以下是与本轮问题相关、已经过本地资料库核验的原创歌曲信息："]
        lines.extend(f"- {song.prompt_line()}" for song in songs)
        lines.append("只能依据这些资料陈述具体作者、年份和版本；资料未覆盖时应坦率说明记不准。")
        return "\n".join(lines)
