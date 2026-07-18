import os
import threading
import http.server
import socketserver
import requests
import telebot

# 1. Tu Token de Telegram
TOKEN_TELEGRAM = "8632019517:AAHMlr_OuSYBfjPVWyUuFXHWTNf8OeIehI4"
bot = telebot.TeleBot(TOKEN_TELEGRAM)

def obtener_tasa_binance_p2p(tipo_operacion):
    """
    Consulta la API oficial de Binance P2P sin bloqueos de proxy.
    """
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    trade_type = "BUY" if tipo_operacion.lower() == "compra" else "SELL"
    
    payload = {
        "asset": "USDT",
        "fiat": "VES",
        "merchantCheck": False,
        "page": 1,
        "payTypes": [],
        "publisherType": None,
        "rows": 1,
        "tradeType": trade_type
    }
    
    try:
        res = requests.post(url, json=payload, timeout=8)
        data = res.json()
        if data and "data" in data and len(data["data"]) > 0:
            return float(data["data"][0]["adv"]["price"])
    except Exception as e:
        print(f"Error en Binance P2P: {e}")
    return None

@bot.message_handler(commands=['precio'])
def enviar_precio(message):
    compra = obtener_tasa_binance_p2p("compra")
    venta = obtener_tasa_binance_p2p("venta")
    
    if compra and venta:
        texto = (
            f"📊 **Tasas de Binance P2P en Tiempo Real**\n"
            f"🇻🇪 Market: USDT / VES\n\n"
            f"🟢 Precio de Compra: {compra} VES\n"
            f"🔴 Precio de Venta: {venta} VES\n\n"
            f"*Valores reales extraídos del libro de órdenes.*"
        )
    else:
        texto = "❌ No se pudieron obtener los datos de Binance en vivo."
        
    bot.reply_to(message, texto, parse_mode="Markdown")

# --- TRUCO PARA KOYEB (Servidor Web en paralelo) ---
def iniciar_servidor_falso():
    # Koyeb le asigna un puerto automáticamente en la variable PORT, si no usa el 8080
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Servidor de mantenimiento activo en el puerto {port}")
        httpd.serve_forever()

if __name__ == "__main__":
    # Arrancamos el servidor falso en un hilo secundario para engañar a Koyeb
    t = threading.Thread(target=iniciar_servidor_falso, daemon=True)
    t.start()
    
    print("🚀 Bot de Telegram escuchando de forma limpia...")
    bot.infinity_polling()
  
