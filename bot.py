import discord
from discord.ext import tasks
import requests
from bs4 import BeautifulSoup
import os
import asyncio
from aiohttp import web

# --- 1. Servidor Web (Impede o Render de desligar o bot) ---
async def handle_ping(request):
    return web.Response(text="Scraper GAG2 rodando 24/7!")

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
    print(f'✅ Bot conectado como {client.user}! Iniciando varredura INFALÍVEL...')
    if not monitorar_site.is_running():
        monitorar_site.start()

@tasks.loop(minutes=3)
async def monitorar_site():
    print("-" * 40)
    print("🔄 Varredura iniciada...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    alertas = []

    try:
        # --- 1. MULTIPLICADORES (SELL) ---
        req_sell = requests.get("https://www.gag2.gg/stock/sell", headers=headers, timeout=10)
        soup_sell = BeautifulSoup(req_sell.text, 'html.parser')
        
        # Pega o título da página para garantir que não é um bloqueio do Cloudflare
        titulo_sell = soup_sell.title.get_text(strip=True) if soup_sell.title else "Erro/Bloqueio"
        print(f"📊 [SELL API] Lendo página: '{titulo_sell}'")
        
        mults_agora = set()
        for elemento_nome in soup_sell.find_all(attrs={"title": True}):
            nome_fruta = elemento_nome['title'].lower().replace("'", "").replace("’", "")
            if any(alvo in nome_fruta for alvo in FILTRO_MULTIPLICADORES):
                container = elemento_nome.parent
                if container:
                    texto_container = container.get_text()
                    if "2×" in texto_container:
                        mults_agora.add(f"{elemento_nome['title']} (2x)")
                    elif "4×" in texto_container:
                        mults_agora.add(f"{elemento_nome['title']} (4x)")

        novos_mults = mults_agora - cache_notificacoes["multiplicadores"]
        if novos_mults:
            lista_formatada = "\n".join([f"📈 • **{m}**" for m in novos_mults])
            alertas.append(f"**Multiplicadores em Alta:**\n{lista_formatada}")
        cache_notificacoes["multiplicadores"] = mults_agora

        # --- 2. SEMENTES NO ESTOQUE (STOCK) ---
        req_stock = requests.get("https://www.gag2.gg/stock", headers=headers, timeout=10)
        soup_stock = BeautifulSoup(req_stock.text, 'html.parser')
        
        titulo_stock = soup_stock.title.get_text(strip=True) if soup_stock.title else "Erro/Bloqueio"
        print(f"🌱 [STOCK API] Lendo página: '{titulo_stock}'")
        
        sementes_agora = set()
        
        # Busca à prova de falhas: varre direto pelos elementos de texto do item
        elementos_nome = soup_stock.find_all(class_=lambda c: c and 'truncate' in c)
        
        for elemento in elementos_nome:
            nome_original = elemento.get_text(strip=True)
            nome_limpo = nome_original.lower().replace("'", "").replace("’", "")
            
            # Como a busca é por igualdade direta, evita qualquer falso positivo
            if nome_limpo in FILTRO_SEMENTES:
                sementes_agora.add(nome_original)
                
        novas_sementes = sementes_agora - cache_notificacoes["sementes"]
        if novas_sementes:
            alertas.append(f"🌱 **Estoque:** {', '.join(novas_sementes)}")
        cache_notificacoes["sementes"] = sementes_agora

        # --- 3. CLIMA (WEATHER) ---
        req_weather = requests.get("https://www.gag2.gg/stock/weather", headers=headers, timeout=10)
        soup_weather = BeautifulSoup(req_weather.text, 'html.parser')
        
        titulo_weather = soup_weather.title.get_text(strip=True) if soup_weather.title else "Erro/Bloqueio"
        print(f"☁️ [WEATHER API] Lendo página: '{titulo_weather}'")
        
        texto_weather = soup_weather.get_text(separator=' ', strip=True).lower()
        
        if "no active weather" not in texto_weather:
            # Encontra exatamente a pílula verde de "Active now"
            badge_ativo = soup_weather.find(string=lambda t: t and 'active now' in t.lower())
            nome_evento = ""
            
            if badge_ativo:
                container = badge_ativo.find_parent('div')
                if container:
                    # O H3 do evento fica do lado ou um nível acima
                    h3_tag = container.find_next_sibling('h3') or container.parent.find('h3')
                    if h3_tag:
                        nome_evento = h3_tag.get_text(strip=True).lower()
            
            # Fallback de segurança se o site mudar
            if not nome_evento:
                primeiro_card = soup_weather.find('div', class_=lambda c: c and 'glass-card' in c)
                nome_evento = primeiro_card.get_text().lower() if primeiro_card else texto_weather

            evento_real = next((e for e in FILTRO_EVENTOS if e in nome_evento), None)
            
            if evento_real:
                estado_clima = f"evento_{evento_real}"
                if cache_notificacoes["weather"] != estado_clima:
                    alertas.append(f"☁️ **Evento Ativo:** {evento_real.title()}!")
                    cache_notificacoes["weather"] = estado_clima
        else:
            cache_notificacoes["weather"] = "limpo"

        # --- ENVIO DA DM ---
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
