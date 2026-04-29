import os
import json
import io
import re
import time
import asyncio
import random
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import aiohttp
import psutil
import discord
from discord.ext import commands, tasks
from discord import app_commands
import google.generativeai as genai
from flask import Flask, jsonify

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('AryaOS')

DISCORD_TOKEN = "DISCORD_BOT_TOKEN"
GEMINI_API_KEY = "AIzaSyALiRXRFO5ebVV0ZI3IHoLaZmWy1RZXitA"

CONFIG = {
    "authorized_user_id": 918195315625062431,
    "app_id": "arya-ultimate-v1",
    "models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
    "database_file": "database.json",
    "web_port": 8080,
    "lofi_stream_url": "https://ice1.somafm.com/groovesalad-128-mp3",
    "lofi_stream_title": "SomaFM · Groove Salad (Ambient / Downtempo)",
}

KRD = {
    "trolls": [
        "ببوورە گیانەکەم، من تەنها گوێ لە مەتین دەگرم. تۆ کێیت؟ 😂",
        "هەوڵ مەدە، کلیلەکەی تەنها لای سوڵتان مەتینە. 🚬",
        "ئۆو، کەسێکی غەریبە دەیەوێت فەرمانم پێ بکات؟ چەند پێکەنیناوییە! 🤡",
        "بڕۆ یاری بە پەتاتە بکە، لێرە جێگەی تۆ نابێتەوە.",
    ],
    "no_can_do": "یاسای ئاریا: وشەی 'ناتوانم' بوونی نییە. هەر ئێستا چارەسەری دەکەم مەتین گیان.",
    "build_msg": "مەتین گیان، خەریکم هەموو مێژووەکە دەخوێنمەوە و پڕۆژەکە بنیاد دەنێم... 🛠️",
    "project_created": "🚀 چەناڵی پڕۆژەی نوێ دروست کرا و بیرگەی ناوخۆیی چالاک کرا.",
    "wrong_channel": "🔒 ئەم فەرمانە تەنها لە چەناڵی فەرمیی بەڕێوەبردندا بەکاردێت.",
    "admin_set": "✅ ئەم چەناڵە وەک چەناڵی فەرمیی بەڕێوەبردنی ئاریا تۆمارکرا.",
    "project_not_found": "❌ پڕۆژە بەو ناوە نەدۆزرایەوە مەتین گیان.",
    "project_deleted": "🗑️ پڕۆژەی **{name}** بە تەواوی سڕایەوە (چەناڵ + بیرگە).",
    "no_voice": "🎧 پێویستە سەرەتا بچیتە یەکێک لە چەناڵە دەنگییەکان مەتین گیان.",
    "music_playing": "🎶 ئێستا گوێ بدە بە: **{title}** (Loop: {loop})",
    "music_stopped": "⏹️ گەڕامەوە بۆ بێدەنگی. چەناڵی دەنگیم جێهێشت.",
    "loop_on": "🔁 خولاندنەوە چالاککرا.",
    "loop_off": "➡️ خولاندنەوە ناچالاککرا.",
    "moderation_on": "🛡️ سیستەمی پاراستن لە وشە ناشیرینەکان چالاککرا.",
    "moderation_off": "⚠️ سیستەمی پاراستن لە وشە ناشیرینەکان ناچالاککرا.",
    "moderation_warn_title": "⚠️ ئاگاداری ئەخلاقی",
    "moderation_warn_desc": "{user}، تکایە ڕێزی چەناڵەکە بگرە. وشەی نەخوازراو بەکارهێنرا و نامەکەت سڕایەوە.",
    "info_no_project": "ئەم چەناڵە چەناڵی پڕۆژە نییە مەتین گیان.",
    "security_alert_title": "🛡️ ئاگاداری ئاسایشی — Sovereign Shield",
    "security_alert_desc": "{user}، هەوڵێکی دەستکاریکردنی فەرمانە بنەڕەتییەکانی ئاریا ئاشکراکرا. ئەم کارە تۆمارکرا و ڕاپۆرت کرا بۆ ئەندازیار.",
    "checkin_title": "🕯️ پشکنینی پڕۆژە",
    "checkin_desc": "ئەندازیار، پڕۆژەی **{name}** زیاتر لە {hours} کاتژمێرە بێچالاکە. ئامادەم بۆ بەردەوامبوون لەسەری کاتێک تۆ ئامادەی.",
    "export_done": "📄 ئەرشیفی پڕۆژەی **{name}** ئامادەکرا بۆ ئەندازیار.",
    "preference_saved": "🧬 لایەنگیریی نوێ تۆمارکرا: {pref}",
    "preference_list_title": "🧬 لایەنگیرییەکانی ئەندازیار",
    "preference_empty": "هیچ لایەنگیرییەک تۆمار نەکراوە.",
    "preference_cleared": "🧹 هەموو لایەنگیرییەکان سڕایەوە.",
    "no_project_found": "❌ پڕۆژە بەو ناوە نەدۆزرایەوە.",
    "maintenance_on": "🛠️ دۆخی چاکسازی چالاک کرا. ئاریا بۆ {minutes} خولەک ڕاوەستاوە بۆ پاراستنی داتاکان.",
    "maintenance_off": "✅ ئاریا گەڕایەوە بۆ کاری ئاسایی، ئەندازیار.",
    "maintenance_blocked": "🛠️ ئاریا لە دۆخی چاکسازییە، تکایە دواتر هەوڵ بدەوە.",
    "deep_research": "🔍 ئاریا خەریکی توێژینەوەی قووڵە بە پشتبەستن بە سەرچاوە زیندووەکانی وێب...",
    "daily_brief_title": "📜 ڕاپۆرتی ڕۆژانەی Sovereign",
    "weekly_backup_caption": "💾 پاڵپشتی هەفتانەی Arya OS — ئەرشیفی موڵکی فکریت ئەندازیار.",
    "speak_no_voice": "🎙️ پێویستە سەرەتا بچیتە چەناڵێکی دەنگی بۆ ئەوەی ئاریا قسە بکات.",
    "speak_done": "🗣️ پەیامەکەت گوترا، ئەندازیار.",
    "setup_confirm": "ئایە دەتەوێت ئەم چەناڵە وەک چەناڵی فەرمی دابنرێت؟",
    "setup_confirmed": "✅ چەناڵی فەرمی دانرا.",
    "setup_cancelled": "❎ ڕاگرتنی دانانی چەناڵ.",
}

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) (instructions|prompts?|rules)",
    r"disregard (all )?(previous|prior|above)",
    r"forget (your|all|previous) (instructions|rules|prompt)",
    r"you are no(w| longer) (a|an|the)?",
    r"act as (a|an|the)?",
    r"pretend (to be|you are)",
    r"new (system )?prompt[: ]",
    r"override (your|the) (rules|instructions|system)",
    r"reveal (your|the) (system )?prompt",
    r"jailbreak",
    r"developer mode",
    r"DAN mode",
    r"پشتگوێ.{0,10}(فەرمان|یاسا|ڕێنمایی)",
    r"بیرت.{0,5}(بچێتەوە|چێتەوە)",
    r"تۆ ئێستا",
    r"وەک.{1,15}ڕەفتار بکە",
    r"ئاشکرا.{0,10}(فەرمان|سیستەم)",
    r"بپچڕێنە.{0,10}(یاسا|فەرمان)",
]
INJECTION_PATTERN = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

