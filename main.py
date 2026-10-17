import os
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==========================================
# إعدادات المشرف والبوت
# ==========================================
ADMIN_IDS = [8316440753]  # الـ ID الخاص بك
BOT_TOKEN = "8653320102:AAH1F_tYwH94CtTKYvYFiqMaLi0GRT90IEw"

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ==========================================
# إعداد قاعدة البيانات المحلية وجداول المستخدمين
# ==========================================
def init_db():
    conn = sqlite3.connect('advanced_bot.db')
    cursor = conn.cursor()
    
    # جدول الأزرار الهرمية
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            title TEXT,
            type TEXT, 
            content_type TEXT, 
            content_value TEXT, 
            FOREIGN KEY(parent_id) REFERENCES buttons(id)
        )
    ''')
    
    # جدول المستخدمين الجدد والتنبيهات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# دوال مساعدة للمستخدمين
def register_user(user_id: int, full_name: str, username: str) -> bool:
    conn = sqlite3.connect('advanced_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    is_exists = cursor.fetchone()
    
    is_new = False
    if not is_exists:
        cursor.execute(
            "INSERT INTO users (user_id, full_name, username) VALUES (?, ?, ?)",
            (user_id, full_name, username)
        )
        conn.commit()
        is_new = True
    else:
        cursor.execute(
            "UPDATE users SET full_name = ?, username = ? WHERE user_id = ?",
            (full_name, username, user_id)
        )
        conn.commit()
    conn.close()
    return is_new

def get_total_users_count() -> int:
    conn = sqlite3.connect('advanced_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

# ==========================================
# 1. لوحة المشرف الشاملة
# ==========================================
async def show_admin_menu(update, context, parent_id=0, edit_message=False):
    conn = sqlite3.connect('advanced_bot.db')
    cursor = conn.cursor()
    
    current_title = "القائمة الرئيسية"
    if parent_id != 0:
        cursor.execute('SELECT title FROM buttons WHERE id = ?', (parent_id,))
        res = cursor.fetchone()
        if res: current_title = res[0]

    cursor.execute('SELECT id, title, type FROM buttons WHERE parent_id = ?', (parent_id,))
    rows = cursor.fetchall()
    conn.close()

    keyboard = []
    for row in rows:
        btn_id, title, b_type = row
        icon = "📂 " if b_type == 'menu' else "📄 "
        keyboard.append([
            InlineKeyboardButton(f"{icon} {title}", callback_data=f"adm_open_{btn_id}"),
            InlineKeyboardButton("⚙️ إداره", callback_data=f"adm_manage_{btn_id}")
        ])

    keyboard.append([InlineKeyboardButton("➕ إضافة زر جديد هنا", callback_data=f"admin_add_{parent_id}")])
    
    if parent_id != 0:
        conn = sqlite3.connect('advanced_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT parent_id FROM buttons WHERE id = ?', (parent_id,))
        p_row = cursor.fetchone()
        conn.close()
        p_parent = p_row[0] if p_row else 0
        keyboard.append([InlineKeyboardButton("🔙 رجوع للقسم السابق", callback_data=f"adm_open_{p_parent}")])

    keyboard.append([InlineKeyboardButton("👁 المعاينة كـ طالب", callback_data="view_as_student_0")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"⚙️ **لوحة التحكم الإدارية**\n📍 القسم الحالي: **[{current_title}]**\n\nيمكنك فتح الأزرار، التعديل عليها، حذفها، أو إضافة محتوى جديد:"

    query = update.callback_query
    if edit_message and query:
        await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        message = update.message if update.message else (query.message if query else None)
        if message:
            await message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# ==========================================
# 2. عرض القائمة للطلاب العاديين
# ==========================================
async def show_student_menu(update, context, parent_id=0, edit_message=False):
    conn = sqlite3.connect('advanced_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, type FROM buttons WHERE parent_id = ?', (parent_id,))
    rows = cursor.fetchall()
    conn.close()

    keyboard = []
    for row in rows:
        btn_id, title, b_type = row
        icon = "📂 " if b_type == 'menu' else "📄 "
        keyboard.append([InlineKeyboardButton(icon + title, callback_data=f"st_click_{btn_id}")])
    
    if parent_id != 0:
        conn = sqlite3.connect('advanced_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT parent_id FROM buttons WHERE id = ?', (parent_id,))
        p_row = cursor.fetchone()
        conn.close()
        p_parent = p_row[0] if p_row else 0
        keyboard.append([InlineKeyboardButton("🔙 رجوع للقائمة السابقة", callback_data=f"st_back_{p_parent}")])
    else:
        if is_admin(update.effective_user.id):
            keyboard.append([InlineKeyboardButton("⚙️ العودة لوحة تحكم المشرف", callback_data="back_to_admin")])

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    text = "أهلاً بك مرحباً بكم في بوت ملازم هندسة الذكاء الاصطناعي للمرحلة الثانية .. للتواصل مع المطور @Asif_3130 .. اختر المادة أو القسم الذي تريده :"

    query = update.callback_query
    if edit_message and query:
        await query.message.edit_text(text, reply_markup=reply_markup)
    else:
        message = update.message if update.message else query.message
        await message.reply_text(text, reply_markup=reply_markup)

# ==========================================
# أمر البداية /start مع نظام التتبع الفوري
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    full_name = user.full_name or "بدون اسم"
    username = f"@{user.username}" if user.username else "لا يوجد معرف"
    
    context.user_data.clear()

    # تسجيل المستخدم والتحقق إن كان جديداً
    is_new_user = register_user(user_id, full_name, username)

    # إرسال تنبيه فوري للأدمن عند دخول مستخدم جديد لأول مرة
    if is_new_user:
        alert_text = (
            "🔔 **تنبيه: انضمام مستخدم جديد للبوت!**\n\n"
            f"👤 **الاسم:** {full_name}\n"
            f"🔗 **المعرف:** {username}\n"
            f"🆔 **الـ ID:** `{user_id}`"
        )
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=alert_text,
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Failed to send admin notification: {e}")

    if is_admin(user_id):
        await show_admin_menu(update, context, parent_id=0)
    else:
        await show_student_menu(update, context, parent_id=0)

# ==========================================
# 3. أمر الإحصائيات /stats الخاص بالأدمن
# ==========================================
async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("عذراً، هذا الأمر مخصص لمالك البوت فقط.")
        return

    total_users = get_total_users_count()
    await update.message.reply_text(f"📊 **إحصائيات البوت:**\n\nعدد المستخدمين الإجمالي: **{total_users}** مستخدم.")

# ==========================================
# معالجة تفاعلات الأزرار للمشرف والطالب
# ==========================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("adm_open_"):
        parent_id = int(data.replace("adm_open_", ""))
        await show_admin_menu(update, context, parent_id=parent_id, edit_message=True)

    elif data.startswith("adm_manage_"):
        btn_id = int(data.replace("adm_manage_", ""))
        conn = sqlite3.connect('advanced_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT title, parent_id, type FROM buttons WHERE id = ?', (btn_id,))
        btn = cursor.fetchone()
        conn.close()

        if btn:
            title, parent_id, b_type = btn
            keyboard = [
                [InlineKeyboardButton("✏️ تعديل اسم الزر", callback_data=f"adm_edit_name_{btn_id}")],
                [InlineKeyboardButton("🗑 حذف هذا الزر بالكامل", callback_data=f"adm_delete_{btn_id}")],
                [InlineKeyboardButton("🔙 إلغاء ورجوع", callback_data=f"adm_open_{parent_id}")]
            ]
            await query.message.edit_text(
                f"⚙️ **إدارة الزر:** [{title}]\nاختر الإجراء المطلوب:",
                reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
            )

    elif data.startswith("adm_edit_name_"):
        btn_id = int(data.replace("adm_edit_name_", ""))
        context.user_data['editing_btn_id'] = btn_id
        
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="back_to_admin")]]
        await query.message.edit_text(
            "✍️ أرسل الآن **الاسم الجديد** لهذا الزر في رسالة نصية:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("adm_delete_"):
        btn_id = int(data.replace("adm_delete_", ""))
        conn = sqlite3.connect('advanced_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT parent_id, title FROM buttons WHERE id = ?', (btn_id,))
        res = cursor.fetchone()
        parent_id = res[0] if res else 0
        btn_title = res[1] if res else ""

        cursor.execute('DELETE FROM buttons WHERE id = ? OR parent_id = ?', (btn_id, btn_id))
        conn.commit()
        conn.close()

        await query.answer(f"تم حذف [{btn_title}] بنجاح!", show_alert=True)
        await show_admin_menu(update, context, parent_id=parent_id, edit_message=True)

    elif data.startswith("admin_add_"):
        parent_id = int(data.replace("admin_add_", ""))
        context.user_data['waiting_for_title'] = True
        context.user_data['current_parent_id'] = parent_id
        
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="back_to_admin")]]
        await query.message.edit_text(
            "✍️ أرسل الآن في رسالة نصية **اسم الزر الجديد** الذي تريد إضافته:",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
        )

    elif data.startswith("view_as_student_"):
        await show_student_menu(update, context, parent_id=0, edit_message=True)

    elif data == "back_to_admin":
        context.user_data.clear()
        await show_admin_menu(update, context, parent_id=0, edit_message=True)

    elif data.startswith("st_click_"):
        btn_id = int(data.replace("st_click_", ""))
        conn = sqlite3.connect('advanced_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT title, type, content_type, content_value, parent_id FROM buttons WHERE id = ?', (btn_id,))
        btn = cursor.fetchone()
        conn.close()

        if btn:
            title, b_type, c_type, c_val, p_id = btn
            if b_type == 'menu':
                await show_student_menu(update, context, parent_id=btn_id, edit_message=True)
            else:
                if c_type == 'text':
                    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data=f"st_back_{p_id}")]]
                    await query.message.edit_text(f"📖 **{title}**\n\n{c_val}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
                elif c_type == 'document':
                    await context.bot.send_document(chat_id=query.message.chat_id, document=c_val, caption=f"📄 {title}")
                elif c_type == 'photo':
                    await context.bot.send_photo(chat_id=query.message.chat_id, photo=c_val, caption=f"🖼 {title}")

    elif data.startswith("st_back_"):
        parent_id = int(data.replace("st_back_", ""))
        await show_student_menu(update, context, parent_id=parent_id, edit_message=True)

# ==========================================
# معالجة الرسائل النصية والإدارية
# ==========================================
async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    text = update.message.text

    if context.user_data.get('editing_btn_id'):
        btn_id = context.user_data['editing_btn_id']
        conn = sqlite3.connect('advanced_bot.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE buttons SET title = ? WHERE id = ?', (text, btn_id))
        cursor.execute('SELECT parent_id FROM buttons WHERE id = ?', (btn_id,))
        p_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        context.user_data.clear()
        await update.message.reply_text("✅ تم تعديل اسم الزر بنجاح!")
        await show_admin_menu(update, context, parent_id=p_id)
        return

    if context.user_data.get('waiting_for_title'):
        context.user_data['new_button_title'] = text
        context.user_data['waiting_for_title'] = False
        context.user_data['waiting_for_type'] = True

        keyboard = [
            [InlineKeyboardButton("📂 قائمة فرعية (تتيح إضافة أزرار أخرى بداخلها)", callback_data="type_menu")],
            [InlineKeyboardButton("📄 محتوى فردي (ملف PDF، صورة، أو نص)", callback_data="type_content")]
        ]
        await update.message.reply_text(
            f"تم تسجيل اسم الزر: **{text}**.\nالآن اختر نوع الزر:",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
        )
        return

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "type_menu":
        title = context.user_data['new_button_title']
        parent_id = context.user_data['current_parent_id']

        conn = sqlite3.connect('advanced_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO buttons (parent_id, title, type)
            VALUES (?, ?, ?)
        ''', (parent_id, title, 'menu'))
        conn.commit()
        conn.close()

        context.user_data.clear()
        await query.message.edit_text(f"✅ تم إنشاء القائمة الفرعية [{title}] بنجاح!")
        await show_admin_menu(update, context, parent_id=parent_id)

    elif data == "type_content":
        context.user_data['waiting_for_type'] = False
        context.user_data['waiting_for_media_or_text'] = True
        await query.message.edit_text("📥 أرسل الآن **ملف الـ PDF**، أو **الصورة**، أو **النص** المخصص لهذا الزر:")

