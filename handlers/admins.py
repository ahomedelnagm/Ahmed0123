from asyncio import QueueEmpty

from callsmusic import callsmusic
from callsmusic.queues import queues
from config import BOT_USERNAME, que
from cache.admins import admins
from handlers.play import cb_admin_check
from helpers.channelmusic import get_chat_id
from helpers.dbtools import delcmd_is_on, delcmd_off, delcmd_on, handle_user_status
from helpers.decorators import authorized_users_only, errors
from helpers.filters import command, other_filters
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)



@Client.on_message()
async def _(bot: Client, cmd: Message):
    await handle_user_status(bot, cmd)

# Back Button
BACK_BUTTON = InlineKeyboardMarkup([[InlineKeyboardButton("🏡 ", callback_data="cbback")]])

# @Client.on_message(filters.text & ~filters.private)
# async def delcmd(_, message: Message):
#    if await delcmd_is_on(message.chat.id) and message.text.startswith("/") or message.text.startswith("!") or message.text.startswith("."):
#        await message.delete()
#    await message.continue_propagation()

# remove the ( # ) if you want the auto del cmd feature is on

@Client.on_message(command(["reload", f"reload@{BOT_USERNAME}"])  & filters.group & ~filters.edited)
async def update_admin(client, message):
    global admins
    new_admins = []
    new_ads = await client.get_chat_members(message.chat.id, filter="administrators")
    for u in new_ads:
        new_admins.append(u.user.id)
    admins[message.chat.id] = new_admins
    await message.reply_text("بوت ** إعادة تحميلها بشكل صحيح !**\n✅ ** قائمة المشرف ** تم تحديث ** ✅ !**")


# Control Menu Of Player
@Client.on_message(command(["control", f"control@{BOT_USERNAME}"])  & filters.group & ~filters.edited)
@errors
@authorized_users_only
async def controlset(_, message: Message):
    await message.reply_text(
        "**💡 قائمة التحكم مشغل الموسيقى المفتوحة!**\n\n**💭يمكنك التحكم في مشغل الموسيقى فقط عن طريق الضغط على أحد الأزرار أدناه **",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⏸ توقف", callback_data="cbpause"
                    ),
                    InlineKeyboardButton(
                        "▶️ استأنف", callback_data="cbresume"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⏩ تخطي", callback_data="cbskip"
                    ),
                    InlineKeyboardButton(
                        "⏹ انتهاء", callback_data="cbend"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🎸︙اوامر المشرفين ", callback_data="cbdelcmds"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🎸︙اعدادات المجموعه", callback_data="cbgtools"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔻الغاء", callback_data="close"
                    )
                ]
            ]
        )
    )


@Client.on_message(command(["pause", f"pause@{BOT_USERNAME}"])  & filters.group & ~filters.edited)
@errors
@authorized_users_only
async def pause(_, message: Message):
    chat_id = get_chat_id(message.chat)
    if (chat_id not in callsmusic.pytgcalls.active_calls) or (
        callsmusic.pytgcalls.active_calls[chat_id] == "paused"
    ):
        await message.reply_text("❌ لا توجد موسيقى يتم تشغيلها.")
    else:
        callsmusic.pytgcalls.pause_stream(chat_id)
        await message.reply_text("⏸ **تم إيقاف المسار مؤقتا.**\n\n• **لاستئناف التشغيل، استخدم** » `/resume` الاوامر.")


@Client.on_message(command(["resume", f"resume@{BOT_USERNAME}"]) & other_filters)
@errors
@authorized_users_only
async def resume(_, message: Message):
    chat_id = get_chat_id(message.chat)
    if (chat_id not in callsmusic.pytgcalls.active_calls) or (
        callsmusic.pytgcalls.active_calls[chat_id] == "playing"
    ):
        await message.reply_text("❌ لا توجد موسيقى متوقفة مؤقتا.")
    else:
        callsmusic.pytgcalls.resume_stream(chat_id)
        await message.reply_text("▶️ **تم استئناف المسار.**\n\n• **لإيقاف التشغيل مؤقتا، استخدم** » `/pause` الاوامر.")


