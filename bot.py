import discord
from discord.ext import tasks
import requests
from bs4 import BeautifulSoup
import os
import asyncio
from aiohttp import web

# --- 1. Servidor Web (Impede o Render de desligar o bot) ---
async def handle_ping(request):
    return web.Response(text="Scraper GAG2 com Diagnóstico rodando 24/7!")

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
    "poison apple", "venom spitter", "moon bloom", "hypno bloom", 
    "dragons breath"
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
    print(f'✅ Bot conectado como {client.user}! Iniciando varredura com diagnóstico...')
    if not monitorar_site.is_running():
        monitorar_site.start()

@tasks.loop(minutes=3)
async def monitorar_site():
    print("-" * 40)
    print("🔄 Iniciando novo ciclo de varredura...")
    
    # Headers mais robustos para tentar passar por bloqueios simples do Cloudflare
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    alertas = []

    try:
        # --- 1. MULTIPLICADORES DE VENDA (SELL) ---
        req_sell = requests.get("https://www.gag2.gg/stock/sell", headers=headers, timeout=10)
        print(f"📊 [SELL API] Status: {req_sell.status_code} | Tamanho: {len(req_sell.text)} bytes")
        
        if req_sell.status_code == 200:
            soup_sell = BeautifulSoup(req_sell.text, 'html.parser')
            mults_agora = set()
            
            for elemento_nome in soup_sell.find_all(attrs={"title": True}):
                nome_fruta = elemento_nome['title'].lower().replace("'", "").replace("’", "")
                if any(alvo in nome_fruta for alvo in FILTRO_MULTIPLICADORES):
                    container = elemento_nome.parent
                    if container:
                        texto_container = container.get_text()
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
        else:
            print(f"⚠️ [BLOQUEIO CLOUDFLARE] Acesso negado à página Sell.")

        # --- 2. SEMENTES NO ESTOQUE (SEED SHOP) ---
        req_stock = requests.get("https://www.gag2.gg/stock", headers=headers, timeout=10)
        print(f"🌱 [STOCK API] Status: {req_stock.status_code} | Tamanho: {len(req_stock.text)} bytes")
        
        if req_stock.status_code == 200:
            soup_stock = BeautifulSoup(req_stock.text, 'html.parser')
            sementes_agora = set()
            
            # Isolando a busca apenas dentro da caixa "Seed Shop" (Escopo sugerido)
            seed_card_header = soup_stock.find('h3', string='Seed Shop')
            if seed_card_header:
                # Volta para a div principal (o glass-card) que contém toda a loja de sementes
                seed_container = seed_card_header.find_parent('div', class_=lambda c: c and 'glass-card' in c)
                
                if seed_container:
                    itens_estoque = seed_container.find_all('div', class_='flex items-center gap-3 py-1.5 px-2')
                    print(f"🔍 Itens encontrados na Seed Shop: {len(itens_estoque)}")
                    
                    for item in itens_estoque:
                        texto_item = item.get_text(separator=' ', strip=True).lower().replace("'", "").replace("’", "")
                        for alvo in FILTRO_SEMENTES:
                            if alvo in texto_item:
                                sementes_agora.add(alvo.title())
                else:
                    print("⚠️ Container da Seed Shop não encontrado na estrutura.")
            else:
                print("⚠️ Título 'Seed Shop' não encontrado (Possível mudança no site ou Cloudflare).")

            novas_sementes = sementes_agora - cache_notificacoes["sementes"]
            if novas_sementes:
                alertas.append(f"🌱 **Estoque:** {', '.join(novas_sementes)}")
            cache_notificacoes["sementes"] = sementes_agora
        else:
            print(f"⚠️ [BLOQUEIO CLOUDFLARE] Acesso negado à página de Estoque.")

        # --- 3. CLIMA (WEATHER) ---
        req_weather = requests.get("https://www.gag2.gg/stock/weather", headers=headers, timeout=10)
        print(f"☁️ [WEATHER API] Status: {req_weather.status_code} | Tamanho: {len(req_weather.text)} bytes")
        
        if req_weather.status_code == 200:
            soup_weather = BeautifulSoup(req_weather.text, 'html.parser')
            
            # Busca baseada na estrutura do primeiro card de vidro em vez da classe do texto
            weather_card = soup_weather.select_one(".glass-card h3")
            
            if weather_card:
                nome_evento = weather_card.get_text(strip=True).lower()
                
                if "no active weather" not in nome_evento:
                    if any(alvo in nome_evento for alvo in FILTRO_EVENTOS):
                        estado_clima = f"evento_{nome_evento}"
                        
                        if cache_notificacoes["weather"] != estado_clima:
                            alertas.append(f"☁️ **Evento Ativo:** {nome_evento.title()}!")
                            cache_notificacoes["weather"] = estado_clima
                else:
                    cache_notificacoes["weather"] = "limpo"
            else:
                print("⚠️ Card de clima não encontrado.")
        else:
             print(f"⚠️ [BLOQUEIO CLOUDFLARE] Acesso negado à página de Clima.")

        # --- ENVIO DA MENSAGEM DIRETA (DM) ---
        if alertas:
            user_id = int(os.environ.get('DISCORD_USER_ID'))
            user = await client.fetch_user(user_id)
            
            mensagem_final = "\n\n".join(alertas)
            await user.send(f"🚨 **Atualização GAG2 Live** 🚨\n\n{mensagem_final}")
            print("✅ DM enviada com sucesso!")
        else:
            print("⚪ Nenhum item dos filtros ativado neste ciclo.")
            
    except Exception as e:
        print(f"❌ Erro grave na execução do loop: {e}")

# --- 3. Inicialização ---
async def main():
    await run_web_server()
    await client.start(os.environ.get('DISCORD_TOKEN'))

if __name__ == "__main__":
    asyncio.run(main())
