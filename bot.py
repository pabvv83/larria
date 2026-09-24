import random
import discord
from discord.ext import commands
from datetime import datetime
import json
import os
from dotenv import load_dotenv
import asyncio
from collections import defaultdict
import time
from flask import Flask
from threading import Thread

# ================== CARREGA .ENV ==================
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ID_CANAL_STATUS = 1497646983287144568

# --- SISTEMA DE CONFIG (JSON) ---
def carregar_json(caminho):
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao ler {caminho}: {e}")
    return {}

def salvar_json(caminho, dados):
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Erro ao salvar {caminho}: {e}")

# ================== EMOJIS (tema aranha/sangue/teia) ==================
EMOJIS = {
    "aura":   "🕷️",
    "heart":  "🩸",
    "laugh":  "🕸️",
    "rage":   "🩸",
    "soviet": "🕷️",
    "think":  "🕸️",
}

# ================== AUTOMOD ANTI-RAID ==================
AUTOMOD_JANELA_SEGUNDOS = 5
AUTOMOD_MSGS_MUTE = 5
AUTOMOD_CANAIS_KICK = 3
AUTOMOD_DURACAO_MUTE = 300

raid_tracker = defaultdict(lambda: {"timestamps": [], "canais": set()})

async def automod_check(message):
    if message.author.bot or not message.guild or message.author.guild_permissions.administrator:
        return

    user_id = message.author.id
    agora = time.time()
    dados = raid_tracker[user_id]

    dados["timestamps"] = [t for t in dados["timestamps"] if agora - t < AUTOMOD_JANELA_SEGUNDOS]

    if "canais_tempo" not in dados:
        dados["canais_tempo"] = []
    dados["canais_tempo"] = [(c, t) for c, t in dados["canais_tempo"] if agora - t < AUTOMOD_JANELA_SEGUNDOS]
    dados["canais"] = {c for c, t in dados["canais_tempo"]}

    dados["timestamps"].append(agora)
    dados["canais_tempo"].append((message.channel.id, agora))
    dados["canais"].add(message.channel.id)

    qtd_msgs = len(dados["timestamps"])
    qtd_canais = len(dados["canais"])

    if qtd_canais >= AUTOMOD_CANAIS_KICK:
        del raid_tracker[user_id]
        try:
            await message.author.kick(reason="[AutoMod Larria] Raid detectado: mensagens em múltiplos canais.")
            await log_status(f"🚨 **AUTOMOD - KICK:** {message.author} (ID: {message.author.id}) mandou msgs em **{qtd_canais} canais diferentes** em {AUTOMOD_JANELA_SEGUNDOS}s.")
            await message.channel.send(f"🚨 **{message.author.display_name}** foi kickado pelo AutoMod. Comportamento de raid detectado! {EMOJIS['rage']}")

            limite_tempo = discord.utils.utcnow() - __import__('datetime').timedelta(hours=12)
            apagadas = 0
            for canal in message.guild.text_channels:
                try:
                    msgs_usuario = [m async for m in canal.history(after=limite_tempo, limit=500) if m.author.id == message.author.id]
                    if msgs_usuario:
                        await canal.delete_messages(msgs_usuario)
                        apagadas += len(msgs_usuario)
                except (discord.Forbidden, discord.HTTPException):
                    pass
            if apagadas:
                await log_status(f"🧹 **AUTOMOD - PURGE:** {apagadas} mensagens das últimas 12h de {message.author} apagadas.")
        except discord.Forbidden:
            await log_status(f"⚠️ AutoMod tentou kickar {message.author} mas não tem permissão.")
        return

    if qtd_msgs >= AUTOMOD_MSGS_MUTE:
        del raid_tracker[user_id]
        try:
            duracao = discord.utils.utcnow() + __import__('datetime').timedelta(seconds=AUTOMOD_DURACAO_MUTE)
            await message.author.timeout(duracao, reason="[AutoMod Larria] Spam detectado.")
            await log_status(f"🔇 **AUTOMOD - MUTE:** {message.author} (ID: {message.author.id}) mandou **{qtd_msgs} msgs** em {AUTOMOD_JANELA_SEGUNDOS}s no mesmo canal.")
            await message.channel.send(f"🔇 **{message.author.display_name}** foi mutado por {AUTOMOD_DURACAO_MUTE // 60} minutos. Calminha no spam! {EMOJIS['rage']}")
        except discord.Forbidden:
            await log_status(f"⚠️ AutoMod tentou mutar {message.author} mas não tem permissão.")