@Client.on_message(command(["stop", f"stop@{BOT_USERNAME}"]) & other_filters)
@errors
@authorized_users_only
async def stop(_, message: Message):
    chat_id = get_chat_id(message.chat)
    if chat_id not in callsmusic.pytgcalls.active_calls:
        await message.reply_text("❌ لا توجد موسيقى يتم تشغيلها.")
    else:
        try:
            queues.clear(chat_id)
        except QueueEmpty:
            pass

        callsmusic.pytgcalls.leave_group_call(chat_id)
        await message.reply_text("✅ **انتهت الموسيقى التشغيل**")


@Client.on_message(command(["skip", f"skip@{BOT_USERNAME}"]) & other_filters)
@errors
@authorized_users_only
async def skip(_, message: Message):
    global que
    chat_id = get_chat_id(message.chat)
    if chat_id not in callsmusic.pytgcalls.active_calls:
        await message.reply_text("❌ لا توجد موسيقى يتم تشغيلها.")
    else:
        queues.task_done(chat_id)

        if queues.is_empty(chat_id):
            callsmusic.pytgcalls.leave_group_call(chat_id)
        else:
            callsmusic.pytgcalls.change_stream(
                chat_id, queues.get(chat_id)["file"]
            )

    qeue = que.get(chat_id)
    if qeue:
        skip = qeue.pop(0)
    if not qeue:
        return
    await message.reply_text("⏭ **لقد تخطيت الأغنية التالية.**")


@Client.on_message(command(["auth", f"auth@{BOT_USERNAME}"]) & other_filters)
@authorized_users_only
async def authenticate(client, message):
    global admins
    if not message.reply_to_message:
        return await message.reply("💡الرد على رسالة لتخويل المستخدم  !")
    if message.reply_to_message.from_user.id not in admins[message.chat.id]:
        new_admins = admins[message.chat.id]
        new_admins.append(message.reply_to_message.from_user.id)
        admins[message.chat.id] = new_admins
        await message.reply("🟢 مستخدم مصرح به.\n\nمن الآن فصاعدا، يمكن للمستخدم استخدام أوامر المسؤول.")
    else:
        await message.reply("✅ المستخدم أذن بالفعل!")


@Client.on_message(command(["deauth", f"deauth@{BOT_USERNAME}"]) & other_filters)
@authorized_users_only
async def deautenticate(client, message):
    global admins
    if not message.reply_to_message:
        return await message.reply("💡 الرد على رسالة لإلغاء تفويض المستخدم !")
    if message.reply_to_message.from_user.id in admins[message.chat.id]:
        new_admins = admins[message.chat.id]
        new_admins.remove(message.reply_to_message.from_user.id)
        admins[message.chat.id] = new_admins
        await message.reply("🔴مستخدم غير مأثور .\n\nمن الآن وهذا هو المستخدم لا يمكن استخدام أوامر المشرف.")
    else:
        await message.reply("✅ مستخدم تم إلغاء تفويضه بالفعل!")


# this is a anti cmd feature
@Client.on_message(command(["delcmd", f"delcmd@{BOT_USERNAME}"]) & other_filters)
@authorized_users_only
async def delcmdc(_, message: Message):
    if len(message.command) != 2:
        return await message.reply_text("**قراءة رسالة /help لمعرفة كيفية استخدام هذا الأمر**")
    status = message.text.split(None, 1)[1].strip()
    status = status.lower()
    chat_id = message.chat.id
    if status == "on":
        if await delcmd_is_on(message.chat.id):
            return await message.reply_text("✅ تم تنشيطه بالفعل")
        await delcmd_on(chat_id)
        await message.reply_text(
            "🟢 `تم تنشيطه بنجاح` "
        )
    elif status == "off":
        await delcmd_off(chat_id)
        await message.reply_text("🔴 __تم تعطيله بنجاح__")
    else:
        await message.reply_text(
            "قراءة رسالة /help لمعرفة كيفية استخدام هذا الأمر"
        )


