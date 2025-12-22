import logging
import re
import datetime
import os
import openai
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, ContextTypes,
    CommandHandler, MessageHandler, filters
)

# ===================== CONFIG =====================
TOKEN = "7894156599:AAGwxohk-l4fTFrTpRM1Rgp_NqtU4RXGJtg"
ADMIN_ID = 8117695030
OPENAI_API_KEY = "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"

openai.api_key = OPENAI_API_KEY
logging.basicConfig(level=logging.INFO)

# ===================== DONNÉES =====================
SERVICES = {
    "1️⃣ Dimensionnement": "Dimensionnement solaire",
    "2️⃣ Installation": "Installation panneaux / pompes",
    "3️⃣ Maintenance": "Maintenance énergétique",
    "4️⃣ Électricité bâtiment": "Électricité bâtiment",
    "5️⃣ Antenne parabolique": "Antenne parabolique"
}

INDICATIFS = {
    "+235": "Tchad",
    "+237": "Cameroun",
    "+33": "France",
    "+212": "Maroc"
}

FETES = {
    "01-01": "🎉 Bonne année !",
    "01-05": "👷 Bonne fête du Travail !",
    "11-08": "🇹🇩 Bonne fête de l’Indépendance du Tchad !"
}

users = {}

# ===================== MENUS =====================
MENU = ReplyKeyboardMarkup(
    [[k] for k in SERVICES] + [["📞 Contact", "🔙 Menu"]],
    resize_keyboard=True
)

CONTACT_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton("📞 Envoyer mon contact", request_contact=True)],
     ["🔙 Menu"]],
    resize_keyboard=True
)

# ===================== UTILITAIRES =====================
def fete_du_jour():
    return FETES.get(datetime.datetime.now().strftime("%d-%m"), "")

def detecter_pays(numero):
    for code, pays in INDICATIFS.items():
        if code in numero:
            return pays
    return "International"

def texte_valide(txt):
    return len(txt.split()) >= 3

def email_valide(txt):
    return re.match(r"[^@]+@[^@]+\.[^@]+", txt)

def log_data(text):
    with open("logs.csv", "a", encoding="utf-8") as f:
        f.write(text + "\n")

def ia_reponse(texte):
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Tu es un assistant énergétique professionnel et clair."},
            {"role": "user", "content": texte}
        ]
    )
    return response.choices[0].message.content.strip()

# ===================== START =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id] = {"step": "menu"}
    await update.message.reply_text(
        "👋 Bienvenue chez *Revolution Énergie*\n\n"
        "Je suis *Manuel Bot*, votre assistant intelligent 🤖\n"
        "Utilisez le menu ci-dessous pour avancer rapidement.",
        parse_mode="Markdown",
        reply_markup=MENU
    )

# ===================== TEXTES =====================
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    if user.id not in users:
        await start(update, context)
        return

    step = users[user.id]["step"]

    if text.lower() in ["merci", "thanks", "thank you"]:
        await update.message.reply_text(
            "🙏 Le plaisir est partagé.\n"
            "Je suis disponible 24h/24 – 7j/7.\n"
            "N’hésitez pas à revenir."
        )
        return

    if text == "🔙 Menu":
        users[user.id]["step"] = "menu"
        await update.message.reply_text("📋 Menu principal :", reply_markup=MENU)
        return

    if text == "📞 Contact":
        users[user.id]["step"] = "contact"
        await update.message.reply_text(
            "📞 Veuillez envoyer votre contact.",
            reply_markup=CONTACT_MENU
        )
        return

    if text in SERVICES:
        users[user.id]["service"] = SERVICES[text]
        users[user.id]["step"] = "explication"
        await update.message.reply_text(
            f"✍️ Expliquez brièvement votre problème concernant :\n*{SERVICES[text]}*",
            parse_mode="Markdown"
        )
        return

    if step == "explication":
        if not texte_valide(text):
            await update.message.reply_text("❌ Explication trop courte.")
            return

        users[user.id]["probleme"] = ia_reponse(text)
        users[user.id]["step"] = "contact"
        await update.message.reply_text(
            "✅ Demande enregistrée.\n📞 Envoyez votre contact.",
            reply_markup=CONTACT_MENU
        )
        return

    if step == "email":
        if not email_valide(text):
            await update.message.reply_text("❌ Email invalide.")
            return
        users[user.id]["email"] = text
        users[user.id]["step"] = "adresse"
        await update.message.reply_text("📍 Envoyez votre adresse.")
        return

    if step == "adresse":
        users[user.id]["adresse"] = text
        pays = detecter_pays(users[user.id]["phone"])
        fete = fete_du_jour()

        message = "✅ Merci. Notre équipe vous contactera rapidement."
        if fete:
            message += f"\n\n{fete}"

        await update.message.reply_text(message, reply_markup=MENU)

        admin_msg = (
            f"📥 NOUVELLE DEMANDE\n"
            f"👤 {user.full_name}\n"
            f"📞 {users[user.id]['phone']}\n"
            f"📧 {users[user.id]['email']}\n"
            f"📍 {users[user.id]['adresse']}\n"
            f"🌍 {pays}\n"
            f"🛠 {users[user.id]['service']}\n"
            f"📝 {users[user.id]['probleme']}"
        )

        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
        log_data(admin_msg.replace("\n", " | "))
        users[user.id]["step"] = "menu"
        return

    await update.message.reply_text(
        "⚠️ Veuillez utiliser le menu des options.\n"
        "Je suis Manuel Bot, assistant de Revolution Énergie."
    )

# ===================== CONTACT =====================
async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]["phone"] = update.message.contact.phone_number
    users[update.effective_user.id]["step"] = "email"
    await update.message.reply_text("📧 Envoyez maintenant votre email.")

# ===================== VOCAL =====================
async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎙️ Message vocal reçu.\n"
        "Veuillez reformuler en texte pour un traitement rapide."
    )

# ===================== MAIN =====================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, contact))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))
    print("🤖 Manuel Bot est en ligne 24/7")
    app.run_polling()

if __name__ == "__main__":
    main()