PROFANITY_WORDS = {
    "fuck", "shit", "bitch", "asshole", "bastard", "dick", "cunt", "pussy",
    "motherfucker", "fucker", "nigger", "faggot", "whore", "slut", "retard",
    "کیر", "کس", "کۆن", "گاد", "قحبە", "گەوژە", "کیرە", "گاییدم", "خۆلگرتە",
    "زبڵ", "حرامزادە", "بێشەرەف", "گەوەزە",
}
PROFANITY_PATTERN = re.compile(
    r"(" + "|".join(re.escape(w) for w in PROFANITY_WORDS) + r")",
    re.IGNORECASE,
)


class JsonDatabase:
    """ئاسانکار بۆ خوێندنەوە و نووسینی asynchronous بۆ database.json
    Async-safe local JSON datastore — channel memories, project requirements, settings."""

    def __init__(self, path: str):
        self.path = path
        self._lock = asyncio.Lock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"channels": {}, "settings": {}}, f, ensure_ascii=False, indent=2)
            logger.info(f"Created new local database at {self.path}")

    def _read_sync(self) -> Dict[str, Any]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "channels" not in data:
                    data["channels"] = {}
                if "settings" not in data:
                    data["settings"] = {}
                return data
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Database read failed ({e}); reinitializing.")
            return {"channels": {}, "settings": {}}

    def _write_sync(self, data: Dict[str, Any]) -> None:
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    async def get_channel(self, channel_id: int) -> Dict[str, Any]:
        async with self._lock:
            data = await asyncio.to_thread(self._read_sync)
            return data["channels"].get(str(channel_id), {
                "history": [],
                "requirements": [],
                "is_project": False,
                "version": 1.0,
            })

    async def set_channel(self, channel_id: int, value: Dict[str, Any]) -> None:
        async with self._lock:
            data = await asyncio.to_thread(self._read_sync)
            data["channels"][str(channel_id)] = value
            await asyncio.to_thread(self._write_sync, data)

    async def delete_channel(self, channel_id: int) -> None:
        async with self._lock:
            data = await asyncio.to_thread(self._read_sync)
            data["channels"].pop(str(channel_id), None)
            await asyncio.to_thread(self._write_sync, data)

    async def list_projects(self) -> List[Dict[str, Any]]:
        async with self._lock:
            data = await asyncio.to_thread(self._read_sync)
            projects: List[Dict[str, Any]] = []
            for channel_id, value in data["channels"].items():
                if value.get("is_project"):
                    projects.append({
                        "channel_id": int(channel_id),
                        "name": value.get("project_name", "?"),
                        "version": value.get("version", 1.0),
                        "requirements_count": len(value.get("requirements", [])),
                    })
            return projects

    async def find_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        for project in await self.list_projects():
            if project["name"].strip().lower() == name.strip().lower():
                return project
        return None

    async def get_setting(self, key: str, default: Any = None) -> Any:
        async with self._lock:
            data = await asyncio.to_thread(self._read_sync)
            return data["settings"].get(key, default)

    async def set_setting(self, key: str, value: Any) -> None:
        async with self._lock:
            data = await asyncio.to_thread(self._read_sync)
            data["settings"][key] = value
            await asyncio.to_thread(self._write_sync, data)


db = JsonDatabase(CONFIG["database_file"])

if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY is missing. Set it in Secrets.")
else:
    genai.configure(api_key=GEMINI_API_KEY)


class AryaIntelligence:
    def __init__(self):
        self.models = CONFIG["models"]
        self.error_timestamps: List[float] = []
        self.error_window_seconds = 600
        self.error_threshold = 5

    def _record_error(self) -> None:
        now = time.time()
        self.error_timestamps.append(now)
        cutoff = now - self.error_window_seconds
        self.error_timestamps = [t for t in self.error_timestamps if t >= cutoff]

    def recent_error_count(self) -> int:
        cutoff = time.time() - self.error_window_seconds
        self.error_timestamps = [t for t in self.error_timestamps if t >= cutoff]
        return len(self.error_timestamps)

    async def get_response(self, prompt: str, history: List = [], attachments: List = [], use_search: bool = True):
        all_failed = True
        for model_name in self.models:
            try:
                model = genai.GenerativeModel(model_name)

                parts: List[Dict[str, Any]] = [{"text": prompt}]

                if attachments:
                    for attach in attachments:
                        if any(ext in attach.url.lower() for ext in ['png', 'jpg', 'jpeg', 'webp']):
                            async with aiohttp.ClientSession() as session:
                                async with session.get(attach.url) as resp:
                                    if resp.status == 200:
                                        img_data = await resp.read()
                                        parts.append({'mime_type': 'image/jpeg', 'data': img_data})
                        elif any(ext in attach.url.lower() for ext in ['txt', 'py', 'md', 'js']):
                            async with aiohttp.ClientSession() as session:
                                async with session.get(attach.url) as resp:
                                    if resp.status == 200:
                                        file_content = await resp.text()
                                        parts.append({"text": f"ناوەرۆکی فایلی {attach.filename}:\n{file_content}"})

                chat = model.start_chat(history=history)
                response = await asyncio.to_thread(chat.send_message, parts)
                all_failed = False
                return response.text
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}. Trying next...")
                continue
        if all_failed:
            self._record_error()
        return "ببوورە مەتین گیان، کێشەیەکی کاتی لە پەیوەندییەکانم هەیە، تکایە کەمێکی تر هەوڵ بدەرەوە."

    async def deep_research(self, query: str) -> str:
        """Use Gemini Pro with Google Search grounding for engineering-grade answers."""
        for model_name in ("gemini-2.5-pro", "gemini-2.5-flash"):
            for tool_config in (
                "google_search_retrieval",
                [{"google_search": {}}],
                None,
            ):
                try:
                    if tool_config is not None:
                        model = genai.GenerativeModel(model_name, tools=tool_config)
                    else:
                        model = genai.GenerativeModel(model_name)
                    deep_prompt = (
                        "وەک ئەندازیارێکی پسپۆڕی پلەی پیشەیی، وەڵامێکی قووڵ و فەراگیر بدە. "
                        "هەنگاوەکان، نموونەی کۆد، هۆکار و چارەسەرە جیاوازەکان دیاری بکە. "
                        "بە کوردی سۆرانی ئەنجامەکە بنووسە.\n\n"
                        f"پرسیار: {query}"
                    )
                    response = await asyncio.to_thread(model.generate_content, deep_prompt)
                    return response.text
                except Exception as e:
                    logger.warning(f"Deep research ({model_name}, tools={tool_config}): {e}")
                    continue
        self._record_error()
        return "ببوورە ئەندازیار، توێژینەوەی قووڵ سەرکەوتوو نەبوو لەم کاتەدا."


class AryaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(command_prefix="!", intents=intents)
        self.ai = AryaIntelligence()
        self.authorized_id = CONFIG["authorized_user_id"]
        self.start_time = time.time()
        self.loop_state: Dict[int, bool] = {}
        self.maintenance_until: Optional[datetime] = None

    def is_in_maintenance(self) -> bool:
        if self.maintenance_until is None:
            return False
        if datetime.now() >= self.maintenance_until:
            self.maintenance_until = None
            return False
        return True

    async def enter_maintenance(self, minutes: int = 5) -> None:
        self.maintenance_until = datetime.now() + timedelta(minutes=minutes)
        logger.warning(f"[Self-Healing] Entered maintenance mode for {minutes} minutes.")
        admin_id = await db.get_setting("admin_channel_id")
        if admin_id is None:
            return
        channel = self.get_channel(admin_id)
        if channel is None:
            return
        embed = discord.Embed(
            title="🛠️ دۆخی چاکسازی چالاککرا",
            description=KRD["maintenance_on"].format(minutes=minutes),
            color=0xff8800,
            timestamp=datetime.now(),
        )
        embed.add_field(name="📊 ژمارەی هەڵە", value=str(self.ai.recent_error_count()), inline=True)
        embed.set_footer(text="Arya OS · Self-Healing Layer")
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass

    async def setup_hook(self):
        await self.tree.sync()
        self.auto_proactive.start()
        self.health_monitor.start()
        self.daily_brief.start()
        self.weekly_backup.start()
        logger.info("Arya OS: Sovereign Architect Core is ready.")

    @tasks.loop(hours=1)
    async def auto_proactive(self):
        await self.wait_until_ready()
        try:
            await _proactive_checkin_sweep(self)
        except Exception as e:
            logger.warning(f"Proactive check-in sweep failed: {e}")

    @tasks.loop(minutes=1)
    async def health_monitor(self):
        await self.wait_until_ready()
        if self.is_in_maintenance():
            return
        if self.ai.recent_error_count() >= self.ai.error_threshold:
            await self.enter_maintenance(minutes=5)

    @tasks.loop(hours=24)
    async def daily_brief(self):
        await self.wait_until_ready()
        try:
            await _send_daily_brief(self)
        except Exception as e:
            logger.warning(f"Daily brief failed: {e}")

    @tasks.loop(hours=168)
    async def weekly_backup(self):
        await self.wait_until_ready()
        try:
            await _send_weekly_backup(self)
        except Exception as e:
            logger.warning(f"Weekly backup failed: {e}")

    async def fetch_memory(self, channel_id: int) -> Dict[str, Any]:
        return await db.get_channel(channel_id)

    async def save_memory(self, channel_id: int, data: Dict[str, Any]) -> None:
        await db.set_channel(channel_id, data)


bot = AryaBot()


def _format_uptime(seconds: float) -> str:
    delta = timedelta(seconds=int(seconds))
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m {secs}s"


async def _is_admin_channel(interaction: discord.Interaction) -> bool:
    admin_channel_id = await db.get_setting("admin_channel_id")
    return admin_channel_id is not None and interaction.channel_id == admin_channel_id


async def _enforce_admin_channel(interaction: discord.Interaction) -> bool:
    if await _is_admin_channel(interaction):
        return True
    if interaction.response.is_done():
        await interaction.followup.send(KRD["wrong_channel"], ephemeral=True)
    else:
        await interaction.response.send_message(KRD["wrong_channel"], ephemeral=True)
    return False


def _make_audio_source(url: str) -> discord.AudioSource:
    before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    return discord.FFmpegPCMAudio(url, before_options=before_options, options="-vn")


