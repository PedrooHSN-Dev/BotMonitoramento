import discord
import os
import asyncio
from aiohttp import web

# --- 1. Servidor Web Fake (Para manter o Render acordado) ---
async def handle_ping(request):
    return web.Response(text="Bot acordado e monitorando!")

async def run_web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle_ping)])
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"✅ Web server rodando na porta {port}")

# --- 2. Lógica do Bot do Discord ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'✅ Bot conectado como {client.user}')

@client.event
async def on_message(message):
    # Ignora mensagens do próprio bot
    if message.author == client.user:
        return

    # Dicionário de canais e palavras-chave (tudo minúsculo)
    ALERTAS_POR_CANAL = {
        "seed": ["bamboo", "tomato", "cactus", "corn", "pineapple", "tulip", "apple"],
        "fruitprice": ["poison apple", "cactus", "venus flytrap", "acorn", "green bean", "baby cactus", "dragons breath"],
        "weather": ["rain"]
    }

    nome_canal = message.channel.name

    if nome_canal not in ALERTAS_POR_CANAL:
        return

    # Extrai o texto dos embeds
    texto_completo = message.content.lower()
    for embed in message.embeds:
        if embed.title:
            texto_completo += f" {embed.title.lower()}"
        if embed.description:
            texto_completo += f" {embed.description.lower()}"
        for field in embed.fields:
            texto_completo += f" {field.name.lower()} {field.value.lower()}"

    if not texto_completo.strip():
        return

    palavras_chave_do_canal = ALERTAS_POR_CANAL[nome_canal]
    palavras_encontradas = [p for p in palavras_chave_do_canal if p in texto_completo]

    if palavras_encontradas:
        print(f"🔔 Encontrado {palavras_encontradas} no canal #{nome_canal}!")
        
        titulo_alerta = message.embeds[0].title if message.embeds and message.embeds[0].title else "Alerta do Jogo"
        texto_notificacao = f"🔔 **{titulo_alerta}**\n**Canal:** #{nome_canal}\n**Gatilho:** {', '.join(palavras_encontradas).title()}"
        
        try:
            # Puxa o seu ID das variáveis de ambiente e converte para número inteiro
            user_id = int(os.environ.get('DISCORD_USER_ID'))
            
            # Busca o seu usuário no Discord
            user = await client.fetch_user(user_id)
            
            # Envia a mensagem direta
            await user.send(texto_notificacao)
            print("✅ DM enviada com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao enviar DM: {e}")

# --- 3. Inicialização ---
async def main():
    await run_web_server()
    await client.start(os.environ.get('DISCORD_TOKEN'))

if __name__ == "__main__":
    asyncio.run(main())