# music player callbacks (control by buttons feature)

@Client.on_callback_query(filters.regex("cbpause"))
@cb_admin_check
async def cbpause(_, query: CallbackQuery):
    chat_id = get_chat_id(query.message.chat)
    if (
        query.message.chat.id not in callsmusic.pytgcalls.active_calls
            ) or (
                callsmusic.pytgcalls.active_calls[query.message.chat.id] == "paused"
            ):
        await query.edit_message_text("❌ **لا توجد موسيقى يتم تشغيلها** ", reply_markup=BACK_BUTTON)
    else:
        callsmusic.pytgcalls.pause_stream(query.message.chat.id)
        await query.edit_message_text("⏸ تم إيقاف تشغيل الموسيقى مؤقتا", reply_markup=BACK_BUTTON)

@Client.on_callback_query(filters.regex("cbresume"))
@cb_admin_check
async def cbresume(_, query: CallbackQuery):
    chat_id = get_chat_id(query.message.chat)
    if (
        query.message.chat.id not in callsmusic.pytgcalls.active_calls
            ) or (
                callsmusic.pytgcalls.active_calls[query.message.chat.id] == "resumed"
            ):
        await query.edit_message_text("❌لا توجد موسيقى متوقفة مؤقتا ", reply_markup=BACK_BUTTON)
    else:
        callsmusic.pytgcalls.resume_stream(query.message.chat.id)
        await query.edit_message_text("▶️ تم استئناف تشغيل الموسيقى", reply_markup=BACK_BUTTON)

@Client.on_callback_query(filters.regex("cbend"))
@cb_admin_check
async def cbend(_, query: CallbackQuery):
    chat_id = get_chat_id(query.message.chat)
    if query.message.chat.id not in callsmusic.pytgcalls.active_calls:
        await query.edit_message_text("❌ لا توجد موسيقى يتم تشغيلها", reply_markup=BACK_BUTTON)
    else:
        try:
            queues.clear(query.message.chat.id)
        except QueueEmpty:
            pass
        
        callsmusic.pytgcalls.leave_group_call(query.message.chat.id)
        await query.edit_message_text("✅__تم مسح قائمة انتظار الموسيقى وترك دردشة صوتية بنجاح__ ", reply_markup=BACK_BUTTON)

@Client.on_callback_query(filters.regex("cbskip"))
@cb_admin_check
async def cbskip(_, query: CallbackQuery):
    global que
    chat_id = get_chat_id(query.message.chat)
    if query.message.chat.id not in callsmusic.pytgcalls.active_calls:
        await query.edit_message_text("❌ لا توجد موسيقى يتم تشغيلها", reply_markup=BACK_BUTTON)
    else:
        queues.task_done(query.message.chat.id)

        if queues.is_empty(query.message.chat.id):
            callsmusic.pytgcalls.leave_group_call(query.message.chat.id)
        else:
            callsmusic.pytgcalls.change_stream(
                query.message.chat.id, queues.get(query.message.chat.id)["file"]
            )

    qeue = que.get(chat_id)
    if qeue:
        skip = qeue.pop(0)
    if not qeue:
        return
    await query.edit_message_text(
        "⏭ **لقد تخطيت الأغنية التالية**", reply_markup=BACK_BUTTON
    )

# ban & unban function


@Client.on_message(command("b")  & filters.group & ~filters.edited)
@authorized_users_only
async def ban_user(_, message):
    is_admin = await admin_check(message)
    if not is_admin:
        return

    user_id, user_first_name = extract_user(message)

    try:
        await message.chat.kick_member(user_id=user_id)
    except Exception as error:
        await message.reply_text(str(error))
    else:
        if str(user_id).lower().startswith("@"):
            await message.reply_text(
                "✅ نجح في حظر "f" {user_first_name} "" من هذه المجموعة!"
            )
        else:
            await message.reply_text(
                "✅ banned "
                f"<a href='tg://user?id={user_id}'>"
                f"{user_first_name}"
                "</a>"
                " from this group !"
            )


