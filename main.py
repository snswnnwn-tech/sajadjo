import re, tempfile, os, json, time, asyncio, threading
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import nest_asyncio
import yt_dlp

nest_asyncio.apply()

# ==================== الإعدادات ====================
DATA_FILE = "bot_data.json"
ADMIN_ID = os.environ.get("ADMIN_ID", "5952132218")
TOKEN = os.environ.get("TOKEN", "6198804155:AAHZ-hZ1UM_KI_B8gahXGdx1PbaDpRqu53o")
RATE_LIMIT_SECONDS = 10
TWITTER_DELETE_SECONDS = 60

PLATFORMS = {
    "youtube":   {"name": "يوتيوب",   "emoji": "▶️", "patterns": [r"youtube\.com", r"youtu\.be"]},
    "tiktok":    {"name": "تيك توك",  "emoji": "🎵", "patterns": [r"tiktok\.com"]},
    "instagram": {"name": "إنستغرام", "emoji": "📷", "patterns": [r"instagram\.com", r"instagr\.am"]},
    "twitter":   {"name": "تويتر",   "emoji": "🐦", "patterns": [r"twitter\.com", r"x\.com"]},
}

URL_REGEX = re.compile(r"https?://[^\s]+")
rate_limit = {}
waiting_for = {}


# ==================== Keep-Alive ====================
def keep_alive():
    """يرسل ping كل 5 دقائق لمنع البوت من النوم"""
    url = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("KOYEB_PUBLIC_DOMAIN")
    if not url:
        print("ℹ️ Keep-alive: لا يوجد رابط عام، تم التخطي")
        return
    if not url.startswith("http"):
        url = f"https://{url}"
    
    print(f"🔥 Keep-alive مفعّل على: {url}")
    while True:
        try:
            time.sleep(300)
            import requests
            requests.get(url, timeout=10)
            print(f"✅ Ping: {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"⚠️ Keep-alive error: {e}")


# ==================== البيانات ====================
def load_data():
    default = {
        "users": {},
        "stats": {"total_downloads": 0, "total_users": 0, "by_platform": {}},
        "banned": [],
        "enabled_platforms": {k: True for k in PLATFORMS.keys()},
        "settings": {
            "welcome_message": "مرحباً {name}! 🎬\n\nاختر المنصة التي تريد التحميل منها 👇",
            "force_channels": [],
            "social_links": {
                "developer": "https://t.me/lll6r",
                "channel":   "https://t.me/ISHTAR11",
            }
        }
    }
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for k, v in default.items():
                    data.setdefault(k, v)
                for k, v in default["settings"].items():
                    data["settings"].setdefault(k, v)
                for key in PLATFORMS.keys():
                    data["enabled_platforms"].setdefault(key, True)
                data["stats"].setdefault("by_platform", {})
                return data
    except Exception as e:
        print(f"Load error: {e}")
    return default


def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Save error: {e}")


def cleanup_temp_files():
    try:
        temp_dir = tempfile.gettempdir()
        count = 0
        for fname in os.listdir(temp_dir):
            if fname.startswith(("m_", "media_", "tt_")) and \
               fname.endswith((".mp4", ".mkv", ".webm", ".mp3", ".m4a")):
                try:
                    os.unlink(os.path.join(temp_dir, fname))
                    count += 1
                except:
                    pass
        if count:
            print(f"🧹 تم تنظيف {count} ملف متروك")
    except Exception as e:
        print(f"Cleanup error: {e}")


bot_data = load_data()


# ==================== أدوات مساعدة ====================
def detect_platform(url):
    url_lower = url.lower()
    for key, info in PLATFORMS.items():
        for pattern in info["patterns"]:
            if re.search(pattern, url_lower):
                return key
    return None


def get_main_keyboard(user_id=None):
    keyboard = []
    enabled = bot_data.get("enabled_platforms", {})
    row = []
    for key, info in PLATFORMS.items():
        if enabled.get(key, True):
            row.append(InlineKeyboardButton(
                f"{info['emoji']} {info['name']}",
                callback_data=f"pl_{key}"
            ))
            if len(row) == 2:
                keyboard.append(row)
                row = []
    if row:
        keyboard.append(row)
    
    if not keyboard:
        keyboard.append([InlineKeyboardButton("⚠️ لا توجد منصات مفعلة", callback_data="none")])
    
    keyboard.append([
        InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"),
        InlineKeyboardButton("ℹ️ المساعدة", callback_data="help")
    ])
    
    social = bot_data.get("settings", {}).get("social_links", {})
    social_row = []
    if social.get("developer"):
        social_row.append(InlineKeyboardButton("👤 المطور", url=social["developer"]))
    if social.get("channel"):
        social_row.append(InlineKeyboardButton("📢 القناة", url=social["channel"]))
    if social_row:
        keyboard.append(social_row)
    
    if user_id and str(user_id) == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ إدارة البوت", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== الحذف التلقائي ====================
async def _delete_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id, message_id = context.job.data
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass


def schedule_delete(context: ContextTypes.DEFAULT_TYPE, chat_id, message_id, delay=10):
    if context.job_queue:
        context.job_queue.run_once(_delete_job, delay, data=(chat_id, message_id))


async def send_temp_message(update, context, text, delay=10, **kwargs):
    msg = await update.message.reply_text(text, **kwargs)
    schedule_delete(context, msg.chat_id, msg.message_id, delay)
    return msg


# ==================== فحص الاشتراك الإجباري ====================
async def check_all_subscriptions(context, user_id):
    channels = bot_data["settings"].get("force_channels", [])
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False, ch
        except:
            return False, ch
    return True, None


async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    channels = bot_data["settings"].get("force_channels", [])
    if not channels:
        return True
    
    ok, missing = await check_all_subscriptions(context, update.effective_user.id)
    if ok:
        return True
    
    kb = []
    for ch in channels:
        name = ch.replace("@", "")
        kb.append([InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{name}")])
    kb.append([InlineKeyboardButton("✅ تحققت من الاشتراك", callback_data="check_sub")])
    
    text = (
        "⚠️ **يجب الاشتراك في القنوات أولاً**\n\n"
        + "\n".join([f"📢 {c}" for c in channels])
        + "\n\nبعد الاشتراك اضغط على زر التحقق."
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return False


# ==================== التحميل ====================
def download_media(url, user_id, platform_key):
    filepath = None
    try:
        temp_dir = tempfile.gettempdir()
        out_template = os.path.join(temp_dir, f"m_{user_id}_{int(time.time())}.%(ext)s")
        
        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": out_template,
            "quiet": True, "no_warnings": True, "noplaylist": True,
            "merge_output_format": "mp4",
            "extractor_args": {
                "tiktok": {"api_hostname": ["api22-normal-c-useast2a.tiktokv.com"]},
            },
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
            if not os.path.exists(filepath):
                base, _ = os.path.splitext(filepath)
                for ext in [".mp4", ".mkv", ".webm"]:
                    if os.path.exists(base + ext):
                        filepath = base + ext
                        break
        
        if not filepath or not os.path.exists(filepath):
            return None, None
        
        bot_data["stats"]["total_downloads"] = bot_data["stats"].get("total_downloads", 0) + 1
        by_plat = bot_data["stats"].setdefault("by_platform", {})
        by_plat[platform_key] = by_plat.get(platform_key, 0) + 1
        
        uid = str(user_id)
        if uid not in bot_data.setdefault("users", {}):
            bot_data["users"][uid] = {
                "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "downloads": 0, "username": "", "name": "",
            }
            bot_data["stats"]["total_users"] = len(bot_data["users"])
        
        bot_data["users"][uid]["downloads"] = bot_data["users"][uid].get("downloads", 0) + 1
        bot_data["users"][uid]["last_download"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_data(bot_data)
        
        info_lite = {
            "title": (info or {}).get("title", ""),
            "uploader": (info or {}).get("uploader", ""),
            "duration": (info or {}).get("duration", 0),
        }
        
        return filepath, info_lite
    except Exception as e:
        print(f"[Download Error] {e}")
        return None, None


# ==================== الأوامر ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    
    if user_id in bot_data.get("banned", []):
        await update.message.reply_text("🚫 **أنت محظور!**", parse_mode="Markdown")
        return
    
    if not await check_subscription(update, context):
        return
    
    if user_id != ADMIN_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"👤 مستخدم جديد:\nID: `{user_id}`\n"
                     f"@{user.username if user.username else 'بدون'}\n"
                     f"الاسم: {user.first_name}"
            )
        except:
            pass
    
    if user_id not in bot_data.get("users", {}):
        bot_data.setdefault("users", {})[user_id] = {
            "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "downloads": 0,
            "username": user.username or "",
            "name": user.first_name or ""
        }
        bot_data["stats"]["total_users"] = len(bot_data["users"])
        save_data(bot_data)
    
    welcome = bot_data["settings"]["welcome_message"]
    welcome = welcome.replace("{name}", user.first_name or "عزيزي")
    
    await update.message.reply_text(
        welcome,
        reply_markup=get_main_keyboard(user.id),
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎬 **بوت التحميل**\n\n"
        "📋 **الأوامر:**\n"
        "/start - القائمة الرئيسية\n"
        "/help - المساعدة\n"
        "/stats - الإحصائيات\n"
        "/myid - ايديك\n\n"
        "📥 **الاستخدام:**\n"
        "1. اضغط على زر المنصة\n"
        "2. أرسل الرابط\n"
        "3. استلم الفيديو"
    )
    await send_temp_message(update, context, text, delay=30, parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    s = bot_data.get("stats", {})
    text = (
        f"📊 **إحصائيات البوت:**\n\n"
        f"👥 **المستخدمين:** {s.get('total_users', 0)}\n"
        f"📥 **التحميلات:** {s.get('total_downloads', 0)}"
    )
    by_plat = s.get("by_platform", {})
    if by_plat:
        text += "\n\n🔥 **حسب المنصة:**\n"
        for key, info in PLATFORMS.items():
            count = by_plat.get(key, 0)
            if count:
                text += f"{info['emoji']} {info['name']}: {count}\n"
    if user_id in bot_data.get("users", {}):
        u = bot_data["users"][user_id]
        text += f"\n\n📈 **تحميلاتك:** {u.get('downloads', 0)}"
    await send_temp_message(update, context, text, delay=30, parse_mode="Markdown")


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_temp_message(update, context, f"🆔 ايديك: `{update.effective_user.id}`", delay=15, parse_mode="Markdown")


# ==================== لوحة المالك ====================
def get_admin_panel():
    channels = bot_data["settings"].get("force_channels", [])
    
    keyboard = []
    keyboard.append([InlineKeyboardButton("✏️ تعديل رسالة الترحيب", callback_data="admin_welcome")])
    keyboard.append([InlineKeyboardButton(
        f"📢 قنوات الاشتراك ({len(channels)})",
        callback_data="admin_channels"
    )])
    keyboard.append([InlineKeyboardButton("🔗 روابط التواصل", callback_data="admin_social")])
    keyboard.append([InlineKeyboardButton("🎛️ تفعيل/تعطيل المنصات", callback_data="admin_platforms")])
    keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


async def show_admin_panel(update, context, edit=True):
    query = update.callback_query
    user_id = str(update.effective_user.id)
    if user_id != ADMIN_ID:
        if query:
            await query.answer("❌ للمالك فقط!", show_alert=True)
        else:
            await update.message.reply_text("❌ للمالك فقط!")
        return
    
    text = "⚙️ **لوحة تحكم المالك**\n\nمن هنا تتحكم بكل إعدادات البوت 👇"
    if edit and query:
        await query.edit_message_text(text, reply_markup=get_admin_panel(), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=get_admin_panel(), parse_mode="Markdown")


async def admin_channels_panel(query):
    channels = bot_data["settings"].get("force_channels", [])
    text = (
        "📢 **قنوات الاشتراك الإجباري**\n\n"
        f"عدد القنوات: {len(channels)}\n\n"
    )
    if channels:
        text += "القنوات الحالية:\n" + "\n".join([f"• {c}" for c in channels])
    else:
        text += "لا توجد قنوات حالياً."
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة قناة", callback_data="admin_add_channel")],
    ]
    if channels:
        keyboard.append([InlineKeyboardButton("🗑️ حذف قناة", callback_data="admin_del_channel")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== معالج الرسائل ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    message = update.message.text or ""
    
    admin_state = context.user_data.get("admin_state")
    if user_id == ADMIN_ID and admin_state:
        if admin_state == "waiting_welcome":
            bot_data["settings"]["welcome_message"] = message
            save_data(bot_data)
            context.user_data.pop("admin_state", None)
            await update.message.reply_text(
                "✅ **تم حفظ رسالة الترحيب!**\n\n"
                f"📝 الرسالة الجديدة:\n\n{message}\n\n"
                "💡 يمكنك استخدام `{name}` ليظهر اسم المستخدم.",
                parse_mode="Markdown"
            )
            return
        
        if admin_state == "waiting_add_channel":
            ch = message.strip()
            if not ch.startswith("@") and "t.me/" not in ch:
                ch = "@" + ch.lstrip("@")
            if "t.me/" in ch:
                ch = "@" + ch.split("t.me/")[-1].split("/")[0]
            
            channels = bot_data["settings"].setdefault("force_channels", [])
            if ch in channels:
                await update.message.reply_text("⚠️ القناة موجودة مسبقاً!")
            else:
                channels.append(ch)
                save_data(bot_data)
                await update.message.reply_text(
                    f"✅ **تمت إضافة القناة:** `{ch}`\n\n"
                    "⚠️ تأكد أن البوت **أدمن** في القناة.",
                    parse_mode="Markdown"
                )
            context.user_data.pop("admin_state", None)
            return
        
        if admin_state == "waiting_social_dev":
            bot_data["settings"]["social_links"]["developer"] = message.strip()
            save_data(bot_data)
            context.user_data.pop("admin_state", None)
            await update.message.reply_text("✅ تم حفظ رابط المطور!")
            return
        
        if admin_state == "waiting_social_channel":
            bot_data["settings"]["social_links"]["channel"] = message.strip()
            save_data(bot_data)
            context.user_data.pop("admin_state", None)
            await update.message.reply_text("✅ تم حفظ رابط القناة!")
            return
    
    if user_id in bot_data.get("banned", []):
        await send_temp_message(update, context, "🚫 أنت محظور!", delay=5)
        return
    
    if not await check_subscription(update, context):
        return
    
    platform_key = waiting_for.get(user_id)
    if not platform_key:
        await send_temp_message(
            update, context,
            "⚠️ **اختر منصة أولاً** من القائمة 👇",
            delay=10,
            reply_markup=get_main_keyboard(user_id),
            parse_mode="Markdown"
        )
        return
    
    match = URL_REGEX.search(message)
    if not match:
        await send_temp_message(
            update, context,
            f"⚠️ **أرسل رابط صحيح**\n\n"
            f"المنصة المختارة: {PLATFORMS[platform_key]['emoji']} **{PLATFORMS[platform_key]['name']}**",
            delay=10,
            parse_mode="Markdown"
        )
        return
    
    url = match.group(0)
    detected = detect_platform(url)
    
    if detected != platform_key:
        if detected:
            await send_temp_message(
                update, context,
                f"❌ **رابط خاطئ!**\n\n"
                f"اخترت: {PLATFORMS[platform_key]['emoji']} **{PLATFORMS[platform_key]['name']}**\n"
                f"لكن الرابط من: {PLATFORMS[detected]['emoji']} **{PLATFORMS[detected]['name']}**",
                delay=10,
                parse_mode="Markdown"
            )
        else:
            await send_temp_message(update, context, "❌ رابط غير مدعوم!", delay=10)
        return
    
    now = time.time()
    last = rate_limit.get(user_id, 0)
    if now - last < RATE_LIMIT_SECONDS:
        remain = int(RATE_LIMIT_SECONDS - (now - last))
        await send_temp_message(update, context, f"⏱️ انتظر **{remain}** ثانية.", delay=5, parse_mode="Markdown")
        return
    
    if not bot_data["enabled_platforms"].get(platform_key, True):
        await send_temp_message(update, context, "❌ هذه المنصة معطلة حالياً!", delay=8)
        waiting_for.pop(user_id, None)
        return
    
    waiting_for.pop(user_id, None)
    rate_limit[user_id] = now
    
    info_plat = PLATFORMS[platform_key]
    wait = await update.message.reply_text(
        f"⏳ جاري التحميل من {info_plat['emoji']} {info_plat['name']}..."
    )
    
    path = None
    info = None
    try:
        loop = asyncio.get_event_loop()
        path, info = await loop.run_in_executor(
            None, download_media, url, user_id, platform_key
        )
        
        if not path or not os.path.exists(path):
            await wait.edit_text("❌ فشل التحميل! تحقق من الرابط.")
            schedule_delete(context, wait.chat_id, wait.message_id, 10)
            return
        
        size = os.path.getsize(path)
        mb = size // (1024 * 1024)
        
        if size > 50 * 1024 * 1024:
            await wait.edit_text(f"❌ الفيديو كبير ({mb}MB). الحد 50MB.")
            schedule_delete(context, wait.chat_id, wait.message_id, 10)
            return
        
        title = (info or {}).get("title", "")[:80]
        uploader = (info or {}).get("uploader", "")
        duration = (info or {}).get("duration", 0)
        dur_text = f"{duration // 60}:{duration % 60:02d}" if duration else "؟"
        
        try:
            await wait.delete()
        except:
            pass
        
        caption = f"🎬 **تم التحميل بنجاح!**\n\n"
        caption += f"{info_plat['emoji']} **المنصة:** {info_plat['name']}\n"
        if title: caption += f"📝 **العنوان:** {title}\n"
        if uploader: caption += f"👤 **الناشر:** {uploader}\n"
        caption += f"⏱️ **المدة:** {dur_text}\n"
        caption += f"📦 **الحجم:** {mb}MB\n"
        
        if platform_key == "twitter":
            caption += f"\n⚠️ **سيتم حذف المقطع بعد {TWITTER_DELETE_SECONDS} ثانية!**"
        
        keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]]
        
        with open(path, "rb") as f:
            sent = await update.message.reply_video(
                video=f, caption=caption,
                parse_mode="Markdown",
                supports_streaming=True,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except Exception as e:
                print(f"Delete error: {e}")
        
        path = None
        info = None
        
        if platform_key == "twitter":
            schedule_delete(context, sent.chat_id, sent.message_id, TWITTER_DELETE_SECONDS)
            notif = await update.message.reply_text(
                f"⏱️ **تنبيه:** سيتم حذف المقطع تلقائياً بعد **{TWITTER_DELETE_SECONDS} ثانية**.\n"
                "احفظه الآن إن أردت الاحتفاظ به! 💾"
            )
            schedule_delete(context, notif.chat_id, notif.message_id, TWITTER_DELETE_SECONDS)
    
    except Exception as e:
        print(f"Handler error: {e}")
        try:
            await wait.edit_text(f"❌ خطأ: {str(e)[:100]}")
            schedule_delete(context, wait.chat_id, wait.message_id, 10)
        except:
            pass
    
    finally:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except:
                pass
        path = None
        info = None


# ==================== الأزرار ====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = str(update.effective_user.id)
    
    if data == "check_sub":
        ok, missing = await check_all_subscriptions(context, update.effective_user.id)
        if ok:
            await query.edit_message_text(
                "✅ **تم التحقق من الاشتراك!**\n\nأرسل /start للبدء.",
                parse_mode="Markdown"
            )
        else:
            await query.answer(f"❌ لم تشترك في {missing} بعد!", show_alert=True)
        return
    
    if user_id in bot_data.get("banned", []):
        await query.answer("🚫 أنت محظور!", show_alert=True)
        return
    
    if data.startswith("pl_"):
        platform_key = data.replace("pl_", "")
        if platform_key not in PLATFORMS:
            await query.answer("❌", show_alert=True)
            return
        if not bot_data["enabled_platforms"].get(platform_key, True):
            await query.answer("❌ معطلة حالياً", show_alert=True)
            return
        
        info = PLATFORMS[platform_key]
        waiting_for[user_id] = platform_key
        
        await query.edit_message_text(
            f"{info['emoji']} **{info['name']}**\n\n"
            f"📥 **أرسل الرابط الآن**",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
            ]]),
            parse_mode="Markdown"
        )
        return
    
    if data == "admin_panel":
        await show_admin_panel(update, context)
        return
    
    if data == "admin_welcome":
        context.user_data["admin_state"] = "waiting_welcome"
        current = bot_data["settings"]["welcome_message"]
        await query.edit_message_text(
            f"✏️ **تعديل رسالة الترحيب**\n\n"
            f"📝 الرسالة الحالية:\n{current}\n\n"
            f"💡 أرسل الرسالة الجديدة الآن.\n"
            f"استخدم `{{name}}` لعرض اسم المستخدم.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 إلغاء", callback_data="admin_panel")
            ]]),
            parse_mode="Markdown"
        )
        return
    
    if data == "admin_channels":
        await admin_channels_panel(query)
        return
    
    if data == "admin_add_channel":
        context.user_data["admin_state"] = "waiting_add_channel"
        await query.edit_message_text(
            "➕ **إضافة قناة اشتراك إجباري**\n\n"
            "أرسل:\n"
            "• اسم القناة مع @ مثل: `@MyChannel`\n"
            "• أو رابط مثل: `https://t.me/MyChannel`\n\n"
            "⚠️ **مهم:** البوت يجب أن يكون أدمن في القناة.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 إلغاء", callback_data="admin_channels")
            ]]),
            parse_mode="Markdown"
        )
        return
    
    if data == "admin_del_channel":
        channels = bot_data["settings"].get("force_channels", [])
        if not channels:
            await query.answer("لا توجد قنوات!", show_alert=True)
            return
        kb = []
        for ch in channels:
            kb.append([InlineKeyboardButton(f"🗑️ {ch}", callback_data=f"delch_{ch}")])
        kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_channels")])
        await query.edit_message_text(
            "🗑️ **اختر القناة للحذف:**",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return
    
    if data.startswith("delch_"):
        ch = data.replace("delch_", "")
        channels = bot_data["settings"].get("force_channels", [])
        if ch in channels:
            channels.remove(ch)
            save_data(bot_data)
            await query.answer(f"✅ تم حذف {ch}")
        await admin_channels_panel(query)
        return
    
    if data == "admin_social":
        social = bot_data["settings"].get("social_links", {})
        kb = [
            [InlineKeyboardButton(f"👤 المطور: {social.get('developer', 'غير محدد')[:30]}", callback_data="set_social_dev")],
            [InlineKeyboardButton(f"📢 القناة: {social.get('channel', 'غير محدد')[:30]}", callback_data="set_social_ch")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        await query.edit_message_text(
            "🔗 **روابط التواصل الاجتماعي**\n\nاختر ما تريد تعديله:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )
        return
    
    if data == "set_social_dev":
        context.user_data["admin_state"] = "waiting_social_dev"
        await query.edit_message_text(
            "👤 **رابط المطور**\n\nأرسل الرابط الجديد (مثال: `https://t.me/username`):",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 إلغاء", callback_data="admin_social")
            ]]),
            parse_mode="Markdown"
        )
        return
    
    if data == "set_social_ch":
        context.user_data["admin_state"] = "waiting_social_channel"
        await query.edit_message_text(
            "📢 **رابط القناة**\n\nأرسل الرابط الجديد:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 إلغاء", callback_data="admin_social")
            ]]),
            parse_mode="Markdown"
        )
        return
    
    if data == "admin_platforms":
        enabled = bot_data.get("enabled_platforms", {})
        kb = []
        for key, info in PLATFORMS.items():
            status = "✅ مفعّل" if enabled.get(key, True) else "❌ معطّل"
            kb.append([InlineKeyboardButton(
                f"{info['emoji']} {info['name']} — {status}",
                callback_data=f"toggle_{key}"
            )])
        kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
        await query.edit_message_text(
            "🎛️ **تفعيل/تعطيل المنصات**\n\nاضغط على أي منصة لتبديل حالتها:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )
        return
    
    if data.startswith("toggle_"):
        if user_id != ADMIN_ID:
            await query.answer("❌ للمالك فقط!", show_alert=True)
            return
        key = data.replace("toggle_", "")
        if key not in PLATFORMS:
            await query.answer("❌", show_alert=True)
            return
        enabled = bot_data.setdefault("enabled_platforms", {})
        enabled[key] = not enabled.get(key, True)
        save_data(bot_data)
        
        info = PLATFORMS[key]
        status = "✅ مفعّلة" if enabled[key] else "❌ معطّلة"
        await query.answer(f"{info['emoji']} {info['name']} {status}")
        
        kb = []
        for k, i in PLATFORMS.items():
            s = "✅ مفعّل" if enabled.get(k, True) else "❌ معطّل"
            kb.append([InlineKeyboardButton(f"{i['emoji']} {i['name']} — {s}", callback_data=f"toggle_{k}")])
        kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
        await query.edit_message_text(
            "🎛️ **تفعيل/تعطيل المنصات**\n\nاضغط على أي منصة لتبديل حالتها:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )
        return
    
    if data == "stats":
        s = bot_data.get("stats", {})
        text = (
            f"📊 **الإحصائيات:**\n\n"
            f"👥 المستخدمين: {s.get('total_users', 0)}\n"
            f"📥 التحميلات: {s.get('total_downloads', 0)}"
        )
        if user_id in bot_data.get("users", {}):
            u = bot_data["users"][user_id]
            text += f"\n\n⬇️ **تحميلاتك:** {u.get('downloads', 0)}"
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
            ]]),
            parse_mode="Markdown"
        )
        return
    
    if data == "help":
        text = (
            "🎬 **المساعدة**\n\n"
            "1. اضغط على زر المنصة\n"
            "2. أرسل الرابط\n"
            "3. استلم الفيديو\n\n"
            "🌐 المنصات:\n"
            "▶️ YouTube / 🎵 TikTok\n"
            "📷 Instagram / 🐦 Twitter"
        )
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
            ]]),
            parse_mode="Markdown"
        )
        return
    
    if data == "main_menu":
        waiting_for.pop(user_id, None)
        welcome = bot_data["settings"]["welcome_message"]
        welcome = welcome.replace("{name}", update.effective_user.first_name or "عزيزي")
        await query.edit_message_text(
            welcome,
            reply_markup=get_main_keyboard(user_id),
            parse_mode="Markdown"
        )
        return
    
    if data == "none":
        await query.answer("⚠️ لا توجد منصات مفعلة!", show_alert=True)