# ================== CONFIGURAÇÃO DO DISCORD ==================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
startup_time = datetime.now()
CONFIG_PATH = "config_servidores.json"

def carregar_config(guild_id: int) -> dict:
    dados = carregar_json(CONFIG_PATH)
    return dados.get(str(guild_id), {})

def salvar_config(guild_id: int, config: dict):
    dados = carregar_json(CONFIG_PATH)
    dados[str(guild_id)] = config
    salvar_json(CONFIG_PATH, dados)

async def log_status(msg):
    canal = bot.get_channel(ID_CANAL_STATUS)
    if canal:
        timestamp = datetime.now().strftime("%H:%M:%S")
        await canal.send(f"🛰️ [`{timestamp}`] **Sistema Larria:** {msg}")

# ================== BOAS-VINDAS ==================
@bot.event
async def on_member_join(member):
    config = carregar_config(member.guild.id)
    canal_id = config.get("canal_boas_vindas", 1497982869790789795)
    canal = member.guild.get_channel(canal_id)
    if not canal: return

    mensagem = (
        f"➡️ **<@{member.id}>**\n"
        f"```ini\n"
        f"LARRIA.EXE // BOOT SEQUENCE INIT\n\n"
        f"[OK] Larria.system loaded.\n"
        f"[OK] Importing modules: events, moderation...\n"
        f"[>>] Scanning for new users...\n"
        f"[>>] User detected: {member.display_name}\n"
        f"[>>] Fetching profile data...\n"
        f"[>>] Access level: GRANTED.\n"
        f"-----------------------------------------\n"
        f"STATUS: CONNECTION ESTABLISHED\n"
        f"-----------------------------------------\n"
        f"```\n"
        f"> Bem-vindo(a) à Biblioteca Ananse.\n"
        f"> 🖥️ >>> Use `!ajuda` para ver os comandos disponíveis.\n"
        f"> 📑 >>> Leia as regras do servidor.\n\n"
        f"```python\n"
        f"if member.is_new():\n"
        f"    print(\"Larria diz: fique à vontade.\")\n"
        f"```\n"
        f"```ini\n"
        f"-----------------------------------------\n"
        f"LRR://ACCESS_GRANTED\n"
        f"-----------------------------------------\n"
        f"```\n"
        f">>> USER_ID=`\"{member.id}\"`"
    )
    await canal.send(mensagem)

@bot.event
async def on_member_remove(member):
    config = carregar_config(member.guild.id)
    canal_id = config.get("canal_boas_vindas", 1497982869790789795)
    canal = member.guild.get_channel(canal_id)
    if not canal: return

    mensagem = (
        f"⬅️ **{member.display_name}**\n"
        f"```ini\n"
        f"LARRIA.EXE // SESSION TERMINATED\n\n"
        f"[OK] Saving user data...\n"
        f"[OK] Closing active connections...\n"
        f"[>>] User: {member.display_name}\n"
        f"[>>] Status: DISCONNECTED\n"
        f"-----------------------------------------\n"
        f"STATUS: CONNECTION LOST\n"
        f"-----------------------------------------\n"
        f"```\n"
        f"> Até a próxima, {member.display_name}. Ou não.\n\n"
        f"```python\n"
        f"if member.left():\n"
        f"    print(\"Larria diz: a porta é ali.\")\n"
        f"```\n"
        f"```ini\n"
        f"-----------------------------------------\n"
        f"LRR://SESSION_CLOSED\n"
        f"-----------------------------------------\n"
        f"```\n"
        f">>> USER_ID=`\"{member.id}\"`"
    )
    await canal.send(mensagem)

@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.idle, activity=discord.CustomActivity(name="Use !ajuda ✨"))
    await log_status(f"Larria **v1.0** ONLINE! Latência: {round(bot.latency * 1000)}ms")
    print(f'✅ Larria v1.0 Online como {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user: return

    await automod_check(message)

    await bot.process_commands(message)

# ================== COMANDOS DE MODERAÇÃO ==================
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, motivo="Falta de aura."):
    await member.kick(reason=motivo)
    await log_status(f"👢 **KICK:** {member.name} (ID: {member.id}) por {ctx.author.name}. Motivo: {motivo}")
    await ctx.send(f"👢 **{member.display_name}** teve que dar no delta! Motivo: {motivo}")

