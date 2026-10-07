# -*- coding: utf-8 -*-
"""
بوت تلجرام - تحميل تيك توك بدون علامة مائية
مع نظام تدوير IP (بروكسي مجاني)
"""

import os
import re
import json
import time
import random
import threading
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

# ============================================================
#          🌐 نظام إدارة البروكسي (IP Rotation)
# ============================================================
proxies_pool = []  # قائمة البروكسيات النشطة
proxies_lock = threading.Lock()


def load_proxies():
    """جلب قائمة بروكسيات جديدة من مصادر موثوقة"""
    global proxies_pool
    sources = [
        "https://raw.githubusercontent.com/stormsia/proxy-list/main/http.txt",
        "https://raw.githubusercontent.com/sakha1370/OpenRay/refs/heads/main/output/all_valid_proxies.txt",
    ]
    new_proxies = set()
    print("🔄 جاري جلب قوائم البروكسي...")

    for url in sources:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                lines = r.text.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if line and ":" in line:
                        new_proxies.add(line)
            print(f"   ✅ تم جلب {len(new_proxies)} بروكسي من {url.split('/')[-1]}")
        except Exception as e:
            print(f"   ❌ فشل جلب من {url}: {e}")

    if not new_proxies:
        print("⚠️ لم يتم جلب أي بروكسي جديد. سيتم استخدام القائمة القديمة إن وجدت.")
        return

    # اختبار البروكسيات الجديدة
    valid_proxies = []
    print(f"🔍 جاري اختبار {len(new_proxies)} بروكسي...")
    for proxy in list(new_proxies)[:50]:  # اختبر أول 50 لتوفير الوقت
        proxy_url = f"http://{proxy}"
        try:
            r = requests.get("https://api.ipify.org", proxies={"http": proxy_url, "https": proxy_url}, timeout=5)
            if r.status_code == 200:
                valid_proxies.append(proxy)
                if len(valid_proxies) >= 20:  # احتفظ بأول 20 بروكسي يعمل
                    break
        except:
            continue

    with proxies_lock:
        proxies_pool = valid_proxies

    print(f"✅ تم العثور على {len(proxies_pool)} بروكسي صالح للعمل.")


def get_random_proxy():
    """إرجاع بروكسي عشوائي من القائمة النشطة"""
    with proxies_lock:
        if not proxies_pool:
            return None
        return random.choice(proxies_pool)


