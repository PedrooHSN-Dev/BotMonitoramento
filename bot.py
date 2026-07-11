import discord
from discord.ext import tasks
import requests
import os
import asyncio
from aiohttp import web
from datetime import datetime, timezone

# --- 1. Servidor Web (Impede o Render de desligar o bot) ---
async def handle_ping(request):
    return web.Response(text="API Monitor GAG2 Multi-Clock rodando 24/7!")

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

# Cache baseado em marcadores de tempo
cache_notificacoes = {
    "last_seed_restock": "",     
    "last_gear_restock": "", 
    "last_crate_restock": "",    
    "last_sell_boundary": 0,     
    "weather": "limpo"
}

# ==========================================
# SUAS LISTAS DE FILTROS (Sempre em minúsculo)
# ==========================================
FILTRO_SEMENTES = [
    "dragon fruit", "venus fly trap", "mushroom",
    "rocket pop", "sunflower", "fire fern", "pomegranate", 
    "poison apple", "venom spitter", "moon bloom", "hypno bloom", "dragons breath"
]

FILTRO_GEAR = [
    "trowel"
]

FILTRO_CRATES = [
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
    print(f'✅ Bot conectado como {client.user}! Monitoramento 100% ativo...')
    if not monitorar_api.is_running():
        monitorar_api.start()

@tasks.loop(minutes=1) 
async def monitorar_api():
    print("-" * 40)
    print("🔄 Puxando dados das APIs...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    
    embed = discord.Embed(
        title="🚨 Radar GAG2 Atualizado",
        description="Novos itens detectados nos seus filtros!",
        color=0x2ecc71,
        timestamp=datetime.now(timezone.utc)
    )

    try:
        # --- 1. MULTIPLICADORES (SELL) ---
        req_sell = requests.get("https://api.gag2.gg/api/live/sell", headers=headers, timeout=10)
        if req_sell.status_code == 200:
            dados_sell = req_sell.json().get("sell", {})
            boundary = dados_sell.get("boundary", 0)
            
            if boundary != cache_notificacoes["last_sell_boundary"]:
                mults_agora = []
                for entrada in dados_sell.get("entries", []):
                    nome_fruta = entrada.get("name", "")
                    nome_limpo = nome_fruta.lower().replace("'", "").replace("’", "")
                    multiplicador = entrada.get("multiplier", 1.0)
                    
                    if nome_limpo in FILTRO_MULTIPLICADORES and multiplicador >= 2.0:
                        mults_agora.append(f"{nome_fruta} ({int(multiplicador)}x)")
                
                if mults_agora:
                    lista_formatada = "\n".join([f"> 📈 **{m}**" for m in mults_agora])
                    embed.add_field(name="💰 Multiplicadores (Sell)", value=lista_formatada, inline=False)
                
                cache_notificacoes["last_sell_boundary"] = boundary

        # --- 2. ESTOQUE: SEMENTES, GEAR E CRATES (STOCK) ---
        req_stock = requests.get("https://api.gag2.gg/api/live/stock", headers=headers, timeout=10)
        if req_stock.status_code == 200:
            dados_stock = req_stock.json()
            
            for categoria in dados_stock.get("stock", []):
                tipo_categoria = categoria.get("category")
                restocked_at = categoria.get("restockedAt", "")
                
                # --- CHECK DA SEED SHOP ---
                if tipo_categoria == "seed":
                    if restocked_at != cache_notificacoes["last_seed_restock"]:
                        sementes_encontradas = []
                        for item in categoria.get("items", []):
                            nome_item = item.get("name", "")
                            emoji_item = item.get("emoji", "🌱")
                            nome_limpo = nome_item.lower().replace("'", "").replace("’", "")
                            
                            if any(alvo in nome_limpo for alvo in FILTRO_SEMENTES):
                                sementes_encontradas.append(f"{emoji_item} **{nome_item}**")
                        
                        if sementes_encontradas:
                            lista_formatada = "\n".join([f"> {s}" for s in sementes_encontradas])
                            embed.add_field(name="🛒 Seed Shop", value=lista_formatada, inline=True)
                        
                        cache_notificacoes["last_seed_restock"] = restocked_at
                
                # --- CHECK DA GEAR SHOP ---
                elif tipo_categoria == "gear":
                    if restocked_at != cache_notificacoes["last_gear_restock"]:
                        gear_encontrados = []
                        for item in categoria.get("items", []):
                            nome_item = item.get("name", "")
                            emoji_item = item.get("emoji", "🔧")
                            nome_limpo = nome_item.lower().replace("'", "").replace("’", "")
                            
                            if any(alvo in nome_limpo for alvo in FILTRO_GEAR):
                                gear_encontrados.append(f"{emoji_item} **{nome_item}**")
                        
                        if gear_encontrados:
                            lista_formatada = "\n".join([f"> {g}" for g in gear_encontrados])
                            embed.add_field(name="🎒 Gear Shop", value=lista_formatada, inline=True)
                        
                        cache_notificacoes["last_gear_restock"] = restocked_at
                        
                # --- CHECK DAS CRATES (CAIXAS) ---
                elif tipo_categoria == "crate":
                    if restocked_at != cache_notificacoes["last_crate_restock"]:
                        crates_encontradas = []
                        for item in categoria.get("items", []):
                            nome_item = item.get("name", "")
                            emoji_item = item.get("emoji", "📦")
                            nome_limpo = nome_item.lower().replace("'", "").replace("’", "")
                            
                            if any(alvo in nome_limpo for alvo in FILTRO_CRATES):
                                crates_encontradas.append(f"{emoji_item} **{nome_item}**")
                        
                        if crates_encontradas:
                            lista_formatada = "\n".join([f"> {c}" for c in crates_encontradas])
                            embed.add_field(name="🎁 Crates", value=lista_formatada, inline=True)
                        
                        cache_notificacoes["last_crate_restock"] = restocked_at

        # --- 3. CLIMA (WEATHER) ---
        req_weather = requests.get("https://api.gag2.gg/api/live/weather", headers=headers, timeout=10)
        if req_weather.status_code == 200:
            dados_weather = req_weather.json()
            clima_atual = dados_weather.get("weather", {}).get("current")
            
            if clima_atual: 
                nome_evento = clima_atual.get("name", "")
                emoji_evento = clima_atual.get("emoji", "☁️")
                nome_limpo = nome_evento.lower().replace("'", "").replace("’", "")
                ends_at_str = clima_atual.get("endsAt")
                
                evento_valido = True
                if ends_at_str:
                    try:
                        ends_at_dt = datetime.fromisoformat(ends_at_str.replace("Z", "+00:00"))
                        agora_utc = datetime.now(timezone.utc)
                        if agora_utc > ends_at_dt:
                            evento_valido = False
                    except Exception as e:
                        print(f"Erro no cálculo de tempo: {e}")

                if evento_valido and any(alvo in nome_limpo for alvo in FILTRO_EVENTOS):
                    estado_clima = f"evento_{nome_limpo}"
                    if cache_notificacoes["weather"] != estado_clima:
                        embed.add_field(name="Clima Ativo", value=f"> {emoji_evento} **{nome_evento}**", inline=False)
                        cache_notificacoes["weather"] = estado_clima
                elif not evento_valido:
                    cache_notificacoes["weather"] = "limpo"
            else:
                cache_notificacoes["weather"] = "limpo"

        # --- ENVIO DA MENSAGEM DIRETA (DM) ---
        if len(embed.fields) > 0:
            user_id = int(os.environ.get('DISCORD_USER_ID'))
            user = await client.fetch_user(user_id)
            
            embed.set_footer(text="Monitoramento Automático GAG2")
            
            await user.send(embed=embed)
            print("✅ Embed enviado com sucesso!")
        else:
            print("⚪ Nenhuma alteração de ciclo ou item alvo detectado.")

    except Exception as e:
        print(f"❌ Erro na varredura da API: {e}")

# --- 3. Inicialização ---
async def main():
    await run_web_server()
    await client.start(os.environ.get('DISCORD_TOKEN'))

if __name__ == "__main__":
    asyncio.run(main())
