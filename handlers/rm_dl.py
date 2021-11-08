# function to remove the downloaded files

import os
from pyrogram import Client, filters
from pyrogram.types import Message
from helpers.filters import command
from helpers.decorators import sudo_users_only, errors

downloads = os.path.realpath("downloads")
raw = os.path.realpath("raw_files")

@Client.on_message(command(["rmd", "rmdownloads", "cleardownloads"]) & ~filters.edited)
@errors
@sudo_users_only
async def clear_downloads(_, message: Message):
    ls_dir = os.listdir(downloads)
    if ls_dir:
        for file in os.listdir(downloads):
            os.remove(os.path.join(downloads, file))
        await message.reply_text("✅ ** أزال جميع الملفات التي تم تنزيلها **")
    else:
        await message.reply_text("❌ ** لم يتم تنزيل أي ملفات**")
