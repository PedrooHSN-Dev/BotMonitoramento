import discord
from discord.ext import tasks
import requests
from bs4 import BeautifulSoup
import os
import asyncio
from aiohttp import web

# --- 1. Servidor Web (Impede o Render de desligar o bot) ---
async def handle_ping(request):
    return web.Response(text="Scraper com filtros rodando 24/7!")

async def run_web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle_ping)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- 2. Lógica do Bot e Web Scraper ---
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Memória para não enviar mensagens repetidas
cache_notificacoes = {
    "weather": "",
    "sementes": set(),
    "multiplicadores": set()
}

# ==========================================
# SUAS LISTAS DE FILTROS (Sempre em minúsculo)
# ==========================================
FILTRO_SEMENTES = [
    "dragon fruit", "venus flytrap", "- mushroom", "rocket pop", 
    "sunflower", "fire fern", "pomegranate", "poison apple", 
    "venon splitter", "venom spitter", "moon bloom", "hypno bloom", "dragons breath"
]

FILTRO_MULTIPLICADORES = [
    "bamboo", "dragon fruit", "venus flytrap", "mushroom"
]

FILTRO_EVENTOS = [
    "goldmoon", "snowfall", "bloodmoon", "rainbow", "rainbow moon", 
    "lightning", "aurora", "starfall", "mega moon", "sunburst"
]
# ==========================================

@client.event
async def on_ready():
    print(f'✅ Bot conectado como {client.user}! Iniciando monitoramento com filtros...')
    if not monitorar_site.is_running():
        monitorar_site.start()

@tasks.loop(minutes=3)
async def monitorar_site():
    print("🔄 Puxando dados do gag2.gg...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    alertas = []

    try:
        # --- 1. MULTIPLICADORES DE VENDA (SELL) ---
        req_sell = requests.get("https://www.gag2.gg/stock/sell", headers=headers)
        soup_sell = BeautifulSoup(req_sell.text, 'html.parser')
        mults_agora = set()
        
        for elemento_nome in soup_sell.find_all(attrs={"title": True}):
            # Limpa o nome removendo apóstrofos para a busca ser infalível
            nome_fruta = elemento_nome['title'].lower().replace("'", "").replace("’", "")
            
            # Verifica se a fruta lida está na sua lista de interesse para 2x/4x
            if any(alvo in nome_fruta for alvo in FILTRO_MULTIPLICADORES):
                container = elemento_nome.parent
                if container:
                    texto_container = container.get_text()
                    # Salva com o nome original do elemento para ficar bonito no Discord
                    nome_original = elemento_nome['title']
                    if "2×" in texto_container:
                        mults_agora.add(f"{nome_original} (2x)")
                    elif "4×" in texto_container:
                        mults_agora.add(f"{nome_original} (4x)")

        novos_mults = mults_agora - cache_notificacoes["multiplicadores"]
        if novos_mults:
            lista_formatada = "\n".join([f"📈 • **{m}**" for m in novos_mults])
            alertas.append(f"**Multiplicadores em Alta:**\n{lista_formatada}")
        cache_notificacoes["multiplicadores"] = mults_agora

        # --- 2. SEMENTES NO ESTOQUE (SEED SHOP) ---
        req_stock = requests.get("https://www.gag2.gg/stock", headers=headers)
        soup_stock = BeautifulSoup(req_stock.text, 'html.parser')
        sementes_agora = set()
        
        for elemento_nome in soup_stock.find_all(attrs={"title": True}):
            nome_item = elemento_nome['title'].lower().replace("'", "").replace("’", "")
            nome_original = elemento_nome['title']
            
            if any(alvo in nome_item for alvo in FILTRO_SEMENTES):
                sementes_agora.add(nome_original)
                
        novas_sementes = sementes_agora - cache_notificacoes["sementes"]
        if novas_sementes:
            alertas.append(f"🌱 **Estoque:** {', '.join(novas_sementes)}")
        cache_notificacoes["sementes"] = sementes_agora

        # --- 3. CLIMA (WEATHER) ---
        req_weather = requests.get("https://www.gag2.gg/stock/weather", headers=headers)
        soup_weather = BeautifulSoup(req_weather.text, 'html.parser')
        texto_weather = soup_weather.get_text(separator=' ', strip=True).lower()
        
        # Se a frase padrão sumiu, o clima mudou
        if "no active weather" not in texto_weather:
            # Procura qual dos seus eventos alvo está no texto da página agora
            eventos_encontrados = [evt for evt in FILTRO_EVENTOS if evt in texto_weather]
            
            if eventos_encontrados:
                # Usa o evento encontrado como marcador de estado no cache
                estado_clima = f"evento_{eventos_encontrados[0]}"
                if cache_notificacoes["weather"] != estado_clima:
                    nomes_formatados = [evt.title() for evt in eventos_encontrados]
                    alertas.append(f"☁️ **Evento Climático Ativo:** Detecção de {', '.join(nomes_formatados)}!")
                    cache_notificacoes["weather"] = estado_clima
        else:
            cache_notificacoes["weather"] = "limpo"

        # --- ENVIO DA MENSAGEM DIRETA (DM) ---
        if alertas:
            user_id = int(os.environ.get('DISCORD_USER_ID'))
            user = await client.fetch_user(user_id)
            
            mensagem_final = "\n\n".join(alertas)
            await user.send(f"🚨 **Atualização GAG2 Live** 🚨\n\n{mensagem_final}")
            print("✅ DM enviada com base nos filtros!")
        else:
            print("Nenhum item dos filtros ativado neste ciclo.")
            
    except Exception as e:
        print(f"❌ Erro na extração de dados: {e}")

# --- 3. Inicialização ---
async def main():
    await run_web_server()
    await client.start(os.environ.get('DISCORD_TOKEN'))

if __name__ == "__main__":
    asyncio.run(main())
