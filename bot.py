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
    # Ignora mensagens do próprio bot que estamos criando
    if message.author == client.user:
        return

    # 1. Configuração do que procurar em cada canal (nomes exatos dos canais do print)
    # IMPORTANTE: Escreva todas as palavras em minúsculo aqui!
    ALERTAS_POR_CANAL = {
        "seed": ["bamboo", "tomato", "cactus"],
        "fruitprice": ["poison apple", "cactus", "venus flytrap"],
        "weather": ["rain"]
    }

    nome_canal = message.channel.name

    # Se a mensagem chegar em um canal que não está na lista acima, o bot ignora
    if nome_canal not in ALERTAS_POR_CANAL:
        return

    # 2. Extraindo o texto de dentro dos Embeds (as caixas do G4G2_BOT)
    texto_completo = message.content.lower()
    
    for embed in message.embeds:
        if embed.title:
            texto_completo += f" {embed.title.lower()}"
        if embed.description:
            texto_completo += f" {embed.description.lower()}"
        for field in embed.fields:
            texto_completo += f" {field.name.lower()} {field.value.lower()}"

    # Se a mensagem for vazia mesmo após procurar nos embeds, ignora
    if not texto_completo.strip():
        return

    # 3. Puxa a lista de palavras-chave correspondente ao canal que recebeu a mensagem
    palavras_chave_do_canal = ALERTAS_POR_CANAL[nome_canal]

    # Verifica se alguma das palavras foi encontrada dentro do texto extraído
    palavras_encontradas = [p for p in palavras_chave_do_canal if p in texto_completo]

    if palavras_encontradas:
        print(f"🔔 Encontrado {palavras_encontradas} no canal #{nome_canal}!")
        
        # Como o texto do embed inteiro é longo e bagunçado, vamos pegar só o Título Principal para o WhatsApp
        titulo_alerta = message.embeds[0].title if message.embeds and message.embeds[0].title else "Alerta do Jogo"
        
        # Formata uma mensagem limpa e direta para o seu WhatsApp
        texto_notificacao = f"🔔 *{titulo_alerta}*\nCanal: #{nome_canal}\nGatilho: {', '.join(palavras_encontradas)}"
        texto_codificado = urllib.parse.quote(texto_notificacao)
        
        # Puxa as variáveis de ambiente
        phone = os.environ.get('WHATSAPP_PHONE')
        apikey = os.environ.get('CALLMEBOT_KEY')
        
        # Dispara para o WhatsApp via CallMeBot
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