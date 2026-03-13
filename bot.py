import discord
from discord.ext import commands
import config
from voice_handler import VoiceHandler
from logger import get_logger

log = get_logger("bot")

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True

bot = discord.Bot(intents=intents)
voice_handler = VoiceHandler()

@bot.event
async def on_ready():
    log.info(f"Logged in as {bot.user}")
    log.info(f"STT Provider   : {config.STT_PROVIDER.value}")
    log.info(f"Translate      : {config.TRANSLATE_PROVIDER.value}")
    log.info(f"Target Lang    : {config.TARGET_LANG}")
    log.info(f"Record Interval: {config.RECORDING_INTERVAL}s")

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
    target: discord.Option(str, "Target language code, e.g. zh en ja ko fr de (defaults to current setting)", required=False, default=None),
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