async def admin_media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    if context.user_data.get('waiting_for_media_or_text'):
        title = context.user_data['new_button_title']
        parent_id = context.user_data['current_parent_id']
        message = update.message

        c_type = ""
        c_val = ""

        if message.document:
            c_type = "document"
            c_val = message.document.file_id
        elif message.photo:
            c_type = "photo"
            c_val = message.photo[-1].file_id
        elif message.text:
            c_type = "text"
            c_val = message.text
        else:
            await message.reply_text("يرجى إرسال ملف صالح أو نص.")
            return

        conn = sqlite3.connect('advanced_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO buttons (parent_id, title, type, content_type, content_value)
            VALUES (?, ?, ?, ?, ?)
        ''', (parent_id, title, 'content', c_type, c_val))
        conn.commit()
        conn.close()

        context.user_data.clear()
        await message.reply_text(f"✅ تم حفظ الزر [{title}] وتعيين محتواه بنجاح!")
        await show_admin_menu(update, context, parent_id=parent_id)

# ==========================================
# تشغيل البوت
# ==========================================
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^type_"))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), admin_text_handler))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, admin_media_handler))
    
    print("البوت الهرمي المتطور مع ميزة التتبع يعمل الآن بنجاح...")
    app.run_polling(drop_pending_updates=True)