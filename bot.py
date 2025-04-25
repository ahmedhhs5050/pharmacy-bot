from keep_alive import keep_alive
keep_alive()

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import os
import json

TOKEN = "7731991245:AAGrgv_XF78DmQ2lFV20q-OAyBVoPawqGOM"
bot = telebot.TeleBot(TOKEN)

subjects = ["📘 Specialized", "📕 QBD", "📙 CAPT", "📗 Physical Pharmacy", "📒 Biopharmaceutics"]
content_types = ["📄 Slides", "🎧 Records"]

LECTURE_PATH = "lectures"
LINKS_FILE = "drive_links.json"
STUDENTS_FILE = "subscribed_users.json"
UPLOAD_STAGE = {}

# تحميل الملفات الحالية
drive_links = {}
if os.path.exists(LINKS_FILE):
    with open(LINKS_FILE, "r") as f:
        drive_links = json.load(f)

subscribed_users = []
if os.path.exists(STUDENTS_FILE):
    with open(STUDENTS_FILE, "r") as f:
        subscribed_users = json.load(f)

# /start
@bot.message_handler(commands=["start"])
def send_welcome(message):
    if message.chat.id not in subscribed_users:
        subscribed_users.append(message.chat.id)
        with open(STUDENTS_FILE, "w") as f:
            json.dump(subscribed_users, f)

    keyboard = InlineKeyboardMarkup(row_width=2)
    for subject in subjects:
        keyboard.add(InlineKeyboardButton(subject, callback_data=f"subject:{subject[2:]}"))
    keyboard.add(
        InlineKeyboardButton("⬆️ رفع محاضرة", callback_data="upload_start"),
        InlineKeyboardButton("✏️ تعديل/حذف رابط", callback_data="manage_links"),
        InlineKeyboardButton("⬇️ عرض جميع الروابط", callback_data="list_links")
    )
    bot.send_message(
        message.chat.id,
        "👋 مرحبًا بك في *بوت محاضرات الصيدلة*\nاختر المادة أو الإجراء المطلوب:",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

# إرسال إشعار يومي
@bot.message_handler(commands=["notify"])
def notify_all(message):
    if message.chat.id not in subscribed_users:
        bot.reply_to(message, "❌ هذا الأمر مخصص فقط للمشرفين.")
        return
    text = message.text.replace("/notify", "").strip()
    if not text:
        bot.reply_to(message, "⚠️ أرسل إشعارًا مع الأمر مثل: /notify المحاضرة الجديدة متاحة الآن.")
        return
    for user in subscribed_users:
        try:
            bot.send_message(user, f"📢 إشعار يومي:\n{text}")
        except:
            continue
    bot.reply_to(message, "✅ تم إرسال الإشعار لجميع المشتركين.")

# باقي التفاعلات:
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    data = call.data

    if data.startswith("subject:"):
        subject = data.split(":")[1]
        keyboard = InlineKeyboardMarkup(row_width=2)
        for ctype in content_types:
            keyboard.add(InlineKeyboardButton(ctype, callback_data=f"type:{subject}:{ctype[2:]}"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f"{subject} - اختر النوع:", reply_markup=keyboard)

    elif data.startswith("type:"):
        _, subject, ctype = data.split(":")
        keyboard = InlineKeyboardMarkup(row_width=4)
        for week in range(1, 13):
            keyboard.add(InlineKeyboardButton(str(week), callback_data=f"week:{subject}:{ctype}:{week}"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f"{subject} > {ctype} - اختر رقم:", reply_markup=keyboard)

    elif data.startswith("week:"):
        _, subject, ctype, week = data.split(":")
        path = os.path.join(LECTURE_PATH, subject, ctype)
        file_found = False
        for ext in ["pdf", "mp4", "docx"]:
            fpath = os.path.join(path, f"{week}.{ext}")
            if os.path.exists(fpath):
                with open(fpath, "rb") as f:
                    bot.send_document(call.message.chat.id, f)
                file_found = True
                break
        if not file_found:
            key = f"{subject}_{ctype}_{week}"
            if key in drive_links:
                bot.send_message(call.message.chat.id, f"📎 {drive_links[key]}")
            else:
                bot.send_message(call.message.chat.id, "❌ لا يوجد محتوى لهذا الرقم.")

    elif data == "upload_start":
        keyboard = InlineKeyboardMarkup()
        for subject in subjects:
            keyboard.add(InlineKeyboardButton(subject, callback_data=f"upload_subject:{subject[2:]}"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="📤 اختر المادة لرفع محاضرة:", reply_markup=keyboard)

    elif data.startswith("upload_subject:"):
        subject = data.split(":")[1]
        keyboard = InlineKeyboardMarkup()
        for ctype in ["Slides", "Records"]:
            keyboard.add(InlineKeyboardButton(ctype, callback_data=f"upload_type:{subject}:{ctype}"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f"{subject} - اختر النوع:", reply_markup=keyboard)

    elif data.startswith("upload_type:"):
        _, subject, ctype = data.split(":")
        keyboard = InlineKeyboardMarkup()
        for week in range(1, 13):
            keyboard.add(InlineKeyboardButton(str(week), callback_data=f"upload_week:{subject}:{ctype}:{week}"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f"{subject} > {ctype} - اختر الرقم:", reply_markup=keyboard)

    elif data.startswith("upload_week:"):
        _, subject, ctype, week = data.split(":")
        UPLOAD_STAGE[call.from_user.id] = (subject, ctype, week)
        bot.send_message(call.message.chat.id, "📎 أرسل الآن *رابط أو ملف* المحاضرة.", parse_mode="Markdown")

    elif data == "list_links":
        if not drive_links:
            bot.send_message(call.message.chat.id, "🔍 لا يوجد روابط حالياً.")
        else:
            msg = "📚 روابط المحاضرات:\n\n"
            for key, link in drive_links.items():
                msg += f"{key.replace('_', ' > ')}\n{link}\n\n"
            bot.send_message(call.message.chat.id, msg)

    elif data == "manage_links":
        keyboard = InlineKeyboardMarkup()
        for key in drive_links.keys():
            keyboard.add(InlineKeyboardButton(key.replace("_", " > "), callback_data=f"edit:{key}"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="✏️ اختر رابط لتعديله أو حذفه:", reply_markup=keyboard)

    elif data.startswith("edit:"):
        key = data.split(":")[1]
        UPLOAD_STAGE[call.from_user.id] = key
        bot.send_message(call.message.chat.id, f"🔄 أرسل الرابط الجديد لـ {key.replace('_', ' > ')} أو اكتب /delete")

# استقبال روابط أو ملفات
@bot.message_handler(content_types=["text", "document", "video"])
def handle_content(message):
    user_id = message.from_user.id
    stage = UPLOAD_STAGE.get(user_id)
    if not stage:
        return

    if isinstance(stage, tuple):
        subject, ctype, week = stage
        key = f"{subject}_{ctype}_{week}"
        if message.content_type == "text":
            drive_links[key] = message.text.strip()
            with open(LINKS_FILE, "w") as f:
                json.dump(drive_links, f, indent=2)
            bot.send_message(message.chat.id, f"✅ تم حفظ الرابط لـ {subject} > {ctype} > {week}")
        else:
            ext = message.document.file_name.split(".")[-1] if message.document else "mp4"
            os.makedirs(os.path.join(LECTURE_PATH, subject, ctype), exist_ok=True)
            save_path = os.path.join(LECTURE_PATH, subject, ctype, f"{week}.{ext}")
            file_info = bot.get_file(message.document.file_id if message.document else message.video.file_id)
            downloaded = bot.download_file(file_info.file_path)
            with open(save_path, "wb") as f:
                f.write(downloaded)
            bot.send_message(message.chat.id, f"✅ تم رفع الملف لـ {subject} > {ctype} > {week}")
        del UPLOAD_STAGE[user_id]
    else:
        # تعديل رابط
        key = stage
        drive_links[key] = message.text.strip()
        with open(LINKS_FILE, "w") as f:
            json.dump(drive_links, f, indent=2)
        bot.send_message(message.chat.id, f"✅ تم تعديل الرابط لـ {key.replace('_', ' > ')}")
        del UPLOAD_STAGE[user_id]

# حذف رابط
@bot.message_handler(commands=["delete"])
def delete_link(message):
    user_id = message.from_user.id
    key = UPLOAD_STAGE.get(user_id)
    if key and key in drive_links:
        del drive_links[key]
        with open(LINKS_FILE, "w") as f:
            json.dump(drive_links, f, indent=2)
        bot.send_message(message.chat.id, f"🗑️ تم حذف الرابط لـ {key.replace('_', ' > ')}")
        del UPLOAD_STAGE[user_id]
    else:
        bot.send_message(message.chat.id, "❌ لا يوجد رابط لتعديله أو حذفه.")

# تشغيل البوت
print("✅ Bot is running...")
bot.polling(timeout=20, long_polling_timeout=10)
