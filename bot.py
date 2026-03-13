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

@bot.slash_command(description="加入你所在的语音频道并开始实时翻译")
async def join(ctx: discord.ApplicationContext):
    if not ctx.author.voice:
        await ctx.respond("❌ 你需要先加入一个语音频道！", ephemeral=True)
        return
    channel = ctx.author.voice.channel
    await ctx.respond(f"✅ 已加入 **{channel.name}**，开始翻译（每 {config.RECORDING_INTERVAL} 秒处理一次）...")
    await voice_handler.start(ctx, channel)

@bot.slash_command(description="停止翻译并离开语音频道")
async def leave(ctx: discord.ApplicationContext):
    await voice_handler.stop(ctx)

@bot.slash_command(description="查看当前配置")
async def settings(ctx: discord.ApplicationContext):
    embed = discord.Embed(title="⚙️ 当前配置", color=discord.Color.blue())
    embed.add_field(name="STT 引擎", value=config.STT_PROVIDER.value, inline=True)
    embed.add_field(name="翻译引擎", value=config.TRANSLATE_PROVIDER.value, inline=True)
    embed.add_field(name="源语言", value=config.SOURCE_LANG, inline=True)
    embed.add_field(name="目标语言", value=config.TARGET_LANG, inline=True)
    embed.add_field(name="录音间隔", value=f"{config.RECORDING_INTERVAL} 秒", inline=True)
    embed.add_field(name="Whisper 模型", value=config.WHISPER_MODEL, inline=True)
    await ctx.respond(embed=embed)

@bot.slash_command(description="翻译一段文字")
async def translate(
    ctx: discord.ApplicationContext,
    text: discord.Option(str, "要翻译的文字", required=True),
    target: discord.Option(str, "目标语言代码，如 zh en ja ko fr de（不填则用当前设置）", required=False, default=None),
):
    await ctx.defer()
    lang = target or config.TARGET_LANG
    try:
        from providers import get_translate_provider
        translator = voice_handler._translator
        result = await translator.translate(text, config.SOURCE_LANG, lang)
    except Exception as e:
        log.error(f"Text translate error: {e}")
        await ctx.respond("❌ 翻译失败，请稍后再试。", ephemeral=True)
        return

    embed = discord.Embed(color=discord.Color.green())
    embed.add_field(name="原文", value=text, inline=False)
    embed.add_field(name=f"翻译 ({lang})", value=result, inline=False)
    embed.set_footer(text=f"翻译引擎: {translator.name}")
    await ctx.respond(embed=embed)

@bot.slash_command(description="修改目标翻译语言")
async def set_lang(
    ctx: discord.ApplicationContext,
    lang: discord.Option(str, "语言代码，如 zh en ja ko fr de", required=True)
):
    config.TARGET_LANG = lang
    await ctx.respond(f"✅ 目标语言已设为 **{lang}**")

if not config.DISCORD_TOKEN:
    print("[Error] DISCORD_TOKEN not set in .env file!")
    exit(1)

bot.run(config.DISCORD_TOKEN)
