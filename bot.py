import discord
from discord.ext import commands
import config
from voice_handler import VoiceHandler

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True

bot = discord.Bot(intents=intents)
voice_handler = VoiceHandler()

@bot.event
async def on_ready():
    print(f"[Bot] Logged in as {bot.user}")
    print(f"[Bot] STT Provider   : {config.STT_PROVIDER.value}")
    print(f"[Bot] Translate      : {config.TRANSLATE_PROVIDER.value}")
    print(f"[Bot] Target Lang    : {config.TARGET_LANG}")
    print(f"[Bot] Record Interval: {config.RECORDING_INTERVAL}s")

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
