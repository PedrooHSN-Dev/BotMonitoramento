import discord
import requests
import urllib.parse
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
    if message.author == client.user:
        return

    PALAVRA_CHAVE = "urgente" # Coloque sua palavra aqui (tudo em minúsculo)
    
    if PALAVRA_CHAVE in message.content.lower():
        print("🔔 Palavra-chave detectada!")
        
        # Formata o texto para o WhatsApp
        texto_notificacao = f"🔔 *Alerta do Discord*\nCanal: {message.channel.name}\n\n{message.content}"
        texto_codificado = urllib.parse.quote(texto_notificacao)
        
        # Puxa as variáveis de ambiente
        phone = os.environ.get('WHATSAPP_PHONE')
        apikey = os.environ.get('CALLMEBOT_KEY')
        
        # Dispara via CallMeBot
        url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={texto_codificado}&apikey={apikey}"
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print("✅ Mensagem enviada para o WhatsApp!")
        except Exception as e:
            print(f"❌ Erro ao enviar: {e}")

# --- 3. Inicialização ---
async def main():
    await run_web_server()
    await client.start(os.environ.get('DISCORD_TOKEN'))

if __name__ == "__main__":
    asyncio.run(main())