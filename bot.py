import discord
from discord.ext import commands
import config
from voice_handler import VoiceHandler
from logger import get_logger

log = get_logger("bot")

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.reactions = True

# Cache of user_id → preferred language (learned from interaction locale)
_user_lang: dict[int, str] = {}

def _get_lang_for_user(user_id: int) -> str:
    return _user_lang.get(user_id, config.TARGET_LANG)

def _save_user_locale(interaction: discord.Interaction):
    locale = str(interaction.locale)
    lang = _LOCALE_TO_LANG.get(locale, locale.split("-")[0])
    _user_lang[interaction.user.id] = lang

# Discord locale code → translation language code
_LOCALE_TO_LANG = {
    "zh-CN": "zh-CN", "zh-TW": "zh-TW",
    "en-US": "en", "en-GB": "en",
    "ko": "ko", "ja": "ja",
    "fr": "fr", "de": "de", "es-ES": "es",
    "pt-BR": "pt", "ru": "ru", "pl": "pl",
    "tr": "tr", "it": "it", "vi": "vi",
    "th": "th", "ar": "ar", "id": "id",
    "hi": "hi", "nl": "nl", "sv-SE": "sv",
    "da": "da", "fi": "fi", "ro": "ro",
    "hu": "hu", "cs": "cs", "uk": "uk",
    "bg": "bg", "hr": "hr", "el": "el",
    "no": "no",
}

bot = discord.Bot(intents=intents)
voice_handler = VoiceHandler()

@bot.event
async def on_ready():
    log.info(f"Logged in as {bot.user}")
    log.info(f"STT Provider   : {config.STT_PROVIDER.value}")
    log.info(f"Translate      : {config.TRANSLATE_PROVIDER.value}")
    log.info(f"Target Lang    : {config.TARGET_LANG}")
    log.info(f"Record Interval: {config.RECORDING_INTERVAL}s")
    if config.ALLOWED_GUILDS:
        log.info(f"Allowed guilds : {config.ALLOWED_GUILDS}")
    else:
        log.warning("ALLOWED_GUILDS is empty — bot will accept all servers")

@bot.event
async def on_guild_join(guild: discord.Guild):
    if config.ALLOWED_GUILDS and guild.id not in config.ALLOWED_GUILDS:
        log.warning(f"Unauthorized guild joined: {guild.name} ({guild.id}), leaving...")
        await guild.leave()
        return
    log.info(f"Joined guild: {guild.name} ({guild.id})")

@bot.slash_command(description="Join your voice channel and start real-time translation")
async def join(ctx: discord.ApplicationContext):
    if not ctx.author.voice:
        await ctx.respond("❌ You need to join a voice channel first!", ephemeral=True)
        return
    channel = ctx.author.voice.channel
    await ctx.respond(f"✅ Joined **{channel.name}**, translation started (every {config.RECORDING_INTERVAL}s)...")
    await voice_handler.start(ctx, channel)

@bot.slash_command(description="Stop translating and leave the voice channel")
async def leave(ctx: discord.ApplicationContext):
    await voice_handler.stop(ctx)

@bot.slash_command(description="View current configuration")
async def settings(ctx: discord.ApplicationContext):
    embed = discord.Embed(title="⚙️ Current Settings", color=discord.Color.blue())
    embed.add_field(name="STT Engine", value=config.STT_PROVIDER.value, inline=True)
    embed.add_field(name="Translate Engine", value=config.TRANSLATE_PROVIDER.value, inline=True)
    embed.add_field(name="Source Language", value=config.SOURCE_LANG, inline=True)
    embed.add_field(name="Target Language", value=config.TARGET_LANG, inline=True)
    embed.add_field(name="Record Interval", value=f"{config.RECORDING_INTERVAL}s", inline=True)
    embed.add_field(name="Whisper Model", value=config.WHISPER_MODEL, inline=True)
    await ctx.respond(embed=embed)

@bot.slash_command(description="Translate a text message")
async def translate(
    ctx: discord.ApplicationContext,
    text: discord.Option(str, "Text to translate", required=True),
    target: discord.Option(str, "Target language (defaults to current setting)", required=False, default=None, choices=[
        discord.OptionChoice("Chinese (Simplified)", "zh-CN"),
        discord.OptionChoice("Chinese (Traditional)", "zh-TW"),
        discord.OptionChoice("English", "en"),
        discord.OptionChoice("Korean", "ko"),
        discord.OptionChoice("Japanese", "ja"),
        discord.OptionChoice("French", "fr"),
        discord.OptionChoice("Thai", "th"),
        discord.OptionChoice("German", "de"),
        discord.OptionChoice("Spanish", "es"),
    ]),
):
    await ctx.defer()
    lang = target or config.TARGET_LANG
    translator = voice_handler._translator
    try:
        result = await translator.translate(text, config.SOURCE_LANG, lang)
    except Exception as e:
        log.error(f"Text translate error: {e}")
        await ctx.followup.send("❌ Translation failed, please try again.")
        return

    embed = discord.Embed(color=discord.Color.green())
    embed.add_field(name="Original", value=text, inline=False)
    embed.add_field(name=f"Translation ({lang})", value=result, inline=False)
    embed.set_footer(text=f"Engine: {translator.name}")
    await ctx.followup.send(embed=embed)