# ==================== أوامر المالك ====================
async def admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ للمالك فقط!")
        return
    
    cmd = update.message.text.split()[0].lstrip("/").split("@")[0]
    
    if cmd == "panel":
        await show_admin_panel(update, context, edit=False)
    
    elif cmd == "ban":
        if not context.args:
            await update.message.reply_text("📝 `/ban ايدي`", parse_mode="Markdown")
            return
        target = context.args[0]
        if target not in bot_data["banned"]:
            bot_data["banned"].append(target)
            save_data(bot_data)
            await update.message.reply_text(f"🚫 تم حظر: `{target}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ محظور مسبقاً!")
    
    elif cmd == "unban":
        if not context.args:
            await update.message.reply_text("📝 `/unban ايدي`", parse_mode="Markdown")
            return
        target = context.args[0]
        if target in bot_data["banned"]:
            bot_data["banned"].remove(target)
            save_data(bot_data)
            await update.message.reply_text(f"✅ تم فك الحظر: `{target}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ غير محظور!")
    
    elif cmd == "broadcast":
        if not context.args:
            await update.message.reply_text("📝 `/broadcast رسالتك`", parse_mode="Markdown")
            return
        msg = " ".join(context.args)
        users = list(bot_data.get("users", {}).keys())
        await update.message.reply_text(f"📤 جاري الإرسال لـ {len(users)} مستخدم...")
        ok, fail = 0, 0
        for uid in users:
            try:
                await context.bot.send_message(int(uid), f"📢 **إشعار:**\n\n{msg}", parse_mode="Markdown")
                ok += 1
                await asyncio.sleep(0.05)
            except:
                fail += 1
        await update.message.reply_text(f"✅ نجح: {ok}\n❌ فشل: {fail}")
    
    elif cmd == "users":
        users = bot_data.get("users", {})
        if not users:
            await update.message.reply_text("📭 لا يوجد مستخدمين!")
            return
        sorted_users = sorted(users.items(), key=lambda x: x[1].get("downloads", 0), reverse=True)
        text = f"👥 **إجمالي:** {len(users)}\n🚫 **محظورين:** {len(bot_data['banned'])}\n\n**Top 10:**\n\n"
        for idx, (uid, d) in enumerate(sorted_users[:10], 1):
            text += f"{idx}. `{uid}` — {d.get('downloads', 0)} ⬇️\n"
        await update.message.reply_text(text, parse_mode="Markdown")
    
    elif cmd == "cleanup":
        cleanup_temp_files()
        await update.message.reply_text("🧹 تم تنظيف الملفات المؤقتة.")


