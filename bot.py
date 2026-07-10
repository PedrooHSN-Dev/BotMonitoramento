import discord
from discord.ext import tasks
import requests
import os
import asyncio
from aiohttp import web

# --- 1. Servidor Web (Impede o Render de desligar o bot) ---
async def handle_ping(request):
    return web.Response(text="API Monitor GAG2 rodando 24/7!")

async def run_web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle_ping)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- 2. Lógica do Bot e API Monitor ---
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
    print(f'✅ Bot conectado como {client.user}! Iniciando monitoramento via API JSON...')
    if not monitorar_api.is_running():
        monitorar_api.start()

@tasks.loop(minutes=3)
async def monitorar_api():
    print("-" * 40)
    print("🔄 Puxando dados das APIs do gag2.gg...")
    # Usamos Accept application/json para avisar ao servidor que queremos o dado puro
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    alertas = []

    try:
        # --- 1. MULTIPLICADORES (SELL) ---
        req_sell = requests.get("https://api.gag2.gg/api/live/sell", headers=headers, timeout=10)
        
        if req_sell.status_code == 200:
            dados_sell = req_sell.json()
            mults_agora = set()
            
            # Navega pelo JSON para encontrar as frutas e seus multiplicadores
            for entrada in dados_sell.get("sell", {}).get("entries", []):
                nome_fruta = entrada.get("name", "")
                nome_limpo = nome_fruta.lower().replace("'", "").replace("’", "")
                multiplicador = entrada.get("multiplier", 1.0)
                
                # Verifica se a fruta está no filtro e se o multiplicador é bom (>= 2.0)
                if nome_limpo in FILTRO_MULTIPLICADORES and multiplicador >= 2.0:
                    mults_agora.add(f"{nome_fruta} ({int(multiplicador)}x)")

            novos_mults = mults_agora - cache_notificacoes["multiplicadores"]
            if novos_mults:
                lista_formatada = "\n".join([f"📈 • **{m}**" for m in novos_mults])
                alertas.append(f"**Multiplicadores em Alta:**\n{lista_formatada}")
            cache_notificacoes["multiplicadores"] = mults_agora
        else:
            print(f"⚠️ Erro na API Sell. Status: {req_sell.status_code}")

        # --- 2. SEMENTES NO ESTOQUE (STOCK) ---
        req_stock = requests.get("https://api.gag2.gg/api/live/stock", headers=headers, timeout=10)
        
        if req_stock.status_code == 200:
            dados_stock = req_stock.json()
            sementes_agora = set()
            
            # Procura especificamente pela categoria "seed" no JSON
            for categoria in dados_stock.get("stock", []):
                if categoria.get("category") == "seed":
                    for item in categoria.get("items", []):
                        nome_semente = item.get("name", "")
                        nome_limpo = nome_semente.lower().replace("'", "").replace("’", "")
                        
                        if nome_limpo in FILTRO_SEMENTES:
                            sementes_agora.add(nome_semente)
                    break # Já varreu as sementes, pode parar o loop de categorias
                    
            novas_sementes = sementes_agora - cache_notificacoes["sementes"]
            if novas_sementes:
                alertas.append(f"🌱 **Estoque:** {', '.join(novas_sementes)}")
            cache_notificacoes["sementes"] = sementes_agora
        else:
            print(f"⚠️ Erro na API Stock. Status: {req_stock.status_code}")

        # --- 3. CLIMA (WEATHER) ---
        req_weather = requests.get("https://api.gag2.gg/api/live/weather", headers=headers, timeout=10)
        
        if req_weather.status_code == 200:
            dados_weather = req_weather.json()
            # O objeto 'current' vai existir se tiver evento, ou será None se o clima estiver limpo
            clima_atual = dados_weather.get("weather", {}).get("current")
            
            if clima_atual: 
                nome_evento = clima_atual.get("name", "")
                nome_limpo = nome_evento.lower().replace("'", "").replace("’", "")
                
                # Checa se o evento que está rodando é um dos que você quer monitorar
                if any(alvo in nome_limpo for alvo in FILTRO_EVENTOS):
                    estado_clima = f"evento_{nome_limpo}"
                    
                    if cache_notificacoes["weather"] != estado_clima:
                        alertas.append(f"☁️ **Evento Ativo:** {nome_evento}!")
                        cache_notificacoes["weather"] = estado_clima
            else:
                cache_notificacoes["weather"] = "limpo"
        else:
            print(f"⚠️ Erro na API Weather. Status: {req_weather.status_code}")

        # --- ENVIO DA DM ---
        if alertas:
            user_id = int(os.environ.get('DISCORD_USER_ID'))
            user = await client.fetch_user(user_id)
            
            mensagem_final = "\n\n".join(alertas)
            await user.send(f"🚨 **Atualização GAG2 Live (Direto da API)** 🚨\n\n{mensagem_final}")
            print("✅ DM enviada com sucesso!")
        else:
            print("⚪ Nenhum item dos filtros ativado neste ciclo.")

    except Exception as e:
        print(f"❌ Erro grave de conexão/processamento: {e}")

# --- 3. Inicialização ---
async def main():
    await run_web_server()
    await client.start(os.environ.get('DISCORD_TOKEN'))

if __name__ == "__main__":
    asyncio.run(main())