@Client.on_message(command("tb") & filters.group & ~filters.edited)
@authorized_users_only
async def temp_ban_user(_, message):
    is_admin = await admin_check(message)
    if not is_admin:
        return

    if len(message.command) <= 1:
        return

    user_id, user_first_name = extract_user(message)

    until_date_val = extract_time(message.command[1])
    if until_date_val is None:
        await message.reply_text(
            (
                "نوع الوقت المحدد غير صالح. "" استخدم تنسيق الوقت m أو h أو : {}"
            ).format(message.command[1][-1])
        )
        return

    try:
        await message.chat.kick_member(user_id=user_id, until_date=until_date_val)
    except Exception as error:
        await message.reply_text(str(error))
    else:
        if str(user_id).lower().startswith("@"):
            await message.reply_text(
                "✅ محظور مؤقتا "
                f"{user_first_name}"
                f" for {message.command[1]}!"
            )
        else:
            await message.reply_text(
                "✅ محظور مؤقتا "
                f"<a href='tg://user?id={user_id}'>"
                "from this group, "
                "</a>"
                f" for {message.command[1]}!"
            )


@Client.on_message(command("ub")  & filters.group & ~filters.edited)
@authorized_users_only
async def un_ban_user(_, message):
    is_admin = await admin_check(message)
    if not is_admin:
        return

    user_id, user_first_name = extract_user(message)

    try:
        await message.chat.unban_member(user_id=user_id)
    except Exception as error:
        await message.reply_text(str(error))
    else:
        if str(user_id).lower().startswith("@"):
            await message.reply_text(
                "✅ ok accepted, user "
                f"{user_first_name} can"
                " join to this group again!"
            )
        else:
            await message.reply_text(
                "✅ ok, now "
                f"<a href='tg://user?id={user_id}'>"
                f"{user_first_name}"
                "</a> is not"
                " restricted again!"
            )


@Client.on_message(command("m")  & filters.group & ~filters.edited)
async def mute_user(_, message):
    is_admin = await admin_check(message)
    if not is_admin:
        return

    user_id, user_first_name = extract_user(message)

    try:
        await message.chat.restrict_member(
            user_id=user_id, permissions=ChatPermissions()
        )
    except Exception as error:
        await message.reply_text(str(error))
    else:
        if str(user_id).lower().startswith("@"):
            await message.reply_text(
                "✅ okay,🏻 " f"{user_first_name}" "تم كتم الصوت بنجاح!"
            )
        else:
            await message.reply_text(
                "🏻✅ okay, "
                f"<a href='tg://user?id={user_id}'>"
                "now is"
                "</a>"
                " muted !"
            )


@Client.on_message(command("tm")  & filters.group & ~filters.edited)
async def temp_mute_user(_, message):
    is_admin = await admin_check(message)
    if not is_admin:
        return

    if len(message.command) <= 1:
        return

    user_id, user_first_name = extract_user(message)

    until_date_val = extract_time(message.command[1])
    if until_date_val is None:
        await message.reply_text(
            (
                "نوع الوقت المحدد غير صالح. "" استخدم تنسيق الوقت m أو h أو d: {}"
            ).format(message.command[1][-1])
        )
        return

    try:
        await message.chat.restrict_member(
            user_id=user_id, permissions=ChatPermissions(), until_date=until_date_val
        )
    except Exception as error:
        await message.reply_text(str(error))
    else:
        if str(user_id).lower().startswith("@"):
            await message.reply_text(
                "Muted for a while! "
                f"{user_first_name}"
                f" muted for {message.command[1]}!"
            )
        else:
            await message.reply_text(
                "Muted for a while! "
                f"<a href='tg://user?id={user_id}'>"
                "is"
                "</a>"
                " now "
                f" muted, for {message.command[1]}!"
            )
