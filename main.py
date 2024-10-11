import os
import zipfile
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TELEGRAM_BOT_TOKEN = 'TELEGRAM_BOT_TOKEN'

ALLOWED_USERS = [USER_IDS]  

selected_files = {}

def list_files_in_directory(directory):
    try:
        files = os.listdir(directory)
        return files
    except FileNotFoundError:
        return []
    except PermissionError:
        return []
    except Exception as e:
        print(f"Error accessing directory {directory}: {e}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("Unfortunately, you do not have access to this bot.")
        return

    selected_files[user_id] = []
    directory = '/'
    await show_directory_contents(update, context, directory)

async def show_directory_contents(update, context, directory):
    user_id = update.effective_user.id
    files = list_files_in_directory(directory)
    files.sort(key=lambda x: x.lower())

    keyboard = []
    for file in files:
        file_path = os.path.join(directory, file)
        is_selected = file_path in selected_files.get(user_id, [])
        button_label = f"🟩" if is_selected else f"🟥"
        emoji = "📁" if os.path.isdir(file_path) else "📄"
        
        keyboard.append([
            InlineKeyboardButton(f"{emoji} {file}", callback_data=f"browse:{file_path}"),
            InlineKeyboardButton(button_label, callback_data=f"select:{file_path}")
        ])

    keyboard.append([InlineKeyboardButton('✔️ Confirm Selections', callback_data='confirm_selection')])

    if directory != '/':
        keyboard.append([InlineKeyboardButton('🔙 Go Back', callback_data=f"back:{directory}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text('Directory Contents:', reply_markup=reply_markup)
    else:
        await update.message.reply_text('Directory Contents:', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split(':')
    action = data[0]
    user_id = query.from_user.id

    if action == 'browse':
        directory = data[1]
        await show_directory_contents(update, context, directory)

    elif action == 'select':
        selected_path = data[1]

        if user_id not in selected_files:
            selected_files[user_id] = []

        if selected_path in selected_files[user_id]:
            selected_files[user_id].remove(selected_path)
        else:
            selected_files[user_id].append(selected_path)

        await show_directory_contents(update, context, os.path.dirname(selected_path))

    elif action == 'confirm_selection':
        if user_id in selected_files and selected_files[user_id]:
            await query.edit_message_text(text="Preparing and sending the selected files...")
            await send_selected_files(context.bot, query.message.chat_id, selected_files[user_id])
            await query.edit_message_text(text="The selected files have been successfully sent!")
        else:
            await query.edit_message_text(text="No file has been selected!")

    elif action == 'back':
        current_directory = data[1]
        parent_directory = os.path.dirname(current_directory)
        await show_directory_contents(update, context, parent_directory)

async def send_selected_files(bot: Bot, chat_id, files):
    last_message = None

    for file_path in files:
        if os.path.isdir(file_path):
            zip_file_path = await zip_directory(file_path)
            last_message = await send_file_to_telegram(bot, zip_file_path, chat_id)
            os.remove(zip_file_path)
        elif os.path.isfile(file_path):
            last_message = await send_file_to_telegram(bot, file_path, chat_id)

    return last_message

async def zip_directory(directory_path):
    zip_file_name = os.path.basename(directory_path.rstrip('/')) + '.zip'
    zip_file_path = os.path.join('/tmp', zip_file_name)

    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.join(directory_path, '..'))
                zipf.write(file_path, arcname)

    return zip_file_path

async def send_file_to_telegram(bot: Bot, file_path, chat_id):
    with open(file_path, 'rb') as f:
        return await bot.send_document(chat_id=chat_id, document=f)

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button))
    application.run_polling()

if __name__ == '__main__':
    main()
