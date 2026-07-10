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

ALERTAS_POR_CANAL = {
    "seed": ["bamboo", "tomato", "cactus"],
    "fruitprice": ["poison apple", "cactus", "venus flytrap"],
    "weather": ["rain"]
}

@client.event
async def on_ready():
    print(f'✅ Bot conectado como {client.user}')

    # Checagem das variáveis de ambiente na inicialização
    phone_ok = bool(os.environ.get('WHATSAPP_PHONE'))
    apikey_ok = bool(os.environ.get('CALLMEBOT_KEY'))
    print(f"📱 WHATSAPP_PHONE configurado: {phone_ok}")
    print(f"🔑 CALLMEBOT_KEY configurada: {apikey_ok}")
    if not phone_ok or not apikey_ok:
        print("⚠️ ATENÇÃO: uma ou mais variáveis de ambiente do WhatsApp estão faltando no Render!")


def extrair_texto(message: discord.Message) -> str:
    """Junta o conteúdo da mensagem + tudo que estiver dentro dos embeds."""
    texto_completo = message.content.lower()
    for embed in message.embeds:
        if embed.title:
            texto_completo += f" {embed.title.lower()}"
        if embed.description:
            texto_completo += f" {embed.description.lower()}"
        for field in embed.fields:
            texto_completo += f" {field.name.lower()} {field.value.lower()}"
    return texto_completo


def enviar_whatsapp(texto_notificacao: str):
    """Envia a notificação via CallMeBot e loga a resposta completa."""
    phone = os.environ.get('WHATSAPP_PHONE')
    apikey = os.environ.get('CALLMEBOT_KEY')

    if not phone or not apikey:
        print("❌ Não é possível enviar: WHATSAPP_PHONE ou CALLMEBOT_KEY não configurados.")
        return

    texto_codificado = urllib.parse.quote(texto_notificacao)
    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={texto_codificado}&apikey={apikey}"

    try:
        response = requests.get(url, timeout=15)
        print(f"📨 CallMeBot status: {response.status_code}")
        print(f"📨 CallMeBot resposta: {response.text}")

        # A CallMeBot quase sempre responde 200, então checamos o texto também
        if "Message queued" in response.text or "Message sent" in response.text:
            print("✅ Mensagem confirmada como enviada para o WhatsApp!")
        elif "APIKey" in response.text or "Invalid" in response.text:
            print("❌ Falha: apikey inválida ou autorização expirada. Reenvie o 'I allow...' pro CallMeBot no WhatsApp.")
        elif response.status_code != 200:
            print(f"❌ Falha ao enviar. Status inesperado: {response.status_code}")
        else:
            print("⚠️ Resposta não reconhecida, verifique manualmente o texto acima.")
    except Exception as e:
        print(f"❌ Erro ao enviar: {e}")


async def processar_mensagem(message: discord.Message):
    if message.author == client.user:
        return

    nome_canal = message.channel.name
    if nome_canal not in ALERTAS_POR_CANAL:
        return

    texto_completo = extrair_texto(message)
    if not texto_completo.strip():
        return

    palavras_chave_do_canal = ALERTAS_POR_CANAL[nome_canal]
    palavras_encontradas = [p for p in palavras_chave_do_canal if p in texto_completo]

    if palavras_encontradas:
        print(f"🔔 Encontrado {palavras_encontradas} no canal #{nome_canal}!")

        titulo_alerta = message.embeds[0].title if message.embeds and message.embeds[0].title else "Alerta do Jogo"
        texto_notificacao = f"🔔 *{titulo_alerta}*\nCanal: #{nome_canal}\nGatilho: {', '.join(palavras_encontradas)}"

        enviar_whatsapp(texto_notificacao)


@client.event
async def on_message(message):
    await processar_mensagem(message)


@client.event
async def on_message_edit(before, after):
    # Muitos bots de tracker editam a mesma mensagem em vez de postar uma nova
    await processar_mensagem(after)


# --- 3. Inicialização ---
async def main():
    await run_web_server()
    await client.start(os.environ.get('DISCORD_TOKEN'))

if __name__ == "__main__":
    asyncio.run(main())
