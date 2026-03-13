import asyncio
import io
import discord
import config
from providers import get_stt_provider, get_translate_provider
from logger import get_logger

log = get_logger("voice_handler")

# Patch for Discord DAVE protocol (E2EE voice, mandatory since late 2024)
# Without dave_protocol_version in SELECT_PROTOCOL, Discord closes with 4017

import discord.gateway as _discord_gateway

# Patch identify to include max_dave_protocol_version (required since late 2024)
_orig_identify = _discord_gateway.DiscordVoiceWebSocket.identify

async def _dave_identify(self):
    state = self._connection
    payload = {
        "op": self.IDENTIFY,
        "d": {
            "server_id": str(state.server_id),
            "user_id": str(state.user.id),
            "session_id": state.session_id,
            "token": state.token,
            "max_dave_protocol_version": 0,
        },
    }
    log.info("[DAVEPatch] Sending IDENTIFY with max_dave_protocol_version=1")
    await self.send_as_json(payload)

_discord_gateway.DiscordVoiceWebSocket.identify = _dave_identify

_orig_select_protocol = _discord_gateway.DiscordVoiceWebSocket.select_protocol

async def _dave_select_protocol(self, ip, port, mode):
    log.info(f"[DAVEPatch] select_protocol called: ip={ip} port={port} mode={mode}")
    payload = {
        "op": self.SELECT_PROTOCOL,
        "d": {
            "protocol": "udp",
            "data": {"address": ip, "port": port, "mode": mode},
            "dave_protocol_version": 0,
        },
    }
    await self.send_as_json(payload)
    log.info("[DAVEPatch] SELECT_PROTOCOL sent with dave_protocol_version=1")

_discord_gateway.DiscordVoiceWebSocket.select_protocol = _dave_select_protocol

_orig_received_message = _discord_gateway.DiscordVoiceWebSocket.received_message

async def _dave_received_message(self, msg):
    op = msg.get("op")
    data = msg.get("d") or {}
    log.debug(f"[DAVEPatch] Voice WS opcode: {op}")
    if op == 21:  # DAVE_PREPARE_TRANSITION
        transition_id = data.get("transition_id", 0)
        self.seq_ack = data.get("seq", getattr(self, "seq_ack", 0))
        log.info(f"[DAVEPatch] DAVE_PREPARE_TRANSITION received, sending TRANSITION_READY transition_id={transition_id}")
        await self.send_as_json({"op": 23, "d": {"transition_id": transition_id}})
        await self._hook(self, msg)
        return
    if 22 <= op <= 31:  # Other DAVE opcodes
        log.info(f"[DAVEPatch] Ignoring DAVE opcode {op}")
        await self._hook(self, msg)
        return
    await _orig_received_message(self, msg)

_discord_gateway.DiscordVoiceWebSocket.received_message = _dave_received_message

# Keep connect_websocket debug logging
_original_connect_ws = discord.VoiceClient.connect_websocket

async def _patched_connect_ws(self):
    try:
        return await _original_connect_ws(self)
    except Exception as e:
        log.error(f"[VoiceDebug] connect_websocket failed: {type(e).__name__}: {e}", exc_info=True)
        raise

discord.VoiceClient.connect_websocket = _patched_connect_ws

# Minimum WAV file bytes for MIN_AUDIO_SECONDS of audio
# Formula: 44 (header) + 48000 * 2 channels * 2 bytes/sample * seconds
def _min_bytes(seconds: float) -> int:
    return 44 + int(192000 * seconds)

