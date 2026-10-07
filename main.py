# -*- coding: utf-8 -*-
"""
بوت تلجرام - تحميل تيك توك بدون علامة مائية
يعمل على Pydroid 3 / Termux / VPS
"""

import os
import re
import json
import time
import requests
from datetime import datetime

# ============================================================
#                    ⚙️ الإعدادات
# ============================================================
API_KEY = "6198804155:AAF5Zj-co6guQ6s2bW5hMTvFga8CFRi0WqA"
ADMIN   = 5952132218

MAX_FILE_SIZE_MB = 50

# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

API_URL = f"https://api.telegram.org/bot{API_KEY}"
last_update_id = 0

print("=" * 50)
print("🤖 بوت تلجرام - بدون علامة مائية")
print(f"👤 الأدمن: {ADMIN}")
print(f"📏 الحد الأقصى: {MAX_FILE_SIZE_MB} MB")
print("=" * 50)


# ============================================================
#                    📂 دوال الملفات
# ============================================================
def _full(path):
    if os.path.isabs(path):
        return path
    return os.path.join(BASE_DIR, path)


def read_file(path, default=""):
    try:
        with open(_full(path), "r", encoding="utf-8") as f:
            return f.read()
    except:
        return default


def write_file(path, content):
    try:
        with open(_full(path), "w", encoding="utf-8") as f:
            f.write(str(content))
    except Exception as e:
        print(f"write error: {e}")


def append_file(path, content):
    try:
        with open(_full(path), "a", encoding="utf-8") as f:
            f.write(str(content))
    except Exception as e:
        print(f"append error: {e}")


def delete_file(path):
    try:
        os.remove(_full(path))
    except:
        pass


# ============================================================
#                    🤖 دوال تلجرام
# ============================================================
def bot(method, data=None, files=None):
    if data is None:
        data = {}
    for k, v in list(data.items()):
        if isinstance(v, bool):
            data[k] = "true" if v else "false"
    url = f"{API_URL}/{method}"
    try:
        if files:
            r = requests.post(url, data=data, files=files, timeout=600)
        else:
            r = requests.post(url, data=data, timeout=30)
        return r.json()
    except Exception as e:
        print(f"[bot error] {method}: {e}")
        return {}