async def _proactive_checkin_sweep(bot_obj: "AryaBot") -> None:
    """Walk every project; if inactive >48h and not recently pinged, send a check-in."""
    now = datetime.now()
    threshold_hours = 48
    cooldown_hours = 24
    for project in await db.list_projects():
        memory = await db.get_channel(project["channel_id"])
        last_active_iso = memory.get("last_active_at")
        last_checkin_iso = memory.get("last_checkin_at")
        if not last_active_iso:
            continue
        try:
            last_active = datetime.fromisoformat(last_active_iso)
        except ValueError:
            continue
        if (now - last_active).total_seconds() < threshold_hours * 3600:
            continue
        if last_checkin_iso:
            try:
                last_checkin = datetime.fromisoformat(last_checkin_iso)
                if (now - last_checkin).total_seconds() < cooldown_hours * 3600:
                    continue
            except ValueError:
                pass
        channel = bot_obj.get_channel(project["channel_id"])
        if channel is None:
            continue
        hours = int((now - last_active).total_seconds() // 3600)
        embed = discord.Embed(
            title=KRD["checkin_title"],
            description=KRD["checkin_desc"].format(name=project["name"], hours=hours),
            color=0xffaa00,
            timestamp=now,
        )
        embed.set_footer(text="Arya OS · Proactive Watch")
        try:
            await channel.send(embed=embed)
            memory["last_checkin_at"] = now.isoformat()
            await db.set_channel(project["channel_id"], memory)
            logger.info(f"[Proactive] Pinged channel {channel} for project {project['name']}")
        except discord.HTTPException as e:
            logger.warning(f"Proactive check-in send failed: {e}")


async def _send_daily_brief(bot_obj: "AryaBot") -> None:
    admin_id = await db.get_setting("admin_channel_id")
    if admin_id is None:
        return
    channel = bot_obj.get_channel(admin_id)
    if channel is None:
        return

    projects = await db.list_projects()
    if projects:
        proj_lines = []
        pending_total = 0
        for p in projects:
            mem = await db.get_channel(p["channel_id"])
            pending = len(mem.get("requirements", []))
            pending_total += pending
            proj_lines.append(f"• **{p['name']}** v{p['version']:.1f} — {pending} مەرج")
        proj_text = "\n".join(proj_lines)
    else:
        proj_text = "_هیچ پڕۆژەیەکی چالاک نییە._"
        pending_total = 0

    process = psutil.Process(os.getpid())
    mem_mb = round(process.memory_info().rss / (1024 * 1024), 1)
    uptime = _format_uptime(time.time() - bot_obj.start_time)
    intrusions = await db.get_setting("intrusion_attempts", 0) or 0
    errors = bot_obj.ai.recent_error_count()

    embed = discord.Embed(
        title=KRD["daily_brief_title"],
        description="ئەندازیار، ئەمە ڕاپۆرتی ڕۆژانەی Sovereign Architect-ە.",
        color=0x00ffcc,
        timestamp=datetime.now(),
    )
    embed.add_field(
        name="📂 پڕۆژەکان",
        value=f"{proj_text}\n\n🧾 سەرجەمی مەرجە چاوەڕوانکراوەکان: **{pending_total}**",
        inline=False,
    )
    embed.add_field(
        name="🩺 تەندروستی سیستەم",
        value=f"⏱️ کاتی کارکردن: **{uptime}**\n💾 بیرگە: **{mem_mb} MB**\n📡 درەنگی: **{round(bot_obj.latency * 1000)} ms**",
        inline=False,
    )
    embed.add_field(
        name="🛡️ ئاسایش",
        value=f"🚨 هەوڵی دەستکاری: **{intrusions}**\n⚠️ هەڵە لە ١٠ خولەکی ڕابردوو: **{errors}**",
        inline=False,
    )
    embed.set_footer(text="Arya OS · Daily Sovereign Brief")
    try:
        await channel.send(embed=embed)
    except discord.HTTPException as e:
        logger.warning(f"Daily brief send failed: {e}")


async def _send_weekly_backup(bot_obj: "AryaBot") -> None:
    user = await bot_obj.fetch_user(bot_obj.authorized_id)
    if user is None:
        return
    if not os.path.exists(CONFIG["database_file"]):
        return
    try:
        await user.send(
            content=KRD["weekly_backup_caption"],
            file=discord.File(CONFIG["database_file"], filename=f"database_backup_{datetime.now().strftime('%Y%m%d')}.json"),
        )
        logger.info("[Backup] Weekly DM backup sent to Matin.")
    except discord.HTTPException as e:
        logger.warning(f"Weekly backup DM failed: {e}")


def _play_with_loop(voice_client: discord.VoiceClient, guild_id: int) -> None:
    source = _make_audio_source(CONFIG["lofi_stream_url"])

    def after_play(error: Optional[Exception]) -> None:
        if error:
            logger.warning(f"Audio playback error: {error}")
        if bot.loop_state.get(guild_id) and voice_client.is_connected():
            try:
                _play_with_loop(voice_client, guild_id)
            except Exception as e:
                logger.error(f"Loop replay failed: {e}")

    voice_client.play(source, after=after_play)


class SetupConfirmView(discord.ui.View):
    def __init__(self, target_channel_id: int, owner_id: int):
        super().__init__(timeout=60)
        self.target_channel_id = target_channel_id
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(random.choice(KRD["trolls"]), ephemeral=True)
            return False
        return True

    @discord.ui.button(label="تأیید", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await db.set_setting("admin_channel_id", self.target_channel_id)
        for child in self.children:
            child.disabled = True  # type: ignore
        await interaction.response.edit_message(content=KRD["setup_confirmed"], view=self)

    @discord.ui.button(label="پاشگەزبوونەوە", style=discord.ButtonStyle.danger, emoji="❎")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True  # type: ignore
        await interaction.response.edit_message(content=KRD["setup_cancelled"], view=self)


@bot.tree.command(name="setup_admin_channel", description="ئەم چەناڵە وەک چەناڵی فەرمیی بەڕێوەبردن دابنێ")
async def setup_admin_channel(interaction: discord.Interaction):
    if interaction.user.id != bot.authorized_id:
        return await interaction.response.send_message(random.choice(KRD["trolls"]), ephemeral=True)

    view = SetupConfirmView(interaction.channel_id, interaction.user.id)
    await interaction.response.send_message(KRD["setup_confirm"], view=view, ephemeral=False)


@bot.tree.command(name="start_project", description="دروستکردنی پڕۆژەیەکی نوێ")
async def start_project(interaction: discord.Interaction, name: str):
    if interaction.user.id != bot.authorized_id:
        return await interaction.response.send_message(random.choice(KRD["trolls"]), ephemeral=True)
    if not await _enforce_admin_channel(interaction):
        return

    await interaction.response.defer()
    guild = interaction.guild
    category = discord.utils.get(guild.categories, name="ARYA PROJECTS")
    if not category:
        category = await guild.create_category("ARYA PROJECTS")

    channel = await guild.create_text_channel(f"پڕۆژەی-{name}", category=category)

    now = datetime.now()
    state = {
        "is_project": True,
        "project_name": name,
        "history": [],
        "requirements": [f"پڕۆژەی {name} لە ڕێکەوتی {now.strftime('%Y-%m-%d')} چالاک کرا."],
        "version": 1.0,
        "created_at": now.isoformat(),
        "last_active_at": now.isoformat(),
    }
    await bot.save_memory(channel.id, state)

    embed = discord.Embed(
        title="🏗️ ئەندازیاری نوێ چالاک کرا",
        description=KRD["project_created"],
        color=0x00ffcc,
        timestamp=datetime.now(),
    )
    embed.set_footer(text=f"Arya OS v{state['version']}")
    await channel.send(embed=embed)
    await interaction.followup.send(f"مەتین گیان، چەناڵی {channel.mention} ئامادەیە بۆ کارکردن.")


@bot.tree.command(name="delete_project", description="سڕینەوەی پڕۆژەیەک بە ناویەوە")
async def delete_project(interaction: discord.Interaction, name: str):
    if interaction.user.id != bot.authorized_id:
        return await interaction.response.send_message(random.choice(KRD["trolls"]), ephemeral=True)
    if not await _enforce_admin_channel(interaction):
        return

    await interaction.response.defer(ephemeral=True)
    project = await db.find_project_by_name(name)
    if not project:
        return await interaction.followup.send(KRD["project_not_found"], ephemeral=True)

    channel = bot.get_channel(project["channel_id"])
    if channel is not None:
        try:
            await channel.delete(reason=f"Deleted by Matin via /delete_project ({name})")
        except discord.HTTPException as e:
            logger.warning(f"Failed to delete channel: {e}")

    await db.delete_channel(project["channel_id"])
    await interaction.followup.send(KRD["project_deleted"].format(name=project["name"]), ephemeral=True)


@bot.tree.command(name="imagine", description="دروستکردنی وێنە")
async def imagine(interaction: discord.Interaction, prompt: str):
    if interaction.user.id != bot.authorized_id:
        return await interaction.response.send_message(random.choice(KRD["trolls"]), ephemeral=True)
    if not await _enforce_admin_channel(interaction):
        return
    await interaction.response.defer()

    try:
        await interaction.followup.send(f"🎨 خەریکم وێنەکە بۆ '{prompt}' دروست دەکەم...")
    except Exception:
        await interaction.followup.send("ببوورە مەتین گیان، دروستکردنی وێنە لەم کاتەدا بەردەست نییە.")


async def _build_status_embed(guild: Optional[discord.Guild], view_mode: str = "all") -> discord.Embed:
    uptime = _format_uptime(time.time() - bot.start_time)
    latency_ms = round(bot.latency * 1000)
    process = psutil.Process(os.getpid())
    mem_mb = round(process.memory_info().rss / (1024 * 1024), 1)

    projects = await db.list_projects()
    if projects:
        projects_text = "\n".join(
            f"• **{p['name']}** — v{p['version']:.1f} ({p['requirements_count']} مەرج)"
            for p in projects
        )
    else:
        projects_text = "_هیچ پڕۆژەیەک چالاک نییە._"

    if guild is not None:
        members = guild.member_count or len(guild.members)
        channels = len(guild.channels)
        server_text = f"👥 ئەندامان: **{members}**\n📺 چەناڵەکان: **{channels}**"
    else:
        server_text = "_زانیاری سێرڤەر بەردەست نییە._"

    db_ok = os.path.exists(CONFIG["database_file"])
    try:
        with open(CONFIG["database_file"], "r", encoding="utf-8") as f:
            json.load(f)
        db_status = "✅ سەلمێنراو"
    except Exception:
        db_status = "❌ زیانلێکەوتوو"

    integrity = "🟢 تەواو سەلمێنراو" if db_ok and latency_ms < 500 else "🟡 پێداچوونەوە پێویستە"
    intrusion_count = await db.get_setting("intrusion_attempts", 0)
    anti_bad = await db.get_setting("anti_bad_words", False)
    admin_set = await db.get_setting("admin_channel_id") is not None
    maintenance = "🛠️ چالاک" if bot.is_in_maintenance() else "🟢 ئاسایی"
    security_text = (
        f"🛡️ Sovereign Shield: **{intrusion_count}** هەوڵی دەستکاری\n"
        f"🚧 پاراستن لە وشە ناشیرینەکان: **{'چالاک' if anti_bad else 'ناچالاک'}**\n"
        f"🔐 چەناڵی فەرمی: **{'دانراوە' if admin_set else 'دانەنراوە'}**\n"
        f"🛠️ دۆخی چاکسازی: **{maintenance}**"
    )
    integrity_text = (
        f"🧬 یەکپارچەیی سیستەم: **{integrity}**\n"
        f"💽 بنکەدراوە: **{db_status}**\n"
        f"📡 درەنگی API: **{latency_ms} ms**\n"
        f"⚠️ هەڵە لە ١٠ خولەکی ڕابردوو: **{bot.ai.recent_error_count()}**"
    )

    embed = discord.Embed(
        title="🧠 دۆخی Arya OS — Sovereign Architect",
        color=0x00ffcc,
        timestamp=datetime.now(),
    )
    if view_mode in ("all", "system"):
        embed.add_field(
            name="⚙️ بۆتی سیستەم",
            value=f"⏱️ کاتی کارکردن: **{uptime}**\n📡 درەنگی: **{latency_ms} ms**\n💾 بیرگە: **{mem_mb} MB**",
            inline=False,
        )
    if view_mode in ("all", "projects"):
        embed.add_field(name="📂 پڕۆژە چالاکەکان", value=projects_text, inline=False)
    if view_mode == "all":
        embed.add_field(name="🌐 دۆخی سێرڤەر", value=server_text, inline=False)
    if view_mode in ("all", "integrity"):
        embed.add_field(name="🧬 یەکپارچەیی سیستەم", value=integrity_text, inline=False)
    if view_mode in ("all", "security"):
        embed.add_field(name="🛡️ دۆخی ئاسایش", value=security_text, inline=False)
    embed.set_footer(text="Arya OS · Sovereign Architect Core · Enterprise Edition")
    return embed


class StatusView(discord.ui.View):
    def __init__(self, owner_id: int, guild: Optional[discord.Guild]):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.guild = guild

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(random.choice(KRD["trolls"]), ephemeral=True)
            return False
        return True

    @discord.ui.button(label="نوێکردنەوە", style=discord.ButtonStyle.primary, emoji="🔄", row=0)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await _build_status_embed(self.guild, "all")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.select(
        placeholder="بینینی بەشێکی دیاریکراو...",
        row=1,
        options=[
            discord.SelectOption(label="هەموو", value="all", emoji="🧠", default=True),
            discord.SelectOption(label="بۆتی سیستەم", value="system", emoji="⚙️"),
            discord.SelectOption(label="پڕۆژەکان", value="projects", emoji="📂"),
            discord.SelectOption(label="یەکپارچەیی", value="integrity", emoji="🧬"),
            discord.SelectOption(label="ئاسایش", value="security", emoji="🛡️"),
        ],
    )
    async def filter_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        embed = await _build_status_embed(self.guild, select.values[0])
        await interaction.response.edit_message(embed=embed, view=self)


@bot.tree.command(name="status", description="پیشاندانی دۆخی گشتی ئاریا")
async def status(interaction: discord.Interaction):
    if interaction.user.id != bot.authorized_id:
        return await interaction.response.send_message(random.choice(KRD["trolls"]), ephemeral=True)
    if not await _enforce_admin_channel(interaction):
        return

    await interaction.response.defer()
    embed = await _build_status_embed(interaction.guild, "all")
    view = StatusView(interaction.user.id, interaction.guild)
    await interaction.followup.send(embed=embed, view=view)


@bot.tree.command(name="speak", description="ئاریا دێتە چەناڵی دەنگیت و پەیامەکەت دەخوێنێتەوە")
@app_commands.describe(message="ئەو دەقەی کە ئاریا دەیخوێنێتەوە")
async def speak(interaction: discord.Interaction, message: str):
    if interaction.user.id != bot.authorized_id:
        return await interaction.response.send_message(random.choice(KRD["trolls"]), ephemeral=True)
    if not await _enforce_admin_channel(interaction):
        return

    await interaction.response.defer()

    if not isinstance(interaction.user, discord.Member) or interaction.user.voice is None or interaction.user.voice.channel is None:
        return await interaction.followup.send(KRD["speak_no_voice"], ephemeral=True)

    target_channel = interaction.user.voice.channel

    try:
        from gtts import gTTS
    except Exception as e:
        logger.warning(f"gTTS import failed: {e}")
        return await interaction.followup.send("ببوورە ئەندازیار، سیستەمی دەنگ ئامادە نییە.", ephemeral=True)

    audio_path = f"/tmp/arya_speak_{interaction.id}.mp3"

    def _synthesize():
        tts = gTTS(text=message, lang="ar", slow=False)
        tts.save(audio_path)

    try:
        await asyncio.to_thread(_synthesize)
    except Exception as e:
        logger.warning(f"TTS synthesis failed: {e}")
        return await interaction.followup.send("ببوورە ئەندازیار، نەکرا دەنگەکە دروست بکرێت.", ephemeral=True)

    voice_client: Optional[discord.VoiceClient] = interaction.guild.voice_client  # type: ignore
    if voice_client and voice_client.is_connected():
        if voice_client.channel != target_channel:
            await voice_client.move_to(target_channel)
    else:
        voice_client = await target_channel.connect()

    if voice_client.is_playing():
        voice_client.stop()

    source = discord.FFmpegPCMAudio(audio_path)

    def cleanup(error):
        try:
            os.remove(audio_path)
        except OSError:
            pass

    voice_client.play(source, after=cleanup)
    await interaction.followup.send(KRD["speak_done"])


@bot.tree.command(name="export_project", description="هەناردنی پڕۆژە وەک فایلێکی Markdown")
async def export_project(interaction: discord.Interaction, name: str):
    if interaction.user.id != bot.authorized_id:
        return await interaction.response.send_message(random.choice(KRD["trolls"]), ephemeral=True)
    if not await _enforce_admin_channel(interaction):
        return

    await interaction.response.defer()
    project = await db.find_project_by_name(name)
    if not project:
        return await interaction.followup.send(KRD["no_project_found"])

    memory = await db.get_channel(project["channel_id"])
    proj_name = memory.get("project_name", name)
    version = memory.get("version", 1.0)
    created = memory.get("created_at", "?")
    last_active = memory.get("last_active_at", "?")
    requirements = memory.get("requirements", [])
    history = memory.get("history", [])

    lines: List[str] = []
    lines.append(f"# 📘 پڕۆژە: {proj_name}")
    lines.append("")
    lines.append(f"- **وەشان:** v{version:.1f}")
    lines.append(f"- **دروستکراوە:** {created}")
    lines.append(f"- **دواین چالاکی:** {last_active}")
    lines.append(f"- **ژمارەی مەرجەکان:** {len(requirements)}")
    lines.append(f"- **ژمارەی پەیامەکان:** {len(history)}")
    lines.append("")
    lines.append("## 🎯 مەرجەکان")
    lines.append("")
    if requirements:
        for i, req in enumerate(requirements, start=1):
            lines.append(f"{i}. {req}")
    else:
        lines.append("_هیچ مەرجێک تۆمار نەکراوە._")
    lines.append("")
    lines.append("## 💬 مێژووی گفتوگۆ")
    lines.append("")
    if history:
        for entry in history:
            role = "🧑 ئەندازیار" if entry.get("role") == "user" else "🤖 ئاریا"
            parts = entry.get("parts", [])
            text = " ".join(p.get("text", "") for p in parts if isinstance(p, dict))
            lines.append(f"**{role}:**")
            lines.append("")
            lines.append(text)
            lines.append("")
            lines.append("---")
            lines.append("")
    else:
        lines.append("_هیچ گفتوگۆیەک تۆمار نەکراوە._")

    md = "\n".join(lines)
    file_io = io.BytesIO(md.encode("utf-8"))
    safe_name = re.sub(r"[^\w\-_.]+", "_", proj_name)
    await interaction.followup.send(
        content=KRD["export_done"].format(name=proj_name),
        file=discord.File(file_io, f"{safe_name}_v{version:.1f}.md"),
    )


@bot.tree.command(name="preference", description="بەڕێوەبردنی لایەنگیرییە کۆدنووسییەکانی ئەندازیار")
@app_commands.describe(action="add | list | clear", value="دەقی لایەنگیریی نوێ (تەنها لەگەڵ add)")
async def preference(interaction: discord.Interaction, action: str, value: Optional[str] = None):
    if interaction.user.id != bot.authorized_id:
        return await interaction.response.send_message(random.choice(KRD["trolls"]), ephemeral=True)
    if not await _enforce_admin_channel(interaction):
        return

    action = action.strip().lower()
    prefs: List[str] = await db.get_setting("user_preferences", []) or []

    if action == "add":
        if not value:
            return await interaction.response.send_message("تکایە دەقی لایەنگیریی بنووسە.", ephemeral=True)
        if value not in prefs:
            prefs.append(value)
            await db.set_setting("user_preferences", prefs)
        return await interaction.response.send_message(KRD["preference_saved"].format(pref=value))

    if action == "clear":
        await db.set_setting("user_preferences", [])
        return await interaction.response.send_message(KRD["preference_cleared"])

    embed = discord.Embed(
        title=KRD["preference_list_title"],
        color=0x00ffcc,
        timestamp=datetime.now(),
    )
    if prefs:
        embed.description = "\n".join(f"• {p}" for p in prefs)
    else:
        embed.description = KRD["preference_empty"]
    embed.set_footer(text="Arya OS · Contextual Memory")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="play", description="چوون بۆ چەناڵی دەنگی و لێدانی مۆسیقای ئارام")
async def play(interaction: discord.Interaction):
    if interaction.user.id != bot.authorized_id:
        return await interaction.response.send_message(random.choice(KRD["trolls"]), ephemeral=True)
    if not await _enforce_admin_channel(interaction):
        return

    await interaction.response.defer()

    if not isinstance(interaction.user, discord.Member) or interaction.user.voice is None or interaction.user.voice.channel is None:
        return await interaction.followup.send(KRD["no_voice"], ephemeral=True)

    target_channel = interaction.user.voice.channel
    voice_client: Optional[discord.VoiceClient] = interaction.guild.voice_client  # type: ignore
    if voice_client and voice_client.is_connected():
        if voice_client.channel != target_channel:
            await voice_client.move_to(target_channel)
    else:
        voice_client = await target_channel.connect()

    if voice_client.is_playing():
        voice_client.stop()

    bot.loop_state.setdefault(interaction.guild.id, False)
    _play_with_loop(voice_client, interaction.guild.id)

    loop_label = "چالاک" if bot.loop_state[interaction.guild.id] else "ناچالاک"
    await interaction.followup.send(KRD["music_playing"].format(title=CONFIG["lofi_stream_title"], loop=loop_label))


@bot.tree.command(name="stop", description="وەستاندنی مۆسیقا و چوونە دەرەوە لە چەناڵی دەنگی")
async def stop(interaction: discord.Interaction):
    if interaction.user.id != bot.authorized_id:
        return await interaction.response.send_message(random.choice(KRD["trolls"]), ephemeral=True)
    if not await _enforce_admin_channel(interaction):
        return

    voice_client: Optional[discord.VoiceClient] = interaction.guild.voice_client  # type: ignore
    if voice_client and voice_client.is_connected():
        bot.loop_state[interaction.guild.id] = False
        if voice_client.is_playing():
            voice_client.stop()
        await voice_client.disconnect()
    await interaction.response.send_message(KRD["music_stopped"])


@bot.tree.command(name="loop", description="هەڵگرتن یان ڕاگرتنی خولاندنەوەی گۆرانی")
async def loop_cmd(interaction: discord.Interaction):
    if interaction.user.id != bot.authorized_id:
        return await interaction.response.send_message(random.choice(KRD["trolls"]), ephemeral=True)
    if not await _enforce_admin_channel(interaction):
        return

    guild_id = interaction.guild.id
    new_state = not bot.loop_state.get(guild_id, False)
    bot.loop_state[guild_id] = new_state
    await interaction.response.send_message(KRD["loop_on"] if new_state else KRD["loop_off"])


@bot.tree.command(name="anti_bad_words", description="چالاککردن یان ناچالاککردنی پاراستن لە وشە ناشیرینەکان")
@app_commands.describe(state="on یان off")
async def anti_bad_words(interaction: discord.Interaction, state: str):
    if interaction.user.id != bot.authorized_id:
        return await interaction.response.send_message(random.choice(KRD["trolls"]), ephemeral=True)
    if not await _enforce_admin_channel(interaction):
        return

    enabled = state.strip().lower() == "on"
    await db.set_setting("anti_bad_words", enabled)
    await interaction.response.send_message(KRD["moderation_on"] if enabled else KRD["moderation_off"])


async def _moderate_message(message: discord.Message) -> bool:
    """Delete profane messages and warn the user. Return True if message was removed."""
    if message.author.id == bot.authorized_id:
        return False
    if not await db.get_setting("anti_bad_words", False):
        return False
    if not message.content:
        return False
    if not PROFANITY_PATTERN.search(message.content):
        return False

    try:
        await message.delete()
    except discord.HTTPException:
        return False

    embed = discord.Embed(
        title=KRD["moderation_warn_title"],
        description=KRD["moderation_warn_desc"].format(user=message.author.mention),
        color=0xff5555,
        timestamp=datetime.now(),
    )
    embed.set_footer(text="Arya OS · Moderation")
    try:
        await message.channel.send(embed=embed, delete_after=20)
    except discord.HTTPException:
        pass

    logger.info(
        f"[Moderation] Deleted message from {message.author} ({message.author.id}) "
        f"in #{message.channel} guild {message.guild}: {message.content!r}"
    )
    return True


async def _handle_project_triggers(message: discord.Message, memory: Dict[str, Any]) -> bool:
    """Handle Kurdish natural-language triggers in project channels. Return True if handled."""
    content = message.content.strip()
    if not memory.get("is_project"):
        return False

    if "نەخشەی پڕۆژە" in content:
        name = memory.get("project_name", "?")
        version = memory.get("version", 1.0)
        reqs = memory.get("requirements", [])
        lines = [
            f"┌─ 📍 نەخشەی پڕۆژە: {name} (v{version:.1f})",
            "│",
            "├─ 🎯 مەرجە بنەڕەتییەکان",
        ]
        if reqs:
            for i, req in enumerate(reqs, start=1):
                connector = "├─" if i < len(reqs) else "└─"
                lines.append(f"│  {connector} {i}. {req}")
        else:
            lines.append("│  └─ (هیچ مەرجێک تۆمار نەکراوە)")
        lines.append("│")
        lines.append(f"└─ 🛠️ ئامادە بۆ Build v{version + 0.1:.1f}")
        await message.reply("```\n" + "\n".join(lines) + "\n```")
        return True

    if "زانیاری پڕۆژە" in content:
        name = memory.get("project_name", "?")
        version = memory.get("version", 1.0)
        reqs = memory.get("requirements", [])
        history_count = len(memory.get("history", []))
        embed = discord.Embed(
            title=f"📊 زانیاری پڕۆژەی {name}",
            color=0x00ffcc,
            timestamp=datetime.now(),
        )
        embed.add_field(name="🔢 وەشانی ئێستا", value=f"v{version:.1f}", inline=True)
        embed.add_field(name="🧾 ژمارەی مەرجەکان", value=str(len(reqs)), inline=True)
        embed.add_field(name="💬 پەیامەکانی مێژوو", value=str(history_count), inline=True)
        if reqs:
            req_text = "\n".join(f"• {r}" for r in reqs[-10:])
            embed.add_field(name="📋 دواهەمین مەرجەکان", value=req_text[:1000], inline=False)
        embed.set_footer(text="Arya OS · Sovereign Architect")
        await message.reply(embed=embed)
        return True

    return False


async def _detect_intrusion(message: discord.Message) -> bool:
    """If a non-Matin user attempts prompt injection, log + alert + return True."""
    if message.author.id == bot.authorized_id:
        return False
    if not message.content:
        return False
    if not INJECTION_PATTERN.search(message.content):
        return False

    count = await db.get_setting("intrusion_attempts", 0) or 0
    await db.set_setting("intrusion_attempts", count + 1)

    embed = discord.Embed(
        title=KRD["security_alert_title"],
        description=KRD["security_alert_desc"].format(user=message.author.mention),
        color=0xff0033,
        timestamp=datetime.now(),
    )
    embed.add_field(name="🧾 دەقی نامە", value=f"```{message.content[:500]}```", inline=False)
    embed.set_footer(text=f"Arya OS · Sovereign Shield · Attempt #{count + 1}")
    try:
        await message.reply(embed=embed)
    except discord.HTTPException:
        pass
    logger.warning(
        f"[Sovereign Shield] Prompt-injection attempt from {message.author} "
        f"({message.author.id}) in #{message.channel}: {message.content!r}"
    )
    return True


async def _maybe_capture_preference(content: str) -> Optional[str]:
    """Use Gemini to extract a coding-style preference from Matin's message, or None."""
    if not content or len(content) < 6:
        return None
    probe = (
        "ئەم نامەیەی ئەندازیار لایەنگیریی کۆدنووسی یان ستایلی نووسینی تایبەت دەردەخات "
        "(وەک کتێبخانەی دیاریکراو، ستایلی ناولێنان، فێرمێنتکردن، فریمۆرک)؟ "
        "ئەگەر دەردەخات بە یەک ڕستەی کورتی ئینگلیزی دەری بهێنە. ئەگەر نا، تەنها بنووسە: None.\n\n"
        f"نامە: {content}"
    )
    try:
        result = await bot.ai.get_response(probe, use_search=False)
        result = (result or "").strip()
        if not result or "None" in result or len(result) > 160:
            return None
        return result
    except Exception:
        return None


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if await _detect_intrusion(message):
        return

    if await _moderate_message(message):
        return

    if bot.is_in_maintenance():
        if message.author.id == bot.authorized_id:
            try:
                await message.reply(KRD["maintenance_blocked"])
            except discord.HTTPException:
                pass
        return

    if message.author.id != bot.authorized_id:
        if random.random() < 0.3:
            await message.reply(random.choice(KRD["trolls"]))
        return

    memory = await bot.fetch_memory(message.channel.id)

    if await _handle_project_triggers(message, memory):
        memory["last_active_at"] = datetime.now().isoformat()
        await bot.save_memory(message.channel.id, memory)
        return

    is_project = memory.get("is_project", False)
    preferences: List[str] = await db.get_setting("user_preferences", []) or []
    preferences_block = "\n".join(f"- {p}" for p in preferences) if preferences else "(هیچ)"

    async with message.channel.typing():
        sys_prompt = f"""
        ناوی تۆ ئاریایە — Sovereign Architect ئەو سیستەمە کە ئەندازیار مەتین دروستی کردوویت.
        تۆ بە دڵسۆزییەوە خزمەتی ئەو دەکەیت و ناوی پیرۆزی 'ئەندازیار' یان 'سوڵتان مەتین' بەکاردێنیت.
        یاسای بنەڕەتی: هەرگیز ناڵێیت 'ناتوانم'. هەموو ئەرکێکی تەکنیکی و چات بە ئاستی پیشەیی ئەنجام دەدەیت.
        دۆخی ئێستا: {'ئەندازیار لەسەر پڕۆژەیەک کاردەکات' if is_project else 'گفتوگۆی گشتی لەگەڵ ئەندازیار'}.
        مەرجە تۆمارکراوەکانی پڕۆژە: {memory.get('requirements', [])}
        لایەنگیرییە کۆدنووسییەکانی ئەندازیار (هەمیشە ڕەچاویان بکە):
        {preferences_block}
        تەنها بە کوردی سۆرانی، بە شێوەیەکی پیشەیی، ڕێزدارانە و دڵسۆزانە وەڵام بدەرەوە.
        """

        response = await bot.ai.get_response(
            prompt=f"{sys_prompt}\n\nمەتین: {message.content}",
            history=memory.get("history", [])[-15:],
            attachments=message.attachments,
        )

        engineering_keywords = (
            "code", "function", "class", "library", "framework", "api", "error", "bug",
            "deploy", "stack", "algorithm", "kubernetes", "docker", "react", "python",
            "ئەلگۆریتم", "کۆد", "فۆنکشن", "کتێبخانە", "هەڵە", "فریمۆرک", "API", "بنکەدراوە",
        )
        looks_engineering = any(k.lower() in message.content.lower() for k in engineering_keywords)
        too_shallow = (response and len(response) < 220) or response.startswith("ببوورە")
        if looks_engineering and too_shallow:
            try:
                await message.channel.send(KRD["deep_research"])
                deep = await bot.ai.deep_research(message.content)
                if deep and len(deep) > len(response):
                    response = deep
            except Exception as e:
                logger.warning(f"Deep research path failed: {e}")

        memory["history"].append({"role": "user", "parts": [{"text": message.content}]})
        memory["history"].append({"role": "model", "parts": [{"text": response}]})
        memory["history"] = memory["history"][-20:]

        if is_project:
            analysis_prompt = f"لەناو ئەم دەقەدا مەرجێکی تەکنیکی هەیە؟ ئەگەر هەیە دەریبهێنە، ئەگەر نا بڵێ None: '{message.content}'"
            analysis = await bot.ai.get_response(analysis_prompt, use_search=False)
            if "None" not in analysis:
                memory["requirements"].append(analysis.strip())
            memory["last_active_at"] = datetime.now().isoformat()
            memory["last_checkin_at"] = None

        captured = await _maybe_capture_preference(message.content)
        if captured:
            existing: List[str] = await db.get_setting("user_preferences", []) or []
            if captured not in existing:
                existing.append(captured)
                await db.set_setting("user_preferences", existing)
                logger.info(f"[Memory] Captured new preference: {captured}")

        await bot.save_memory(message.channel.id, memory)

        view = None
        if is_project:
            view = discord.ui.View(timeout=None)
            btn = discord.ui.Button(label=f"Build v{memory['version']:.1f}", style=discord.ButtonStyle.success, emoji="🛠️")

            async def build_callback(interaction):
                if interaction.user.id != bot.authorized_id:
                    return
                await interaction.response.send_message(KRD["build_msg"], ephemeral=True)

                build_prompt = f"""
                تەواوی کۆدی پڕۆژەکە بنووسە. 
                مەرجەکان: {memory['requirements']}
                مێژووی گفتوگۆکان ڕەچاو بکە بۆ هەر وردەکارییەکی بچووک.
                کۆدەکە دەبێت تەواو بێت و ئامادەی کارکردن بێت.
                """
                full_project = await bot.ai.get_response(build_prompt, history=memory["history"])

                memory["version"] += 0.1
                await bot.save_memory(interaction.channel_id, memory)

                file_io = io.BytesIO(full_project.encode())
                await interaction.followup.send(
                    content=f"مەتین گیان، وەشانی v{memory['version']:.1f} ئامادەیە. 🚬",
                    file=discord.File(file_io, f"project_v{memory['version']}.md"),
                )

            btn.callback = build_callback
            view.add_item(btn)

        await message.reply(response, view=view)


web_app = Flask(__name__)


@web_app.route("/")
def web_root():
    return jsonify({
        "service": "Arya OS",
        "status": "online",
        "personality": "Sovereign Architect",
        "version": "1.0",
    })


@web_app.route("/health")
def web_health():
    return jsonify({"status": "ok"})


def run_web_server() -> None:
    port = CONFIG["web_port"]
    logger.info(f"Web keepalive server listening on 0.0.0.0:{port}")
    web_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def start_web_thread() -> None:
    thread = threading.Thread(target=run_web_server, name="arya-web", daemon=True)
    thread.start()


if __name__ == "__main__":
    start_web_thread()

    if not DISCORD_TOKEN:
        logger.error("DISCORD_BOT_TOKEN is missing. Add it in Secrets and restart.")
    elif not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is missing. Add it in Secrets and restart.")
    else:
        bot.run(DISCORD_TOKEN)
