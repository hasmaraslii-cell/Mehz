"""
Mehz - Topluyo botu
Kurulum:  pip install topluyobot
Çalıştır: python mehz_bot.py
Token'ı koda yazma; ortam değişkeni olarak ver:  TOPLUYO_TOKEN=xxxx python mehz_bot.py
"""
import ast
import json
import operator
import os
import random
import time

from topluyobot import TopluyoBOT

TOKEN = os.environ.get("TOPLUYO_TOKEN", "BURAYA_BOT_TOKENI")
PREFIX = "!"
DB_FILE = "mehz_db.json"

bot = TopluyoBOT(TOKEN)

# ---------------------------------------------------------------- veritabanı
def load_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"users": {}}


def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(DB, f, ensure_ascii=False, indent=2)


DB = load_db()


def user(uid):
    return DB["users"].setdefault(str(uid), {"xp": 0, "puan": 0, "son_gunluk": 0, "son_xp": 0})


# ---------------------------------------------------------------- yanıt gönderme
def send_dm(user_id, text):
    """Topluyo kütüphanesinde belgelenen yöntem: messages.send (DM)."""
    return bot.post_sync("messages.send", {"user_id": str(user_id), "message": text})


def send_channel(channel_id, text):
    """
    Kanala yazma metodunun adı kütüphane dokümanında yok.
    Topluyo bot API dokümanından doğru metod adını bulup burayı düzelt.
    """
    return bot.post_sync("posts.add", {"channel_id": str(channel_id), "message": text})


def reply(data, text):
    if data.get("channel_id"):
        send_channel(data["channel_id"], text)
    else:
        send_dm(data["user_id"], text)


# ---------------------------------------------------------------- güvenli hesap makinesi
OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def safe_eval(node):
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        left, right = safe_eval(node.left), safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("Üs çok büyük")
        return OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](safe_eval(node.operand))
    raise ValueError("Geçersiz ifade")


# ---------------------------------------------------------------- komutlar
SEKIZ_TOP = ["Evet.", "Hayır.", "Belki.", "Kesinlikle!", "Pek sanmam.", "Tekrar sor.", "Olabilir."]
ESPRILER = [
    "Bilgisayar neden soğuk? Çünkü Windows'u açık.",
    "Programcı neden gözlük takar? Çünkü C# göremez.",
    "Bug değil, özellik bu.",
]


def cmd_yardim(data, args):
    return (
        "Mehz komutları:\n"
        "!ping  !zar [yüz]  !yazitura  !8top <soru>  !sec a, b, c\n"
        "!hesapla <işlem>  !espri  !seviye  !siralama  !gunluk\n"
        "!yardim"
    )


def cmd_ping(data, args):
    return "Pong! 🏓"


def cmd_zar(data, args):
    n = int(args[0]) if args and args[0].isdigit() and int(args[0]) > 1 else 6
    return f"🎲 {random.randint(1, n)} (1-{n})"


def cmd_yazitura(data, args):
    return random.choice(["Yazı", "Tura"])


def cmd_8top(data, args):
    if not args:
        return "Bir soru sor: !8top bugün şanslı mıyım?"
    return "🎱 " + random.choice(SEKIZ_TOP)


def cmd_sec(data, args):
    secenekler = [s.strip() for s in " ".join(args).split(",") if s.strip()]
    if len(secenekler) < 2:
        return "Kullanım: !sec elma, armut, muz"
    return "Seçimim: " + random.choice(secenekler)


def cmd_hesapla(data, args):
    try:
        return "Sonuç: " + str(safe_eval(ast.parse(" ".join(args), mode="eval")))
    except Exception:
        return "Hesaplanamadı. Örnek: !hesapla (5+3)*2"


def cmd_espri(data, args):
    return random.choice(ESPRILER)


def seviye_hesapla(xp):
    return int((xp / 100) ** 0.5) + 1


def cmd_seviye(data, args):
    u = user(data["user_id"])
    return f"Seviye {seviye_hesapla(u['xp'])} | XP: {u['xp']} | Puan: {u['puan']}"


def cmd_siralama(data, args):
    top = sorted(DB["users"].items(), key=lambda kv: kv[1]["xp"], reverse=True)[:10]
    if not top:
        return "Henüz kimse yok."
    return "🏆 Sıralama\n" + "\n".join(
        f"{i}. {uid} — {u['xp']} XP" for i, (uid, u) in enumerate(top, 1)
    )


def cmd_gunluk(data, args):
    u = user(data["user_id"])
    if time.time() - u["son_gunluk"] < 86400:
        kalan = int((86400 - (time.time() - u["son_gunluk"])) / 3600)
        return f"Günlük ödülü zaten aldın. ~{kalan} saat sonra tekrar gel."
    odul = random.randint(50, 150)
    u["puan"] += odul
    u["son_gunluk"] = time.time()
    save_db()
    return f"🎁 {odul} puan kazandın! Toplam: {u['puan']}"


KOMUTLAR = {
    "yardim": cmd_yardim, "yardım": cmd_yardim, "ping": cmd_ping, "zar": cmd_zar,
    "yazitura": cmd_yazitura, "8top": cmd_8top, "sec": cmd_sec, "hesapla": cmd_hesapla,
    "espri": cmd_espri, "seviye": cmd_seviye, "siralama": cmd_siralama, "gunluk": cmd_gunluk,
}


# ---------------------------------------------------------------- olaylar
def xp_ver(uid):
    u = user(uid)
    if time.time() - u["son_xp"] >= 30:  # spam engeli
        u["xp"] += random.randint(5, 15)
        u["son_xp"] = time.time()
        save_db()


def handle_text(data):
    text = str(data.get("message", "")).strip()
    uid = data.get("user_id")
    if uid is None:
        return
    xp_ver(uid)
    if not text.startswith(PREFIX):
        return
    parts = text[len(PREFIX):].split()
    if not parts:
        return
    fn = KOMUTLAR.get(parts[0].lower())
    if fn:
        reply(data, fn(data, parts[1:]))


@bot.on("connected")
def on_connected():
    print("✅ Mehz bağlandı")


@bot.on("auth_problem")
def on_auth():
    print("❌ Token geçersiz")


@bot.on("close")
def on_close():
    print("🔌 Bağlantı kapandı")


@bot.on("error")
def on_error(err):
    print(f"⚠️ Hata: {err}")


@bot.on("message")
def on_message(data):
    action = data.get("action")
    try:
        if action in ("message/send", "post/add", "post/mention"):
            handle_text(data)
        elif action == "group/join":
            print(f"Gruba katıldı: {data.get('group_id')}")
    except Exception as e:
        print(f"Komut hatası: {e}")


if __name__ == "__main__":
    bot.run()