# ============================================================
#      🎵 تحميل تيك توك - بدون علامة مائية أولاً
# ============================================================
def tik_no_watermark(query, from_id):
    """
    تحميل بأولوية: بدون علامة مائية أولاً
    1) tikwm.com (no watermark)
    2) tikwm.com (hd)
    3) yt-dlp كاحتياطي
    """

    # ====== 1) tikwm - بدون علامة مائية ======
    try:
        print("🔄 tikwm (بدون علامة)...")
        r = requests.get(
            "https://www.tikwm.com/api/",
            params={"url": query, "hd": 0},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        data = r.json()
        if data.get("code") == 0 and data.get("data"):
            d = data["data"]
            url = "https://www.tikwm.com" + d.get("play", "")
            print(f"⬇️ تحميل بدون علامة: {url[:70]}...")

            tmp = os.path.join(TEMP_DIR, f"{from_id}_nowm.mp4")
            r2 = requests.get(url, timeout=300,
                              headers={"User-Agent": "Mozilla/5.0"},
                              stream=True)
            with open(tmp, "wb") as f:
                for chunk in r2.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

            size_mb = os.path.getsize(tmp) / (1024 * 1024)
            print(f"✅ تم التحميل بدون علامة: {size_mb:.2f} MB")

            return {
                "source": "tikwm-بدون علامة",
                "title": d.get("title", ""),
                "author": d.get("author", {}).get("unique_id", ""),
                "author_name": d.get("author", {}).get("nickname", ""),
                "duration": d.get("duration", 0),
                "resolution": f"{d.get('width', '?')}x{d.get('height', '?')}",
                "file_path": tmp,
                "size_mb": size_mb,
                "has_watermark": False,
            }
    except Exception as e:
        print(f"❌ tikwm nowm failed: {e}")

    # ====== 2) tikwm - HD ======
    try:
        print("🔄 tikwm (HD)...")
        r = requests.get(
            "https://www.tikwm.com/api/",
            params={"url": query, "hd": 1},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        data = r.json()
        if data.get("code") == 0 and data.get("data"):
            d = data["data"]
            url = "https://www.tikwm.com" + (d.get("hdplay") or d.get("play", ""))
            print(f"⬇️ تحميل HD: {url[:70]}...")

            tmp = os.path.join(TEMP_DIR, f"{from_id}_hd.mp4")
            r2 = requests.get(url, timeout=300,
                              headers={"User-Agent": "Mozilla/5.0"},
                              stream=True)
            with open(tmp, "wb") as f:
                for chunk in r2.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

            size_mb = os.path.getsize(tmp) / (1024 * 1024)
            print(f"✅ تم التحميل HD: {size_mb:.2f} MB")

            return {
                "source": "tikwm-HD",
                "title": d.get("title", ""),
                "author": d.get("author", {}).get("unique_id", ""),
                "author_name": d.get("author", {}).get("nickname", ""),
                "duration": d.get("duration", 0),
                "resolution": f"{d.get('width', '?')}x{d.get('height', '?')}",
                "file_path": tmp,
                "size_mb": size_mb,
                "has_watermark": False,
            }
    except Exception as e:
        print(f"❌ tikwm HD failed: {e}")

    # ====== 3) yt-dlp (احتياطي - قد يحتوي علامة) ======
    try:
        print("🔄 yt-dlp (احتياطي)...")
        import yt_dlp

        output_template = os.path.join(TEMP_DIR, f"{from_id}_%(id)s.%(ext)s")
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "best[ext=mp4]/best",
            "outtmpl": output_template,
            "noplaylist": True,
            "no_check_certificate": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            file_path = ydl.prepare_filename(info)

            video_id = info.get("id", "")
            if not os.path.exists(file_path):
                for f in os.listdir(TEMP_DIR):
                    if video_id in f and f.endswith((".mp4", ".webm")):
                        file_path = os.path.join(TEMP_DIR, f)
                        break

            if os.path.exists(file_path):
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                print(f"✅ yt-dlp: {size_mb:.2f} MB")

                return {
                    "source": "yt-dlp",
                    "title": info.get("title", ""),
                    "author": info.get("uploader_id", ""),
                    "author_name": info.get("uploader", ""),
                    "duration": info.get("duration", 0),
                    "resolution": f"{info.get('width', '?')}x{info.get('height', '?')}",
                    "file_path": file_path,
                    "size_mb": size_mb,
                    "has_watermark": True,
                }
    except Exception as e:
        print(f"❌ yt-dlp failed: {e}")

    return None


def is_member(channel, user_id):
    if not channel or channel in ("on", "none", ""):
        return True
    try:
        r = requests.get(
            f"{API_URL}/getChatMember",
            params={"chat_id": channel, "user_id": user_id},
            timeout=15,
        ).text
        if ('"status":"left"' in r or '"status":"kicked"' in r
                or 'USER_ID_INVALID' in r or 'chat not found' in r):
            return False
        return True
    except:
        return True


def build_admin_panel(skor):
    return json.dumps({
        "inline_keyboard": [
            [{"text": "- قفل البوت .", "callback_data": "abcd"},
             {"text": "- فتح البوت .", "callback_data": "abcde"}],
            [{"text": "- اعضاء البوت .", "callback_data": "userd"}],
            [{"text": "- تفعيل التنبيه .", "callback_data": "ont"},
             {"text": "- تعطيل التنبيه .", "callback_data": "oft"}],
            [{"text": "- قسم الاذاعةه .", "callback_data": "for"}],
            [{"text": "- قائمةه الاشتراك .", "callback_data": "channel"},
             {"text": f"- الاشتراك ({skor}) .", "callback_data": "off"}],
            [{"text": "- نسخة احتياطيةه .", "callback_data": "file"},
             {"text": "- رفع النسخةه .", "callback_data": "up"}],
            [{"text": "- الاحصائيات .", "callback_data": "pannel"},
             {"text": "- قسم الادمن .", "callback_data": "lIllabbas"}],
            [{"text": "- التعديلات .", "callback_data": "xxxtentacionllllo"}],
            [{"text": "- كليشةه /start .", "callback_data": "editstart"}],
        ]
    }, ensure_ascii=False)


ADMIN_PANEL_TEXT = ("-•\n🤍 | اهلا بك\n🤍 | اليك قائمه الاوامر\n\n"
                    "dev: @qqqqbqq  || 🇮🇶 ")


# ============================================================
#                    🎯 معالج الرسائل الرئيسي
# ============================================================
def handle_update(update):
    message  = update.get("message")
    callback = update.get("callback_query")

    text = None
    chat_id = None
    name = None
    user = None
    message_id = None
    from_id = None
    chat_id2 = None
    data = None

    if message:
        text       = message.get("text")
        chat_id    = message.get("chat", {}).get("id")
        name       = message.get("from", {}).get("first_name")
        user       = message.get("from", {}).get("username")
        message_id = message.get("message_id")
        from_id    = message.get("from", {}).get("id")

    if callback:
        chat_id2   = callback.get("message", {}).get("chat", {}).get("id")
        message_id = callback.get("message", {}).get("message_id")
        data       = callback.get("data")
        from_id    = callback.get("from", {}).get("id")

    if not message and not callback:
        return

    # الحالات
    msg_on      = read_file("msg.php")
    forward_on  = read_file("forward.php")
    midea_on    = read_file("midea.php")
    inlin_on    = read_file("inlin.php")
    photoi_on   = read_file("photoi.php")
    upq_on      = read_file("up.php")
    skor        = read_file("skor.php") or "معطل ⚠️"
    ont         = read_file("ont.php")
    bot_status  = read_file("bot.txt")
    channel     = read_file("link.php")
    link_state  = read_file("link2.php")
    uuser       = read_file("uuser.php")
    k088        = read_file("data/k088.txt")
    q1          = read_file("data/q1.txt")

    # الاشتراك الإجباري
    if message and skor == "مفعل ✅":
        if channel and channel != "on" and not is_member(channel, from_id):
            bot("sendMessage", {
                "chat_id": chat_id,
                "text": ("»  عليك الاشتراك في قناة تحديثات البوت اولا 📨\n"
                         "»  ليمكنك استخدام البوت  🔊\n"
                         "»  اشترك ثم ارسل { /start }\n"
                         f"»  [اضغط هنا للشتراك]({link_state})"),
                "parse_mode": "MarkDown",
                "disable_web_page_preview": True,
            })
            return
        if uuser and uuser != "on" and uuser.strip() and not is_member(uuser.strip(), from_id):
            bot("sendMessage", {
                "chat_id": chat_id,
                "text": ("»  عليك الاشتراك في قناة تحديثات البوت اولا 📨\n"
                         "»  ليمكنك استخدام البوت  🔊\n"
                         "»  اشترك ثم ارسل { /start }\n"
                         f"»  {uuser}"),
            })
            return

    # الأعضاء
    users_raw = read_file("abbas.json")
    users = [u.strip() for u in users_raw.split("\n") if u.strip()]
    if message and str(from_id) not in users:
        append_file("abbas.json", f"{from_id}\n")
        users.append(str(from_id))
    all_users = max(len(users), 0)

    # إحصائيات
    try:
        stats = json.loads(read_file("abbas09.json", "{}"))
    except:
        stats = {}
    stats.setdefault("sudoarr", [])
    stats.setdefault("addmessage", 0)
    stats.setdefault("messagee", 0)

    if message:
        if from_id == ADMIN:
            stats["addmessage"] = stats.get("addmessage", 0) + 1
        else:
            stats["messagee"] = stats.get("messagee", 0) + 1
        write_file("abbas09.json", json.dumps(stats, ensure_ascii=False))

    xll = stats.get("addmessage", 0) + stats.get("messagee", 0)

    # الأدمنية
    adminss_raw = read_file("ad.json")
    adminss = [a.strip() for a in adminss_raw.split("\n") if a.strip()]
    if str(ADMIN) not in adminss:
        append_file("ad.json", f"{ADMIN}\n")
        adminss.append(str(ADMIN))
    is_admin = str(from_id) in adminss

    # اليوم
    d = datetime.now().strftime("%a")
    day_file = f"{d}.txt"
    day_raw = read_file(day_file)
    day = [x.strip() for x in day_raw.split("\n") if x.strip()]
    todayuser = len(day)
    if message and str(from_id) not in day:
        append_file(day_file, f"{from_id}\n")

    user_at = f"@{user}" if user else "بلا معرف"

    # دخول جديد
    if text == "/start" and str(from_id) not in [u for u in users[:-1]]:
        bot("sendMessage", {
            "chat_id": ADMIN,
            "text": ("٭ تم دخول شخص جديد الى البوت الخاص بك 👾\n\n"
                     "• معلومات العضو الجديد .\n"
                     "                 •--•\n"
                     f"• الاسم : {name}\n"
                     f"• المعرف : {user_at}\n"
                     f"• الايدي : {from_id}\n"
                     "                  •--•\n"
                     f"• عدد الاعضاء الكلي : {all_users}\n"),
        })

    # /start للأدمن
    if text == "/start" and is_admin:
        bot("sendMessage", {
            "chat_id": chat_id,
            "text": ADMIN_PANEL_TEXT,
            "parse_mode": "Markdown",
            "reply_markup": build_admin_panel(skor),
        })

    # قسم الأدمن
    if data == "lIllabbas" and is_admin:
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": "اهلا",
            "parse_mode": "Markdown",
            "reply_markup": json.dumps({
                "inline_keyboard": [
                    [{"text": "- رفع ادمن.", "callback_data": "adl"}],
                    [{"text": "- اخر الادمن.", "callback_data": "addmin"}],
                    [{"text": "- حذف الادمنيه.", "callback_data": "delateaddmin"}],
                ]
            }, ensure_ascii=False),
        })

    if data == "adl" and is_admin:
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": "قم بارسال ايدي العضو",
        })
        write_file("data/k088.txt", "k088")

    if text and text != "/start" and k088 == "k088" and is_admin:
        write_file("data/k088.txt", "none")
        if text not in adminss:
            append_file("ad.json", f"{text}\n")
            bot("sendMessage", {"chat_id": chat_id, "text": "تم رفع العضو"})
            bot("sendMessage", {"chat_id": text, "text": "تم رفعك ادمن في البوت"})
        else:
            bot("sendMessage", {"chat_id": chat_id, "text": "العضو ادمن بالفعل"})

    if data == "addmin" and is_admin:
        lines = []
        for i in range(5):
            idx = len(adminss) - 2 - i
            val = adminss[idx] if idx >= 0 else "-"
            lines.append(f" {i+1} - ️{val}")
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": "اخر خمس ادمنيه :\n" + "\n".join(lines),
            "parse_mode": "Markdown",
            "reply_markup": json.dumps({
                "inline_keyboard": [
                    [{"text": "- الصفحه الرئيسيه.", "callback_data": "bak"}]
                ]
            }),
        })

    if data == "delateaddmin" and is_admin:
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": "هل انت متاكد من الحذف",
            "parse_mode": "MarkDown",
            "reply_markup": json.dumps({
                "inline_keyboard": [
                    [{"text": "لا", "callback_data": "bak"}],
                    [{"text": "نعم", "callback_data": "yesaarsslan"}],
                ]
            }, ensure_ascii=False),
        })

    if data == "yesaarsslan" and is_admin:
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": "تم حذف الادمنيه",
            "parse_mode": "MarkDown",
            "reply_markup": json.dumps({
                "inline_keyboard": [
                    [{"text": "الصفحه الرئيسيه", "callback_data": "bak"}]
                ]
            }, ensure_ascii=False),
        })
        write_file("ad.json", f"{ADMIN}\n")

    if data == "abcde" and is_admin:
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": "- اهلا بك مطوري الشهير \n- تم فتح البوت \n- /start",
            "parse_mode": "MarkDown",
            "reply_markup": json.dumps({
                "inline_keyboard": [
                    [{"text": "الصفحه الرئيسيه", "callback_data": "bak"}]
                ]
            }, ensure_ascii=False),
        })
        write_file("bot.txt", "مفتوح")

    if data == "abcd" and is_admin:
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": "- اهلا بك مطوري الشهير \n- تم قفل البوت\n- /start ",
            "parse_mode": "MarkDown",
            "reply_markup": json.dumps({
                "inline_keyboard": [
                    [{"text": "الصفحه الرئيسيه", "callback_data": "bak"}]
                ]
            }, ensure_ascii=False),
        })
        write_file("bot.txt", "متوقف")

    if text == "/start" and bot_status == "متوقف" and str(chat_id) != str(ADMIN):
        bot("sendMessage", {"chat_id": chat_id, "text": "عذرا البوت يخضع للتحديث الان"})
        return

    if data == "userd" and is_admin:
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": f" اهلا بك مطوري الشهير  الادمن\n عدد الاعضاء : ( {all_users} )",
            "parse_mode": "MarkDown",
            "reply_markup": json.dumps({
                "inline_keyboard": [
                    [{"text": "الصفحه الرئيسيه", "callback_data": "bak"}]
                ]
            }, ensure_ascii=False),
        })

    if data == "ont" and is_admin:
        write_file("ont.php", "on")
        bot("answerCallbackQuery", {
            "callback_query_id": callback.get("id"),
            "text": "مرحبا مطوري الشهير \n تم تفعيل الاشعارات في البوت\n➖➖➖➖➖➖➖➖",
            "show_alert": True,
        })

    if data == "oft" and is_admin:
        write_file("ont.php", "off")
        bot("answerCallbackQuery", {
            "callback_query_id": callback.get("id"),
            "text": "مرحبا مطوري الشهير \n⚠ تم تعطيل الاشعارات في البوت\n➖➖➖➖➖➖➖➖",
            "show_alert": True,
        })

    if ont == "on" and from_id != ADMIN and message:
        bot("forwardMessage", {
            "chat_id": ADMIN, "from_chat_id": chat_id, "message_id": message_id,
        })

    # الإذاعة
    if data == "for" and is_admin:
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": "حسنا مطوري الشهير \n قم باختيار ما يناسبك",
            "reply_markup": json.dumps({
                "inline_keyboard": [
                    [{"text": "اذاعه صورة", "callback_data": "photoi"}],
                    [{"text": "اذاعه رسالة", "callback_data": "msg"},
                     {"text": "اذاعه توجيه", "callback_data": "forward"}],
                    [{"text": "اذاعه ميديا", "callback_data": "midea"},
                     {"text": "اذاعه انلاين", "callback_data": "inline"}],
                    [{"text": "رجوع", "callback_data": "bak"}],
                ]
            }, ensure_ascii=False),
        })

    if data == "msg" and is_admin:
        write_file("msg.php", "on")
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": "حسنا مطوري الشهير \n قم بأرسال رسالتك لتحويلها لجميع المشتركين",
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "الغاء", "callback_data": "bak"}]]
            }, ensure_ascii=False),
        })

    if msg_on == "on" and message and text and is_admin:
        sent = 0
        for u in users:
            res = bot("sendMessage", {"chat_id": u, "text": text})
            if res.get("ok"): sent += 1
        bot("sendMessage", {
            "chat_id": chat_id,
            "text": f"حسنا مطوري الشهير \n تم عمل اذاعه بنجاح\n الى ( {sent} ) مشترك",
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "رجوع", "callback_data": "bak"}]]
            }, ensure_ascii=False),
        })
        delete_file("msg.php")

    if data == "forward" and is_admin:
        write_file("forward.php", "on")
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": "حسنا مطوري الشهير \n ارسل الرسالة لتحويلها توجيهاً",
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "الغاء", "callback_data": "bak"}]]
            }, ensure_ascii=False),
        })

    if forward_on == "on" and message and is_admin:
        sent = 0
        for u in users:
            res = bot("forwardMessage", {
                "chat_id": u, "from_chat_id": chat_id, "message_id": message_id,
            })
            if res.get("ok"): sent += 1
        bot("sendMessage", {
            "chat_id": chat_id,
            "text": f"حسنا مطوري الشهير \n تم عمل اذاعه توجيه بنجاح\n الى ( {sent} ) مشترك",
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "رجوع", "callback_data": "bak"}]]
            }, ensure_ascii=False),
        })
        delete_file("forward.php")

    if data == "midea" and is_admin:
        write_file("midea.php", "on")
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": ("حسنا مطوري الشهير \n أرسل الميديا (ماعدى الصورة)\n"
                     "(ملصق - فيديو - بصمه - ملف صوتي - ملف - متحركه)"),
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "الغاء", "callback_data": "bak"}]]
            }, ensure_ascii=False),
        })

    if midea_on == "on" and message and is_admin:
        media_types = {
            "voice": "sendVoice", "audio": "sendAudio", "video": "sendVideo",
            "document": "sendDocument", "sticker": "sendSticker",
        }
        for key, method in media_types.items():
            if key in message:
                val = message[key]
                if isinstance(val, list): val = val[0]
                file_id = val.get("file_id")
                for u in users:
                    payload = {"chat_id": u, key: file_id}
                    if message.get("caption"):
                        payload["caption"] = message["caption"]
                    bot(method, payload)
                delete_file("midea.php")
                bot("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"تم نشر الميديا بنجاح إلى ({all_users}) مشترك",
                })
                break

    if data == "photoi" and is_admin:
        write_file("photoi.php", "on")
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": "حسنا مطوري الشهير \n قم بأرسال الصورة",
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "الغاء", "callback_data": "bak"}]]
            }, ensure_ascii=False),
        })

    if photoi_on == "on" and message and message.get("photo") and is_admin:
        file_id = message["photo"][-1]["file_id"]
        for u in users:
            payload = {"chat_id": u, "photo": file_id}
            if message.get("caption"):
                payload["caption"] = message["caption"]
            bot("sendPhoto", payload)
        bot("sendMessage", {
            "chat_id": chat_id,
            "text": f" مطوري الشهير \n تم نشر الصورة بنجاح\n الى ( {all_users} ) مشترك",
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "رجوع", "callback_data": "bak"}]]
            }, ensure_ascii=False),
        })
        delete_file("photoi.php")

    if data == "inline" and is_admin:
        write_file("inlin.php", "on")
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": "حسنا مطوري الشهير \n قم بتوجيه نص الانلاين",
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "الغاء", "callback_data": "bak"}]]
            }, ensure_ascii=False),
        })

    if inlin_on == "on" and message and is_admin and (
            message.get("forward_from") or message.get("forward_from_chat")):
        for u in users:
            bot("forwardMessage", {
                "chat_id": u, "from_chat_id": chat_id, "message_id": message_id,
            })
        bot("sendMessage", {
            "chat_id": chat_id,
            "text": f"حسنا مطوري الشهير \n تم نشر الانلاين بنجاح\n الى ( {all_users} ) مشترك",
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "رجوع", "callback_data": "bak"}]]
            }, ensure_ascii=False),
        })
        delete_file("inlin.php")

    # الاشتراك
    if data == "channel" and is_admin:
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": "حسنا مطوري الشهير \n قم بتحديد الامر لأتمكن من تنفيذه",
            "reply_markup": json.dumps({
                "inline_keyboard": [
                    [{"text": "قناة خاصة", "callback_data": "link"}],
                    [{"text": "قناة عامة", "callback_data": "user"}],
                    [{"text": "رجوع", "callback_data": "bak"}],
                ]
            }, ensure_ascii=False),
        })

    if data == "link" and is_admin:
        write_file("link.php", "on")
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": ("حسنا مطوري الشهير \n ارفع البوت ادمن في القناة\n"
                     " ثم ارسل توجيه من القناة الى هنا"),
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "رجوع", "callback_data": "bak"}]]
            }, ensure_ascii=False),
        })

    if channel == "on" and message and message.get("forward_from_chat"):
        ch_id = message["forward_from_chat"]["id"]
        bot("sendMessage", {
            "chat_id": chat_id,
            "text": "حسنا مطوري الشهير \n قم الان بأرسال رابط القناة هنا",
        })
        write_file("link.php", str(ch_id))
        write_file("link2.php", "on")

    if link_state == "on" and message and text and is_admin:
        pattern = re.compile(r"(https?://|t\.me|telegram\.me|telesco\.me)", re.IGNORECASE)
        if pattern.search(text):
            bot("sendMessage", {
                "chat_id": chat_id,
                "text": "حسنا مطوري الشهير \n تم تفعيل الاشتراك بنجاح",
                "reply_markup": json.dumps({
                    "inline_keyboard": [[{"text": "اتمام العملية", "callback_data": "bak"}]]
                }, ensure_ascii=False),
            })
            write_file("link2.php", text)
            write_file("skor.php", "مفعل ✅")
        else:
            bot("sendMessage", {
                "chat_id": chat_id,
                "text": "عذرا مطوري الشهير \n قم بأرسال الرابط بصورة صحيحه",
            })

    if data == "user" and is_admin:
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": ("حسنا مطوري الشهير \n ارفع البوت ادمن\n"
                     " ثم ارسل يوزر القناة"),
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "رجوع", "callback_data": "bak"}]]
            }, ensure_ascii=False),
        })
        write_file("uuser.php", "on")

    if uuser == "on" and message and text and is_admin:
        if re.search(r"@|#", text):
            bot("sendMessage", {
                "chat_id": chat_id,
                "text": "حسنا مطوري الشهير \n تم تفعيل الاشتراك بنجاح",
                "reply_markup": json.dumps({
                    "inline_keyboard": [[{"text": "اتمام", "callback_data": "bak"}]]
                }, ensure_ascii=False),
            })
            write_file("skor.php", "مفعل ✅")
            write_file("uuser.php", text)
        else:
            bot("sendMessage", {
                "chat_id": chat_id,
                "text": "عذرا مطوري الشهير \n قم بأرسال يوزر بصورة صحيحه",
            })

    if data == "off" and is_admin:
        if skor != "مفعل ✅":
            bot("answerCallbackQuery", {
                "callback_query_id": callback.get("id"),
                "text": "حالة الاشتراك معطل حالياً",
                "show_alert": True,
            })
        else:
            bot("editMessageText", {
                "chat_id": chat_id2, "message_id": message_id,
                "text": "هل انت متأكد من تعطيل الاشتراك؟",
                "reply_markup": json.dumps({
                    "inline_keyboard": [
                        [{"text": "نعم", "callback_data": "yesde2"},
                         {"text": "لا", "callback_data": "bak"}],
                    ]
                }, ensure_ascii=False),
            })

    if data == "yesde2" and is_admin:
        write_file("uuser.php", "")
        write_file("link.php", "")
        write_file("skor.php", "معطل ⚠️")
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": "حسنا مطوري الشهير \n تم تعطيل الاشتراك",
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "رجوع", "callback_data": "bak"}]]
            }, ensure_ascii=False),
        })

    bloktime = datetime.now().strftime("%I:%M:%S %p")

    if data == "file" and is_admin:
        path = _full("abbas.json")
        if os.path.exists(path):
            with open(path, "rb") as f:
                bot("sendDocument", {
                    "chat_id": chat_id2,
                    "caption": (f" نسخة للمستخدمين  \n"
                                f" وقت الارسال : ( {bloktime} )\n"
                                f" عدد المشتركين : ( {all_users} )"),
                }, files={"document": ("abbas.json", f)})

    if data == "up" and is_admin:
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": "حسنا مطوري الشهير \n ارسل الملف باسم abbas.json",
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "رجوع", "callback_data": "bak"}]]
            }, ensure_ascii=False),
        })
        write_file("up.php", "on")

    if upq_on == "on" and message and message.get("document") and is_admin:
        doc = message["document"]
        if doc.get("file_name") == "abbas.json":
            try:
                info = bot("getFile", {"file_id": doc["file_id"]})
                fp = info.get("result", {}).get("file_path")
                if fp:
                    url = f"https://api.telegram.org/file/bot{API_KEY}/{fp}"
                    r = requests.get(url, timeout=60)
                    with open(_full("abbas.json"), "wb") as f:
                        f.write(r.content)
                    bot("sendMessage", {
                        "chat_id": chat_id,
                        "text": "* تم رفع الملف : abbas.json *",
                        "parse_mode": "MarkDown",
                    })
                    delete_file("up.php")
            except Exception as e:
                bot("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"* فشل رفع الملف : {e}*",
                    "parse_mode": "MarkDown",
                })

    if data == "pannel" and is_admin:
        lines = []
        for i in range(5):
            idx = len(users) - 2 - i
            val = users[idx] if idx >= 0 else "-"
            lines.append(f"▫️ {i+1}- {val}")
        last5 = "\n".join(lines)
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": ("*اهلا بك في قسم - الاحصائيات . 📊\n"
                     "--------------------------\n"
                     f" عدد اعضاء بوتك : {all_users}\n"
                     f" المتفاعلين اليوم  : {todayuser}\n"
                     f" عدد الرسائل المرسله : {stats.get('addmessage', 0)}\n"
                     f" عدد الرسائل المستلمه : {stats.get('messagee', 0)}\n"
                     f" مجموع الرسائل : {xll}\n"
                     "--------------------------\n"
                     f" اخر خمس مشتركين :\n{last5}\n"
                     "--------------------------*"),
            "parse_mode": "MarkDown",
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "الصفحه الرئيسيه", "callback_data": "bak"}]]
            }, ensure_ascii=False),
        })

    if data == "editstart" and is_admin:
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": "قم بارسال رسالة الاستارت الان",
        })
        write_file("data/q1.txt", "q1")

    if text and text != "/start" and q1 == "q1" and is_admin:
        write_file("data/q1.txt", "none")
        write_file("q2.txt", text)
        bot("sendMessage", {"chat_id": chat_id, "text": "تم التعين بنجاح"})

    if data == "bak" and is_admin:
        for f in ["msg.php", "forward.php", "midea.php",
                  "inlin.php", "photoi.php", "up.php"]:
            delete_file(f)
        bot("editMessageText", {
            "chat_id": chat_id2, "message_id": message_id,
            "text": ADMIN_PANEL_TEXT,
            "parse_mode": "Markdown",
            "reply_markup": build_admin_panel(skor),
        })

    # /start العادي - بدون زر المطور
    if text == "/start" and not is_admin:
        default_start = (
            "• اهلا بك اخي في بوت تحميل من تيك توك 🐿️.\n"
            "• فقط ارسل الرابط وسيتم ارسال المقطع بدون علامةه مائيةه 🤍.\n"
            ". — — — — — — — — — — .\n"
            "• Tele : @C2CCM | @C76XU ."
        )
        start_msg = read_file("q2.txt") or default_start
        bot("sendMessage", {
            "chat_id": chat_id,
            "text": start_msg,
        })

    # ============================================================
    #        🎵 تحميل تيك توك (بدون علامة مائية أولاً)
    # ============================================================
    if text and ("tiktok.com" in text.lower() or "tik" in text.lower()):
        print(f"\n{'='*60}")
        print(f"🎵 رابط جديد: {text[:80]}")
        print(f"{'='*60}")

        wait = bot("sendMessage", {
            "chat_id": chat_id,
            "text": "⏳ جاري التحميل...",
        })
        wait_id = wait.get("result", {}).get("message_id")

        result = tik_no_watermark(text, from_id)

        if not result or not os.path.exists(result.get("file_path", "")):
            if wait_id:
                bot("editMessageText", {
                    "chat_id": chat_id,
                    "message_id": wait_id,
                    "text": "❌ تعذر التحميل. جرب رابطاً آخر.",
                })
            return

        file_path = result["file_path"]
        size_mb = result.get("size_mb", 0)
        duration = result.get("duration", 0)
        resolution = result.get("resolution", "غير معروف")

        # العنوان + الدقة + التوقيع فقط
        caption = (
            f"📝 العنوان: {result.get('title', 'بدون عنوان')[:150]}\n"
            f"🎞 الدقة: {resolution}\n"
            ". — — — — — — — — — — .\n"
            "• Tele : @C2CCM | @C76XU ."
        )

        sent_any = False

        if size_mb <= MAX_FILE_SIZE_MB:
            try:
                with open(file_path, "rb") as f:
                    res = bot("sendVideo", {
                        "chat_id": chat_id,
                        "caption": caption,
                        "supports_streaming": True,
                        "duration": int(duration) if duration else 0,
                    }, files={"video": ("video.mp4", f)})
                if res.get("ok"):
                    sent_any = True
                    print("✅ تم الإرسال")
                else:
                    print(f"❌ فشل الإرسال: {res.get('description')}")
            except Exception as e:
                print(f"❌ خطأ إرسال: {e}")
        else:
            if wait_id:
                bot("editMessageText", {
                    "chat_id": chat_id,
                    "message_id": wait_id,
                    "text": (f"⚠️ الفيديو بحجم {size_mb:.1f} MB\n"
                             f"الحد الأقصى {MAX_FILE_SIZE_MB} MB"),
                })

        delete_file(file_path)

        if sent_any:
            if wait_id:
                bot("deleteMessage", {"chat_id": chat_id, "message_id": wait_id})
            print("✅ اكتملت العملية\n")
        else:
            if wait_id and size_mb <= MAX_FILE_SIZE_MB:
                bot("editMessageText", {
                    "chat_id": chat_id,
                    "message_id": wait_id,
                    "text": "❌ فشل الإرسال. حاول مرة أخرى.",
                })


