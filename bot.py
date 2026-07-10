import discord
from discord.ext import tasks
import requests
import re
import os
import asyncio
from aiohttp import web

# --- 1. Servidor Web (Impede o Render de desligar o bot) ---
async def handle_ping(request):
    return web.Response(text="Scraper GAG2 Inteligente rodando 24/7!")

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

# Memória para evitar notificações repetidas
cache_notificacoes = {
    "weather": "",
    "sementes": set(),
    "multiplicadores": set()
}

# ==========================================
# SUAS LISTAS DE FILTROS (Sempre em minúsculo)
# ==========================================
FILTRO_SEMENTES = [
    "dragon fruit", "venus fly trap", "mushroom", "strawberry", 
    "rocket pop", "sunflower", "fire fern", "pomegranate", 
    "poison apple", "venom spitter", "moon bloom", "hypno bloom", "dragons breath"
]

FILTRO_MULTIPLICADORES = [
    "bamboo", "dragon fruit", "venus fly trap", "mushroom"
]

FILTRO_EVENTOS = [
    "goldmoon", "snowfall", "bloodmoon", "rainbow", "rainbow moon", 
    "lightning", "aurora", "starfall", "mega moon", "sunburst"
]
# ==========================================

@client.event
async def on_ready():
    print(f'✅ Bot conectado como {client.user}! Iniciando varredura por texto...')
    if not monitorar_site.is_running():
        monitorar_site.start()

@tasks.loop(minutes=3)
async def monitorar_site():
    print("-" * 40)
    print("🔄 Iniciando varredura de texto cru...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    alertas = []

    try:
        # --- 1. MULTIPLICADORES DE VENDA (SELL) ---
        req_sell = requests.get("https://www.gag2.gg/stock/sell", headers=headers, timeout=10)
        texto_sell_lower = req_sell.text.lower()
        
        mults_agora = set()
        for fruta in FILTRO_MULTIPLICADORES:
            # Procura a fruta e captura o primeiro multiplicador que termine com '×' ou 'x' logo após ela
            match = re.search(re.escape(fruta) + r'.*?(\d+(?:\.\d+)?)\s*[×x]', texto_sell_lower, re.DOTALL)
            if match:
                mult_val = float(match.group(1))
                # Filtra apenas os focos de 2x e 4x
                if mult_val >= 2.0:
                    mults_agora.add(f"{fruta.title()} ({int(mult_val)}x)")

        novos_mults = mults_agora - cache_notificacoes["multiplicadores"]
        if novos_mults:
            lista_formatada = "\n".join([f"📈 • **{m}**" for m in novos_mults])
            alertas.append(f"**Multiplicadores em Alta:**\n{lista_formatada}")
        cache_notificacoes["multiplicadores"] = mults_agora

        # --- 2. SEMENTES NO ESTOQUE (STOCK) ---
        req_stock = requests.get("https://www.gag2.gg/stock", headers=headers, timeout=10)
        texto_stock_lower = req_stock.text.lower()
        
        sementes_agora = set()
        idx_seed = texto_stock_lower.find("seed shop")
        idx_gear = texto_stock_lower.find("gear shop")
        
        # Segmenta o texto para ler apenas a área correspondente às sementes
        if idx_seed != -1 and idx_gear != -1:
            trecho_seeds = texto_stock_lower[idx_seed:idx_gear]
            for alvo in FILTRO_SEMENTES:
                if alvo in trecho_seeds:
                    sementes_agora.add(alvo.title())
        else:
            # Fallback de segurança caso a estrutura mude drasticamente
            for alvo in FILTRO_SEMENTES:
                if alvo in texto_stock_lower:
                    sementes_agora.add(alvo.title())

        novas_sementes = sementes_agora - cache_notificacoes["sementes"]
        if novas_sementes:
            alertas.append(f"🌱 **Estoque:** {', '.join(novas_sementes)}")
        cache_notificacoes["sementes"] = sementes_agora

        # --- 3. CLIMA (WEATHER) ---
        req_weather = requests.get("https://www.gag2.gg/stock/weather", headers=headers, timeout=10)
        texto_weather_lower = req_weather.text.lower()
        
        if "no active weather" not in texto_weather_lower:
            idx_active = texto_weather_lower.find("active now")
            if idx_active != -1:
                # Examina os próximos 400 caracteres após o indicador de evento ativo
                trecho_clima_ativo = texto_weather_lower[idx_active:idx_active+400]
                
                for evento in FILTRO_EVENTOS:
                    if evento in trecho_clima_ativo:
                        estado_clima = f"evento_{evento}"
                        if cache_notificacoes["weather"] != estado_clima:
                            alertas.append(f"☁️ **Evento Ativo:** {evento.title()}!")
                            cache_notificacoes["weather"] = estado_clima
                        break
        else:
            cache_notificacoes["weather"] = "limpo"

        # --- ENVIO DA MENSAGEM DIRETA (DM) ---
        if alertas:
            user_id = int(os.environ.get('DISCORD_USER_ID'))
            user = await client.fetch_user(user_id)
            
            mensagem_final = "\n\n".join(alertas)
            await user.send(f"🚨 **Atualização GAG2 Live** 🚨\n\n{mensagem_final}")
            print("✅ DM enviada com sucesso utilizando varredura crua!")
        else:
            print("⚪ Nenhum item dos filtros ativo neste ciclo.")
            
    except Exception as e:
        print(f"❌ Erro na varredura: {e}")

# --- 3. Inicialização ---
async def main():
    await run_web_server()
    await client.start(os.environ.get('DISCORD_TOKEN'))

if __name__ == "__main__":
    asyncio.run(main())