class VoiceHandler:
    def __init__(self):
        self._sessions: dict = {}  # guild_id -> session
        self._stt = get_stt_provider()
        self._translator = get_translate_provider()
        log.info(f"STT: {self._stt.name}")
        log.info(f"Translator: {self._translator.name}")

    async def start(self, ctx: discord.ApplicationContext, voice_channel: discord.VoiceChannel):
        guild_id = ctx.guild.id
        log.info(f"Starting voice session for guild {guild_id}")

        try:
            # Connect or move
            if ctx.guild.voice_client:
                vc = ctx.guild.voice_client
                log.info(f"Moving to channel {voice_channel.name}")
                await vc.move_to(voice_channel)
            else:
                log.info(f"Connecting to channel {voice_channel.name}")
                vc = await voice_channel.connect()

            # Force _connected to bypass py-cord bug where it's never set
            await asyncio.sleep(3)
            vc._connected.set()
            log.info(f"Voice connection forced ready, ws={vc.ws}")

            self._sessions[guild_id] = {
                "vc": vc,
                "text_channel": ctx.channel,
                "active": True,
            }

            log.info(f"Creating recording loop task for guild {guild_id}")
            asyncio.create_task(self._recording_loop(guild_id))
        except Exception as e:
            log.error(f"Failed to start voice session: {e}", exc_info=True)

    async def stop(self, ctx: discord.ApplicationContext):
        guild_id = ctx.guild.id
        session = self._sessions.get(guild_id)
        if not session:
            await ctx.respond("Bot is not currently in a voice channel.", ephemeral=True)
            return

        session["active"] = False
        vc = session["vc"]
        if vc.recording:
            vc.stop_recording()
        await vc.disconnect()
        del self._sessions[guild_id]
        await ctx.respond("Stopped translating and left the voice channel.")

    async def _recording_loop(self, guild_id: int):
        session = self._sessions.get(guild_id)
        if not session:
            return

        queue: asyncio.Queue = asyncio.Queue()

        async def on_finished(sink, *args):
            await queue.put(sink)

        vc = session["vc"]

        log.debug(f"Recording loop started for guild {guild_id}")
        while guild_id in self._sessions and self._sessions[guild_id]["active"]:
            try:
                log.debug(f"Starting recording for guild {guild_id}")
                sink = discord.sinks.WaveSink()
                vc.start_recording(sink, on_finished)

                await asyncio.sleep(config.RECORDING_INTERVAL)

                if vc.recording:
                    log.debug(f"Stopping recording for guild {guild_id}")
                    vc.stop_recording()
                else:
                    log.warning(f"vc.recording is False before stop for guild {guild_id}")

                # Wait for callback (timeout = interval + 3s buffer)
                finished_sink = await asyncio.wait_for(queue.get(), timeout=config.RECORDING_INTERVAL + 3)
                log.debug(f"Got sink for guild {guild_id}")
                asyncio.create_task(self._process_sink(finished_sink, guild_id))

            except asyncio.TimeoutError:
                log.warning(f"Recording callback timed out for guild {guild_id}")
            except Exception as e:
                log.error(f"Recording loop error: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _process_sink(self, sink: discord.sinks.WaveSink, guild_id: int):
        session = self._sessions.get(guild_id)
        if not session:
            return

        text_channel: discord.TextChannel = session["text_channel"]
        guild = text_channel.guild
        min_size = _min_bytes(config.MIN_AUDIO_SECONDS)

        log.debug(f"Processing sink: {len(sink.audio_data)} user(s) captured")

        for user_id, audio in sink.audio_data.items():
            audio_file: io.BytesIO = audio.file

            # Check audio length
            audio_file.seek(0, 2)
            size = audio_file.tell()
            audio_file.seek(0)
            log.debug(f"User {user_id} audio size: {size} bytes (min: {min_size})")
            if size < min_size:
                log.debug(f"Skipping user {user_id}: audio too short")
                continue

            # STT
            try:
                text = await self._stt.transcribe(audio_file, config.SOURCE_LANG)
            except Exception as e:
                log.error(f"STT error user={user_id}: {e}")
                continue

            if not text or len(text.strip()) < 2:
                continue

            # Translate
            try:
                translation = await self._translator.translate(text, config.SOURCE_LANG, config.TARGET_LANG)
            except Exception as e:
                log.error(f"Translate error: {e}")
                translation = "⚠️ Translation failed"

            # Send embed to text channel
            member = guild.get_member(user_id)
            display_name = member.display_name if member else str(user_id)
            avatar_url = member.display_avatar.url if member else None

            embed = discord.Embed(color=discord.Color.blurple())
            embed.set_author(name=display_name, icon_url=avatar_url)
            embed.add_field(name="Original", value=text, inline=False)
            embed.add_field(name=f"Translation ({config.TARGET_LANG})", value=translation, inline=False)
            embed.set_footer(text=f"STT: {self._stt.name} | Translate: {self._translator.name}")

            await text_channel.send(embed=embed)