@bot.slash_command(name="kick", description="Expulsa um membro do servidor")
@commands.has_permissions(kick_members=True)
async def slash_kick(ctx: discord.ApplicationContext, membro: discord.Member, motivo: str = "Falta de aura."):
    await kick(ctx, membro, motivo=motivo)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, motivo="Se graduou no banimento."):
    await member.ban(reason=motivo)
    await log_status(f"⚖️ **BAN:** {member.name} (ID: {member.id}) por {ctx.author.name}. Motivo: {motivo}")
    await ctx.send(f"⚖️ **{member.display_name}** se graduou e perdeu -1.000 de aura! {EMOJIS['rage']}")

@bot.slash_command(name="ban", description="Bane um membro permanentemente")
@commands.has_permissions(ban_members=True)
async def slash_ban(ctx: discord.ApplicationContext, membro: discord.Member, motivo: str = "Se graduou no banimento."):
    await ban(ctx, membro, motivo=motivo)

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    try:
        usuario = await bot.fetch_user(user_id)
    except discord.NotFound:
        return await ctx.send("❌ Não achei nenhum usuário com esse ID.")

    try:
        await ctx.guild.unban(usuario, reason=f"Unban solicitado por {ctx.author.name}")
    except discord.NotFound:
        return await ctx.send("❌ Esse usuário não está banido neste servidor.")
    except discord.Forbidden:
        return await ctx.send(f"❌ Não tenho permissão pra desbanir. {EMOJIS['rage']}")

    await log_status(f"♻️ **UNBAN:** {usuario} (ID: {usuario.id}) desbanido por {ctx.author.name}")
    await ctx.send(f"♻️ **{usuario}** foi desbanido(a) e pode voltar pro servidor! {EMOJIS['aura']}")

@bot.slash_command(name="unban", description="Desbane um usuário pelo ID (Apenas ADM)")
@commands.has_permissions(ban_members=True)
async def slash_unban(ctx: discord.ApplicationContext, user_id: str):
    await unban(ctx, int(user_id))

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, quantidade: int):
    if quantidade <= 0:
        return await ctx.send("Como vou limpar 0 mensagens? Ta bebendo água de ar condicionado?")
    deleted = await ctx.channel.purge(limit=quantidade + 1)
    await log_status(f"🧹 **CLEAR:** {len(deleted)-1} mensagens limpas por {ctx.author.name} em #{ctx.channel.name}")
    await ctx.send(f"🧹 Aura purificada! {len(deleted)-1} mensagens deletadas.", delete_after=5)

@bot.slash_command(name="clear", description="Limpa N mensagens do canal")
@commands.has_permissions(manage_messages=True)
async def slash_clear(ctx: discord.ApplicationContext, quantidade: int):
    await clear(ctx, quantidade)

@bot.command()
@commands.has_permissions(administrator=True)
async def automod(ctx):
    embed = discord.Embed(title="🛡️ AutoMod Larria — Configurações", color=0xFF4444)
    embed.add_field(name="⏱️ Janela de tempo", value=f"`{AUTOMOD_JANELA_SEGUNDOS}` segundos", inline=True)
    embed.add_field(name="🔇 Mute após", value=f"`{AUTOMOD_MSGS_MUTE}` msgs no mesmo canal", inline=True)
    embed.add_field(name="👢 Kick após", value=f"`{AUTOMOD_CANAIS_KICK}` canais diferentes", inline=True)
    embed.add_field(name="⏳ Duração do mute", value=f"`{AUTOMOD_DURACAO_MUTE // 60}` minutos", inline=True)
    embed.set_footer(text="Edite as constantes AUTOMOD_* no código pra ajustar.")
    await ctx.send(embed=embed)

@bot.slash_command(name="automod", description="Exibe configurações do AutoMod (Apenas ADM)")
@commands.has_permissions(administrator=True)
async def slash_automod(ctx: discord.ApplicationContext):
    await automod(ctx)