async def _translate_message_to(ctx: discord.ApplicationContext, message: discord.Message, lang: str):
    _save_user_locale(ctx.interaction)
    await ctx.defer(ephemeral=True)
    if not message.content:
        await ctx.followup.send("❌ This message has no text to translate.", ephemeral=True)
        return

    translator = voice_handler._translator
    try:
        result = await translator.translate(message.content, "auto", lang)
    except Exception as e:
        log.error(f"Message translate error: {e}")
        await ctx.followup.send("❌ Translation failed, please try again.", ephemeral=True)
        return

    embed = discord.Embed(color=discord.Color.green())
    embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
    embed.add_field(name="Original", value=message.content, inline=False)
    embed.add_field(name=f"Translation ({lang})", value=result, inline=False)
    embed.set_footer(text=f"Engine: {translator.name}")
    await ctx.followup.send(embed=embed, ephemeral=True)

@bot.message_command(name="Translate → Chinese")
async def translate_to_zh(ctx: discord.ApplicationContext, message: discord.Message):
    await _translate_message_to(ctx, message, "zh-CN")

@bot.message_command(name="Translate → English")
async def translate_to_en(ctx: discord.ApplicationContext, message: discord.Message):
    await _translate_message_to(ctx, message, "en")

@bot.message_command(name="Translate → Korean")
async def translate_to_ko(ctx: discord.ApplicationContext, message: discord.Message):
    await _translate_message_to(ctx, message, "ko")


@bot.message_command(name="Translate → My Language")
async def translate_to_my_lang(ctx: discord.ApplicationContext, message: discord.Message):
    log.info(f"[MyLang] invoked by user={ctx.author.id} guild={ctx.guild_id} locale={ctx.interaction.locale}")
    try:
        locale = str(ctx.interaction.locale)
        lang = _LOCALE_TO_LANG.get(locale, locale.split("-")[0])
        _user_lang[ctx.author.id] = lang
        await _translate_message_to(ctx, message, lang)
    except Exception as e:
        log.error(f"[MyLang] error: {e}", exc_info=True)

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    log.info(f"[Reaction] emoji={str(payload.emoji)!r} user={payload.user_id}")
    if str(payload.emoji) != "🌐":
        return
    if payload.user_id == bot.user.id:
        return

    channel = bot.get_channel(payload.channel_id)
    if not channel:
        try:
            channel = await bot.fetch_channel(payload.channel_id)
        except Exception as e:
            log.error(f"[Reaction] fetch_channel failed: {e}")
            return
    log.info(f"[Reaction] channel={channel}")
    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception as e:
        log.error(f"[Reaction] fetch_message failed: {e}")
        return
    log.info(f"[Reaction] message.content={message.content!r}")
    if not message.content:
        log.warning("[Reaction] message has no text content, skipping")
        return

    lang = _get_lang_for_user(payload.user_id)
    translator = voice_handler._translator
    try:
        result = await translator.translate(message.content, "auto", lang)
    except Exception as e:
        log.error(f"[Reaction] translate error: {e}")
        return

    log.info(f"[Reaction] translation result={result!r}")
    embed = discord.Embed(color=discord.Color.green())
    embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
    embed.add_field(name="Original", value=message.content, inline=False)
    embed.add_field(name=f"Translation ({lang})", value=result, inline=False)
    embed.set_footer(text=f"Engine: {translator.name} | React with 🌐 to translate")
    try:
        await message.reply(embed=embed)
        log.info("[Reaction] reply sent successfully")
    except Exception as e:
        log.error(f"[Reaction] reply failed: {e}", exc_info=True)

@bot.slash_command(description="Change the target translation language")
async def set_lang(
    ctx: discord.ApplicationContext,
    lang: discord.Option(str, "Language code, e.g. zh en ja ko fr de", required=True)
):
    config.TARGET_LANG = lang
    await ctx.respond(f"✅ Target language set to **{lang}**")

if not config.DISCORD_TOKEN:
    print("[Error] DISCORD_TOKEN not set in .env file!")
    exit(1)

bot.run(config.DISCORD_TOKEN)