def start_proxy_updater():
    """تشغيل محدث البروكسي في خيط منفصل"""
    def updater():
        while True:
            load_proxies()
            time.sleep(1800)  # تحديث كل 30 دقيقة

    thread = threading.Thread(target=updater, daemon=True)
    thread.start()


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
#      🎵 تحميل تيك توك - مع تدوير البروكسي
# ============================================================
def tik_no_watermark(query, from_id):
    """
    تحميل بأولوية: بدون علامة مائية أولاً
    مع محاولة استخدام بروكسي مختلف في كل مرة
    """

    # المحاولة الأولى: باستخدام بروكسي
    proxy = get_random_proxy()
    proxies_dict = None
    if proxy:
        proxies_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        print(f"🌐 استخدام البروكسي: {proxy}")
    else:
        print("⚠️ لا يوجد بروكسي متاح، سيتم المحاولة بدون بروكسي.")

    UA = "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"

    # ====== المحاولة 1: tikwm.com ======
    try:
        print("🔄 [1] tikwm...")
        r = requests.get(
            "https://www.tikwm.com/api/",
            params={"url": query, "hd": 0},
            headers={"User-Agent": UA},
            proxies=proxies_dict,
            timeout=30,
        )
        data = r.json()
        if data.get("code") == 0 and data.get("data"):
            d = data["data"]
            url = "https://www.tikwm.com" + d.get("play", "")
            tmp = os.path.join(TEMP_DIR, f"{from_id}_tikwm.mp4")
            r2 = requests.get(url, timeout=300, headers={"User-Agent": UA},
                              proxies=proxies_dict, stream=True)
            with open(tmp, "wb") as f:
                for chunk in r2.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
            if os.path.getsize(tmp) > 5000:
                print(f"✅ tikwm نجح!")
                return {
                    "source": "tikwm",
                    "title": d.get("title", ""),
                    "author": d.get("author", {}).get("unique_id", ""),
                    "author_name": d.get("author", {}).get("nickname", ""),
                    "duration": d.get("duration", 0),
                    "resolution": f"{d.get('width', '?')}x{d.get('height', '?')}",
                    "file_path": tmp,
                    "size_mb": os.path.getsize(tmp) / (1024 * 1024),
                    "has_watermark": False,
                }
    except Exception as e:
        print(f"❌ tikwm: {e}")

    # ====== المحاولة 2: tiklydown ======
    try:
        print("🔄 [2] tiklydown...")
        r = requests.get("https://api.tiklydown.eu.org/api/download",
                         params={"url": query},
                         headers={"User-Agent": UA},
                         proxies=proxies_dict,
                         timeout=30)
        data = r.json()
        if data.get("video") and data["video"].get("noWatermark"):
            url = data["video"]["noWatermark"]
            tmp = os.path.join(TEMP_DIR, f"{from_id}_tikly.mp4")
            r2 = requests.get(url, timeout=300, headers={"User-Agent": UA},
                              proxies=proxies_dict, stream=True)
            with open(tmp, "wb") as f:
                for chunk in r2.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
            if os.path.getsize(tmp) > 5000:
                print(f"✅ tiklydown نجح!")
                return {
                    "source": "tiklydown",
                    "title": data.get("title", ""),
                    "author": "",
                    "author_name": "",
                    "duration": 0,
                    "resolution": "غير معروف",
                    "file_path": tmp,
                    "size_mb": os.path.getsize(tmp) / (1024 * 1024),
                    "has_watermark": False,
                }
    except Exception as e:
        print(f"❌ tiklydown: {e}")

    # ====== المحاولة 3: yt-dlp ======
    try:
        print("🔄 [3] yt-dlp...")
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
        if proxy:
            ydl_opts["proxy"] = f"http://{proxy}"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            file_path = ydl.prepare_filename(info)
            video_id = info.get("id", "")
            if not os.path.exists(file_path):
                for f in os.listdir(TEMP_DIR):
                    if video_id in f and f.endswith((".mp4", ".webm")):
                        file_path = os.path.join(TEMP_DIR, f)
                        break
            if os.path.exists(file_path) and os.path.getsize(file_path) > 5000:
                print(f"✅ yt-dlp نجح!")
                return {
                    "source": "yt-dlp",
                    "title": info.get("title", ""),
                    "author": info.get("uploader_id", ""),
                    "author_name": info.get("uploader", ""),
                    "duration": info.get("duration", 0),
                    "resolution": f"{info.get('width', '?')}x{info.get('height', '?')}",
                    "file_path": file_path,
                    "size_mb": os.path.getsize(file_path) / (1024 * 1024),
                    "has_watermark": True,
                }
    except Exception as e:
        print(f"❌ yt-dlp: {e}")

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

    # ... (باقي الكود كما هو، مع استبدال جزء تحميل الفيديو فقط) ...

    # ============================================================
    #        🎵 تحميل تيك توك (مع نظام البروكسي)
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
                    "text": ("❌ تعذر التحميل.\n\n"
                             "🔹 الأسباب المحتملة:\n"
                             "• جميع البروكسيات المجانية فشلت\n"
                             "• الرابط خاص أو محذوف\n"
                             "• الإنترنت ضعيف\n\n"
                             "جرب رابطاً آخر أو أعد المحاولة."),
                })
            return

        file_path = result["file_path"]
        size_mb = result.get("size_mb", 0)
        duration = result.get("duration", 0)
        resolution = result.get("resolution", "غير معروف")

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

    # بدء نظام تحديث البروكسي في الخلفية
    start_proxy_updater()

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