# ================== CONFIG DO SERVIDOR ==================
@bot.command()
@commands.has_permissions(administrator=True)
async def prefixo(ctx, novo: str = None):
    if not novo:
        return await ctx.send(f"O prefixo atual é `{bot.command_prefix}`. Use `!prefixo [novo]` pra trocar.")
    if len(novo) > 5:
        return await ctx.send("Prefixo muito longo, choom. Máximo 5 caracteres.")
    bot.command_prefix = novo
    await log_status(f"🔧 **PREFIXO:** Trocado para `{novo}` por {ctx.author.name} em {ctx.guild.name}")
    await ctx.send(f"✅ Prefixo updated para `{novo}` neste servidor!")

@bot.slash_command(name="prefixo", description="Muda o prefixo do bot (Apenas ADM)")
@commands.has_permissions(administrator=True)
async def slash_prefixo(ctx: discord.ApplicationContext, novo: str):
    await prefixo(ctx, novo)

@bot.command()
@commands.has_permissions(administrator=True)
async def setwelcome(ctx, canal: discord.TextChannel = None):
    canal = canal or ctx.channel
    config = carregar_config(ctx.guild.id)
    config["canal_boas_vindas"] = canal.id
    salvar_config(ctx.guild.id, config)
    await log_status(f"📌 **SETWELCOME:** Canal de boas-vindas de {ctx.guild.name} definido como #{canal.name} por {ctx.author.name}")
    await ctx.send(f"✅ Canal de boas-vindas e saída definido como {canal.mention}!")

@bot.slash_command(name="setwelcome", description="Define o canal de boas-vindas deste servidor (Apenas ADM)")
@commands.has_permissions(administrator=True)
async def slash_setwelcome(ctx: discord.ApplicationContext, canal: discord.TextChannel = None):
    await setwelcome(ctx, canal)

@bot.command()
async def status(ctx):
    latencia = round(bot.latency * 1000)
    embed = discord.Embed(title="📊 Status da Larria", color=0x00FF00)
    embed.add_field(name="Ping", value=f"{latencia}ms", inline=True)
    embed.add_field(name="Servidores", value=len(bot.guilds), inline=True)
    await ctx.send(embed=embed)

@bot.slash_command(name="status", description="Status técnico do bot")
async def slash_status(ctx: discord.ApplicationContext):
    await status(ctx)

# ================== SOBRE ==================
@bot.command()
async def sobre(ctx):
    embed = discord.Embed(
        title="ℹ️ Sobre a Larria",
        description=(
            "A **Larria** é um bot de administração de servidores, "
            "criada por **@pabvv83** para o servidor **Biblioteca Ananse**."
        ),
        color=0x7000FF
    )
    embed.set_footer(text="LRR://ABOUT")
    await ctx.send(embed=embed)

@bot.slash_command(name="sobre", description="Mostra informações sobre a Larria")
async def slash_sobre(ctx: discord.ApplicationContext):
    await sobre(ctx)

# ================== SERVIDOR & UTILITÁRIOS ==================
@bot.command()
async def serverinfo(ctx):
    g = ctx.guild
    total_membros = g.member_count
    bots = sum(1 for m in g.members if m.bot)
    humanos = total_membros - bots
    online = sum(1 for m in g.members if m.status != discord.Status.offline and not m.bot)
    criado_em = g.created_at.strftime("%d/%m/%Y")
    boost_level = g.premium_tier
    boosts = g.premium_subscription_count
    canais_texto = len(g.text_channels)
    canais_voz = len(g.voice_channels)
    cargos = len(g.roles) - 1

    embed = discord.Embed(title=f"🌆 {g.name}", color=0x7000FF)
    embed.set_thumbnail(url=g.icon.url if g.icon else discord.Embed.Empty)
    embed.add_field(name="👤 Dono", value=g.owner.mention if g.owner else "N/A", inline=True)
    embed.add_field(name="🆔 ID", value=f"`{g.id}`", inline=True)
    embed.add_field(name="📅 Criado em", value=criado_em, inline=True)
    embed.add_field(name="👥 Membros", value=f"Total: **{total_membros}** | Humanos: **{humanos}** | Bots: **{bots}**", inline=False)
    embed.add_field(name="🟢 Online", value=f"**{online}** humanos agora", inline=True)
    embed.add_field(name="📢 Canais", value=f"💬 {canais_texto} texto | 🔊 {canais_voz} voz", inline=True)
    embed.add_field(name="🏷️ Cargos", value=f"**{cargos}**", inline=True)
    embed.add_field(name="🚀 Boost", value=f"Nível **{boost_level}** com **{boosts}** boosts", inline=True)
    embed.set_footer(text="LRR://SERVER_SCAN_COMPLETE")
    await ctx.send(embed=embed)