# ============================================================
#                    🔄 Polling
# ============================================================
def main():
    global last_update_id
    print("🟢 البوت يعمل الآن...")
    print(f"📏 الحد الأقصى: {MAX_FILE_SIZE_MB} MB")
    print("اضغط Ctrl+C للإيقاف\n")

    while True:
        try:
            r = requests.get(
                f"{API_URL}/getUpdates",
                params={"offset": last_update_id + 1, "timeout": 30},
                timeout=40,
            ).json()

            if not r.get("ok"):
                print(f"⚠ خطأ: {r.get('description')}")
                time.sleep(3)
                continue

            for u in r.get("result", []):
                last_update_id = u["update_id"]
                try:
                    handle_update(u)
                except Exception as e:
                    print(f"❌ خطأ في المعالجة: {e}")

        except KeyboardInterrupt:
            print("\n🔴 تم إيقاف البوت")
            break
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"⚠ خطأ الاتصال: {e}")
            time.sleep(3)


if __name__ == "__main__":
    try:
        me = requests.get(f"{API_URL}/getMe", timeout=10).json()
        if me.get("ok"):
            print(f"✅ تم الاتصال بالبوت: @{me['result']['username']}")
            print(f"📛 الاسم: {me['result']['first_name']}\n")
            main()
        else:
            print(f"❌ التوكن خطأ: {me.get('description')}")
    except Exception as e:
        print(f"❌ فشل الاتصال: {e}")
