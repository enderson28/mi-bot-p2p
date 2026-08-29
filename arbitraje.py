import json
import logging
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, time, timedelta, timezone

logger = logging.getLogger(__name__)

USER_ARBITRAJE_DATA = {}

# --- DICCIONARIO DE EMOJIS ANIMADOS (Telegram Premium HTML) ---
# Puedes ajustar los IDs aquí si deseas cambiar alguno en el futuro
TG_EMOJIS = {
    "calc": '<tg-emoji emoji-id="5303214794336125778">🧮</tg-emoji>',
    "usdt1": '<tg-emoji emoji-id="5843796824367832872">🪙</tg-emoji>',
    "check": '<tg-emoji emoji-id="5206607081334906820">✔️</tg-emoji>',
    "pencil": '<tg-emoji emoji-id="5395444784611480792">✏️</tg-emoji>',
    "bank": '<tg-emoji emoji-id="5332455502917949981">🏦</tg-emoji>',
    "dollar": '<tg-emoji emoji-id="5409048419211682843">💵</tg-emoji>',
    "percent": '<tg-emoji emoji-id="5229064374403998351">🛍</tg-emoji>',
    "chart": '<tg-emoji emoji-id="5197503331215361533">📈</tg-emoji>',
    "red_circle": '<tg-emoji emoji-id="5411225014148014586">🔴</tg-emoji>',
    "green_circle": '<tg-emoji emoji-id="5416081784641168838">🟢</tg-emoji>',
    "usdt": '<tg-emoji emoji-id="5814556334829343625">🪙</tg-emoji>',
    "usd": '<tg-emoji emoji-id="5325517150754986636">🪙</tg-emoji>',
    "binance": '<tg-emoji emoji-id="5830062858985018281">🪙</tg-emoji>',
    "hand": '<tg-emoji emoji-id="5264713049637409446">🪙</tg-emoji>',
    "briefcase": '<tg-emoji emoji-id="5445221832074483553">💼</tg-emoji>',
    "party": '<tg-emoji emoji-id="5461151367559141950">🎉</tg-emoji>',
    "bcv": '<tg-emoji emoji-id="5143558232739940356">🪛</tg-emoji>',
    "pro": '<tg-emoji emoji-id="4949492420392781701">🕘</tg-emoji>',
    "bdv1": '<tg-emoji emoji-id="4949813911579788830">🔉</tg-emoji>',
    "bdv2": '<tg-emoji emoji-id="4949567234428110351">🌁</tg-emoji>',
    "teso": '<tg-emoji emoji-id="4949973031528170774">🕥</tg-emoji>',
    "bancaamiga": '<tg-emoji emoji-id="4947747894871460151">😶‍🌫️</tg-emoji>',
    "bancoactivo": '<tg-emoji emoji-id="4949649440102156194">☄️</tg-emoji>',
    "zinli": '<tg-emoji emoji-id="4949657248352700116">😛</tg-emoji>',
    "banesco": '<tg-emoji emoji-id="4949457545258338260">👎</tg-emoji>',
    "mercantil": '<tg-emoji emoji-id="4949779543251486291">😀</tg-emoji>',
    "bfc": '<tg-emoji emoji-id="4949958450114201616">😁</tg-emoji>',
    "bnc": '<tg-emoji emoji-id="5100832907396646323">😃</tg-emoji>',
    "bancoexterior": '<tg-emoji emoji-id="4949665988611146999">😉</tg-emoji>',
    "clic": '<tg-emoji emoji-id="5310278924616356636">🎯</tg-emoji>',
    
}

COMISIONES_BANCOS = {
    "provincial": {
        "emoji": TG_EMOJIS["pro"],
        "nombre": "BBVA Provincial",
        "porcentaje_str": f"1.5{TG_EMOJIS['percent']}",
        "comision": 0.015,
    },
    "bdv_debit": {
        "emoji": TG_EMOJIS["bdv1"],
        "nombre": "BDV Masterdebit",
        "porcentaje_str": f"2.5{TG_EMOJIS['percent']}",
        "comision": 0.025,
    },
    "otros_1_5": {
        "emoji": TG_EMOJIS["clic"],
        "nombre": "Otros Bancos",
        "porcentaje_str": f"1.5{TG_EMOJIS['percent']}",
        "comision": 0.015,
    },
    "bdv_master": {
        "emoji": TG_EMOJIS["bdv2"],
        "nombre": "BDV MASTERCARD",
        "porcentaje_str": f"2.5{TG_EMOJIS['percent']}",
        "comision": 0.025,
    },
    "tesoro": {
        "emoji": TG_EMOJIS["teso"],
        "nombre": "BANCO TESORO",
        "porcentaje_str": f"2.5{TG_EMOJIS['percent']}",
        "comision": 0.025,
    },
    "otros_2_5": {
        "emoji": TG_EMOJIS["clic"],
        "nombre": "otros bancos",
        "porcentaje_str": f"2.5{TG_EMOJIS['percent']}",
        "comision": 0.025,
    },
    "activo": {
        "emoji": TG_EMOJIS["bancoactivo"],
        "nombre": "BANCO ACTIVO",
        "porcentaje_str": f"3{TG_EMOJIS['percent']}",
        "comision": 0.030,
    },    
    "amiga": {
        "emoji": TG_EMOJIS["bancaamiga"],
        "nombre": "BANCO BANCAMIGA",
        "porcentaje_str": f"5{TG_EMOJIS['percent']}",
        "comision": 0.050,
    },
    "mercantil": {
        "emoji": TG_EMOJIS["mercantil"],
        "nombre": "MERCANTIL",
        "porcentaje_str": f"{TG_EMOJIS['zinli']}",
        "comision": 0.0,
    },   
}

COMISION_PASARELA_BINANCE = 0.041  # 4.1% fija