@bot.slash_command(name="serverinfo", description="Informações detalhadas do servidor")
async def slash_serverinfo(ctx: discord.ApplicationContext):
    await serverinfo(ctx)

@bot.command()
async def userinfo(ctx, membro: discord.Member = None):
    membro = membro or ctx.author
    entrou_em = membro.joined_at.strftime("%d/%m/%Y às %H:%M") if membro.joined_at else "Desconhecido"
    criado_em = membro.created_at.strftime("%d/%m/%Y")
    eh_adm = membro.guild_permissions.administrator

    embed = discord.Embed(title=f"🪪 Ficha de {membro.display_name}", color=0x7000FF)
    embed.set_thumbnail(url=membro.display_avatar.url)
    embed.add_field(name="🆔 ID", value=f"`{membro.id}`", inline=True)
    embed.add_field(name="🤖 Bot?", value="Sim" if membro.bot else "Não", inline=True)
    embed.add_field(name="🛡️ Adm", value="Sim" if eh_adm else "Não", inline=True)
    embed.add_field(name="📅 Conta criada em", value=criado_em, inline=True)
    embed.add_field(name="➡️ Entrou no servidor em", value=entrou_em, inline=True)
    embed.set_footer(text="LRR://USER_SCAN_COMPLETE")
    await ctx.send(embed=embed)

@bot.slash_command(name="userinfo", description="Mostra informações detalhadas de um usuário")
async def slash_userinfo(ctx: discord.ApplicationContext, membro: discord.Member = None):
    await userinfo(ctx, membro)

@bot.command()
async def avatar(ctx, membro: discord.Member = None):
    membro = membro or ctx.author
    embed = discord.Embed(title=f"🖼️ Avatar de {membro.display_name}", color=0x7000FF)
    embed.set_image(url=membro.display_avatar.url)
    embed.set_footer(text=f"ID: {membro.id}")
    await ctx.send(embed=embed)

@bot.slash_command(name="avatar", description="Mostra o avatar de um usuário em tamanho cheio")
async def slash_avatar(ctx: discord.ApplicationContext, membro: discord.Member = None):
    await avatar(ctx, membro)

