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

# Cache for translated UI strings: lang -> {english_text -> translated_text}
_ui_cache: dict[str, dict[str, str]] = {}

async def _ui(user_id: int, text: str) -> str:
    """Translate a UI string to the user's preferred language."""
    lang = _user_lang.get(user_id, config.TARGET_LANG)
    if lang.startswith("en"):
        return text
    if lang not in _ui_cache:
        _ui_cache[lang] = {}
    if text not in _ui_cache[lang]:
        try:
            _ui_cache[lang][text] = await voice_handler._translator.translate(text, "en", lang)
        except Exception:
            _ui_cache[lang][text] = text
    return _ui_cache[lang][text]

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

@bot.message_command(name="Translate → Japanese")
async def translate_to_ja(ctx: discord.ApplicationContext, message: discord.Message):
    await _translate_message_to(ctx, message, "ja")


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

class _DeleteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="🗑️", style=discord.ButtonStyle.secondary)
    async def delete(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.message.delete()


async def _do_reaction_translate(message: discord.Message, lang: str, user: discord.User):
    translator = voice_handler._translator
    try:
        result = await translator.translate(message.content, "auto", lang)
    except Exception as e:
        log.error(f"[Reaction] translate error: {e}")
        return
    embed = discord.Embed(color=discord.Color.green())
    embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
    embed.add_field(name="Original", value=message.content, inline=False)
    embed.add_field(name=f"Translation ({lang})", value=result, inline=False)
    embed.set_footer(text=f"Engine: {translator.name}")
    await message.reply(embed=embed, view=_DeleteView())


class _LanguageSelectView(discord.ui.View):
    _OPTIONS = [
        discord.SelectOption(label="Chinese (Simplified)", value="zh-CN", emoji="🇨🇳"),
        discord.SelectOption(label="Chinese (Traditional)", value="zh-TW", emoji="🇹🇼"),
        discord.SelectOption(label="English", value="en", emoji="🇺🇸"),
        discord.SelectOption(label="Japanese", value="ja", emoji="🇯🇵"),
        discord.SelectOption(label="Korean", value="ko", emoji="🇰🇷"),
        discord.SelectOption(label="French", value="fr", emoji="🇫🇷"),
        discord.SelectOption(label="Thai", value="th", emoji="🇹🇭"),
        discord.SelectOption(label="German", value="de", emoji="🇩🇪"),
        discord.SelectOption(label="Spanish", value="es", emoji="🇪🇸"),
        discord.SelectOption(label="Russian", value="ru", emoji="🇷🇺"),
        discord.SelectOption(label="Vietnamese", value="vi", emoji="🇻🇳"),
        discord.SelectOption(label="Indonesian", value="id", emoji="🇮🇩"),
        discord.SelectOption(label="Arabic", value="ar", emoji="🇸🇦"),
    ]

    def __init__(self, message: discord.Message, reactor_id: int):
        super().__init__(timeout=30)
        self.message = message
        self.reactor_id = reactor_id

    @discord.ui.select(placeholder="Select language...", options=_OPTIONS)
    async def select_language(self, select: discord.ui.Select, interaction: discord.Interaction):
        if interaction.user.id != self.reactor_id:
            msg = await _ui(interaction.user.id, "❌ This selection is not for you.")
            await interaction.response.send_message(msg, ephemeral=True)
            return

        lang = select.values[0]
        _user_lang[self.reactor_id] = lang
        self.stop()

        translator = voice_handler._translator
        try:
            result = await translator.translate(self.message.content, "auto", lang)
        except Exception as e:
            log.error(f"[LangSelect] translate error: {e}")
            msg = await _ui(self.reactor_id, "❌ Translation failed.")
            await interaction.response.edit_message(content=msg, view=None)
            return

        saved_msg = await _ui(self.reactor_id, "✅ Language saved")
        embed = discord.Embed(color=discord.Color.green())
        embed.set_author(name=self.message.author.display_name, icon_url=self.message.author.display_avatar.url)
        embed.add_field(name="Original", value=self.message.content, inline=False)
        embed.add_field(name=f"Translation ({lang})", value=result, inline=False)
        embed.set_footer(text=f"{saved_msg} | Engine: {translator.name}")
        await interaction.response.edit_message(content=saved_msg, embed=embed, view=None)

    async def on_timeout(self):
        pass


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

    if payload.user_id not in _user_lang:
        view = _LanguageSelectView(message, payload.user_id)
        prompt = await _ui(payload.user_id, "Select your translation language (🌐 will use it automatically next time):")
        await message.reply(f"<@{payload.user_id}> {prompt}", view=view)
        return

    user = await bot.fetch_user(payload.user_id)
    await _do_reaction_translate(message, _user_lang[payload.user_id], user)

@bot.slash_command(description="Set your personal translation language for 🌐 reactions")
async def my_lang(ctx: discord.ApplicationContext):
    current = _user_lang.get(ctx.author.id, config.TARGET_LANG)
    view = _MyLangView(ctx.author.id)
    await ctx.respond(f"Current language: **{current}**. Select a new language:", view=view, ephemeral=True)


class _MyLangView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=30)
        self.user_id = user_id

    @discord.ui.select(placeholder="Select language...", options=_LanguageSelectView._OPTIONS)
    async def select_language(self, select: discord.ui.Select, interaction: discord.Interaction):
        lang = select.values[0]
        _user_lang[self.user_id] = lang
        self.stop()
        msg = await _ui(self.user_id, f"✅ Translation language set to **{lang}**")
        await interaction.response.edit_message(content=msg, view=None)


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