# ==================== التشغيل ====================
def main():
    if TOKEN == "ضع_توكن_البوت_هنا":
        print("❌ ضع توكن البوت!")
        return
    if ADMIN_ID == "ضع_ايدي_حسابك_هنا":
        print("❌ ضع ايديك!")
        return
    
    cleanup_temp_files()
    threading.Thread(target=keep_alive, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("myid", myid_command))
    app.add_handler(CommandHandler("panel", admin_commands))
    app.add_handler(CommandHandler("cleanup", admin_commands))
    
    for cmd in ["ban", "unban", "broadcast", "users"]:
        app.add_handler(CommandHandler(cmd, admin_commands))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    enabled = bot_data.get("enabled_platforms", {})
    channels = bot_data["settings"].get("force_channels", [])
    print("=" * 50)
    print("🎬 بوت التحميل - النسخة الاحترافية")
    print("=" * 50)
    print(f"👑 المالك: {ADMIN_ID}")
    print(f"👥 المستخدمين: {bot_data['stats']['total_users']}")
    print(f"🚫 المحظورين: {len(bot_data['banned'])}")
    print(f"📢 قنوات الاشتراك: {len(channels)}")
    print("─" * 50)
    print("📱 حالة المنصات:")
    for key, info in PLATFORMS.items():
        status = "✅" if enabled.get(key, True) else "❌"
        print(f"  {status} {info['emoji']} {info['name']}")
    print("=" * 50)
    print("✅ البوت يعمل...")
    
    app.run_polling()


if __name__ == "__main__":
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                json.load(f)
        except:
            print("⚠️ ملف البيانات تالف، جاري إعادة إنشائه...")
            os.remove(DATA_FILE)
    main()