@bot.command()
async def uptime(ctx):
    delta = datetime.now() - startup_time
    horas, resto = divmod(int(delta.total_seconds()), 3600)
    minutos, segundos = divmod(resto, 60)
    dias = delta.days
    horas = horas % 24

    embed = discord.Embed(title="⏱️ Uptime da Larria", color=0x7000FF)
    embed.add_field(name="Online há", value=f"**{dias}d {horas}h {minutos}m {segundos}s**", inline=False)
    embed.add_field(name="🏓 Latência", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.set_footer(text="LRR://SYSTEM_UPTIME")
    await ctx.send(embed=embed)

@bot.slash_command(name="uptime", description="Mostra há quanto tempo a Larria está online")
async def slash_uptime(ctx: discord.ApplicationContext):
    await uptime(ctx)

# ================== DIVERSÃO ==================
@bot.command()
async def aura(ctx, alvo: discord.Member = None):
    alvo = alvo or ctx.author
    valor = random.randint(0, 100)

    if valor == 100:
        msg = f"{EMOJIS['aura']} **{alvo.mention} farma muita aura!** {EMOJIS['aura']}\n> `AURA: {valor}%` — LENDÁRIO."
    elif valor >= 75:
        msg = f"{EMOJIS['aura']} **{alvo.mention}** tá bem de aura.\n> `AURA: {valor}%`"
    elif valor >= 50:
        msg = f"**{alvo.mention}** sobreviveu. Por enquanto.\n> `AURA: {valor}%`"
    elif valor >= 25:
        msg = f"**{alvo.mention}** tá na zona de risco de virar neandertal.\n> `AURA: {valor}%` {EMOJIS['laugh']}"
    elif valor == 0:
        msg = f"{EMOJIS['rage']} **{alvo.mention} anda farmando muita aura de neandertal...**\n> `AURA: {valor}%` — CRÍTICO."
    else:
        msg = f"**{alvo.mention}** tá precisando treinar mais.\n> `AURA: {valor}%` {EMOJIS['rage']}"

    await ctx.send(msg)

@bot.slash_command(name="aura", description="Rola a aura de alguém (0% a 100%)")
async def slash_aura(ctx: discord.ApplicationContext, alvo: discord.Member = None):
    await aura(ctx, alvo)

@bot.command()
async def d20(ctx):
    resultado = random.randint(1, 20)

    if resultado == 20:
        msg = f"🎲 O dado deu **20**! Crítico! {EMOJIS['aura']}"
    elif resultado == 1:
        msg = f"🎲 O dado deu **1**. Falha crítica. Que vergonha, {ctx.author.mention}. {EMOJIS['laugh']}"
    elif resultado >= 15:
        msg = f"🎲 O dado deu **{resultado}**. Bom resultado."
    elif resultado >= 8:
        msg = f"🎲 O dado deu **{resultado}**. Mediano, como esperado."
    else:
        msg = f"🎲 O dado deu **{resultado}**. Tá ruim pra você. {EMOJIS['rage']}"

    await ctx.send(msg)

@bot.slash_command(name="d20", description="Rola um dado de 20 lados")
async def slash_d20(ctx: discord.ApplicationContext):
    await d20(ctx)

@bot.command(name="path")
async def lifepath(ctx, alvo: discord.Member = None):
    alvo = alvo or ctx.author
    escolha = random.choice(["Nomad", "Street Kid", "Corpo"])

    descricoes = {
        "Nomad": f"{EMOJIS['aura']} **{alvo.mention}** rola um Life Path: **Nomad**.\n> Cresceu na estrada, longe das megacorps. Família é tudo — sangue ou não.",
        "Street Kid": f"{EMOJIS['laugh']} **{alvo.mention}** rola um Life Path: **Street Kid**.\n> Nasceu e se criou nas ruas. Conhece Night City melhor que a própria cara.",
        "Corpo": f"{EMOJIS['soviet']} **{alvo.mention}** rola um Life Path: **Corpo**.\n> Formado dentro de uma corporação. Ambição e traição no sangue.",
    }
    await ctx.send(descricoes[escolha])

@bot.slash_command(name="path", description="Sorteia um Life Path do universo Cyberpunk")
async def slash_path(ctx: discord.ApplicationContext, alvo: discord.Member = None):
    await lifepath(ctx, alvo)

# ================== AJUDA ==================
@bot.command(name="ajuda")
async def ajuda(ctx):
    embed = discord.Embed(title="🤖 Central de Comando Larria", color=0x7000FF)
    embed.add_field(name="🛡️ Moderação", value="`!kick`, `!ban`, `!unban [ID]`, `!clear [N]`, `!automod` (ADM)", inline=False)
    embed.add_field(name="⚙️ Config", value="`!prefixo` (ADM), `!setwelcome` (ADM), `!status`", inline=False)
    embed.add_field(name="🌆 Servidor", value="`!serverinfo`, `!userinfo [@user]`, `!avatar`, `!uptime`", inline=True)
    embed.add_field(name="🎲 Diversão", value="`!aura [@user]`, `!d20`, `!path [@user]`", inline=True)
    embed.add_field(name="ℹ️ Outros", value="`!sobre`", inline=True)
    embed.set_footer(text="Larria — Todos os comandos disponíveis também como /slash")
    await ctx.send(embed=embed)

@bot.slash_command(name="ajuda", description="Painel de ajuda completo")
async def slash_ajuda(ctx: discord.ApplicationContext):
    await ajuda(ctx)

# ================== TRATAMENTO DE ERROS ==================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply(f"Calma aí, professor Hiro! Você não tem aura suficiente pra usar esse comando. {EMOJIS['rage']}")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.reply("Não achei esse usuário no servidor.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(f"Tá faltando coisa no comando! Use `!ajuda` pra ver como faz.")
    else:
        print(f"Erro ignorado: {error}")

# ================== KEEP-ALIVE (FLASK) ==================
# Servidor HTTP mínimo só pra dar sinal de vida pro monitor (UptimeRobot/etc)
# e o Render não deixar o Web Service dormir por "falta de atividade".
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Larria tá online e de olho em vocês. 👁️"

@app_flask.route('/health')
def health():
    return {"status": "ok", "latencia_ms": round(bot.latency * 1000) if bot.is_ready() else None}, 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

async def main():
    async with bot:
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    keep_alive()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
