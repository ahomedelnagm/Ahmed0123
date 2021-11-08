import asyncio
from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant
from helpers.filters import command
from helpers.decorators import authorized_users_only, errors
from callsmusic.callsmusic import client as USER
from config import BOT_USERNAME, SUDO_USERS


@Client.on_message(command(["userbotjoin", f"userbotjoin@{BOT_USERNAME}"]) & ~filters.private & ~filters.bot)
@authorized_users_only
@errors
async def addchannel(client, message):
    chid = message.chat.id
    try:
        invitelink = await client.export_chat_invite_link(chid)
    except:
        await message.reply_text(
            "<b> قم بترقيتي كمسؤول أولاً! </ b>",
        )
        return

    try:
        user = await USER.get_me()
    except:
        user.first_name = "مساعد موسيقى"

    try:
        await USER.join_chat(invitelink)
        await USER.send_message(message.chat.id, "🤖: لقد انضممت هنا لتشغيل الموسيقى في الدردشة الصوتية")
    except UserAlreadyParticipant:
        await message.reply_text(
            f"<b> ✅ userbot انضم بالفعل إلى هذه المجموعة. </ b>",
        )
    except Exception as e:
        print(e)
        await message.reply_text(
            f"<b> 🛑 خطأ في انتظار الفيضان 🛑 \n \n تعذر على المستخدم {user.first_name} الانضمام إلى مجموعتك بسبب كثرة طلبات الانضمام إلى userbot."
           +f"\n \ أو إضافة المساعد يدويًا إلى مجموعتك وحاول مرة أخرى </ b>",
        )
        return
    await message.reply_text(
        f"<b> ✅ userbot انضم بنجاح إلى هذه المجموعة. </ b>",
    )


@Client.on_message(command(["userbotleave", f"userbotleave@{BOT_USERNAME}"]) & filters.group & ~filters.edited)
@authorized_users_only
async def rem(client, message):
    try:
        await USER.send_message(message.chat.id, "✅ غادر userbot المجموعة بنجاح")
        await USER.leave_chat(message.chat.id)
    except:
        await message.reply_text(
            "<b> تعذر على المستخدم مغادرة مجموعتك ، فقد يكون مصابًا بالفيضانات. \n\ ولا يطردني يدويًا من مجموعتك </b>"
        )

        return


@Client.on_message(command(["userbotleaveall", f"userbotleaveall@{BOT_USERNAME}"]))
async def bye(client, message):
    if message.from_user.id not in SUDO_USERS:
        return

    left = 0
    failed = 0
    lol = await message.reply("مساعد مغادرة جميع الدردشات")
    async for dialog in USER.iter_dialogs():
        try:
            await USER.leave_chat(dialog.chat.id)
            left += 1
            await lol.edit(f"غادر المساعد كل المجموعة ... \ n \ n على اليسار: محادثات {left}. فشل: {failed} الدردشات.")
        except:
            failed += 1
            await lol.edit(f"مغادرة المساعد ... اليسار: {left} الدردشات. فشل: الدردشات {failed}.")
        await asyncio.sleep(0.7)
    await client.send_message(message.chat.id, f"غادر {left} الدردشات. فشل الدردشات {failed}.")


@Client.on_message(command(["userbotjoinchannel", "ubjoinc"]) & ~filters.private & ~filters.bot)
@authorized_users_only
@errors
async def addcchannel(client, message):
    try:
      conchat = await client.get_chat(message.chat.id)
      conid = conchat.linked_chat.id
      chid = conid
    except:
      await message.reply("هل الدردشة مرتبطة حتى؟")
      return    
    chat_id = chid
    try:
        invitelink = await client.export_chat_invite_link(chid)
    except:
        await message.reply_text(
            "<b> قم بترقيتي كمسؤول المجموعة أولاً! </ b>",
        )
        return

    try:
        user = await USER.get_me()
    except:
        user.first_name = "helper"

    try:
        await USER.join_chat(invitelink)
        await USER.send_message(message.chat.id, "🤖: لقد انضممت هنا كما طلبت")
    except UserAlreadyParticipant:
        await message.reply_text(
            "<b> المساعد موجود بالفعل في قناتك </b>",
        )
        return
    except Exception as e:
        print(e)
        await message.reply_text(
            f"<b> 🛑 خطأ في انتظار الفيضان 🛑 \n\n تعذر على المستخدم {user.first_name} الانضمام إلى قناتك بسبب كثرة طلبات الانضمام إلى userbot! تأكد من عدم حظر المستخدم في القناة."
            f"\n\n أو أضف @{ASSISTANT_NAME} يدويًا إلى مجموعتك وحاول مرة أخرى </b>",
        )
        return
    await message.reply_text(
        "<b> انضم userbot المساعد إلى قناتك </b>",
    )
