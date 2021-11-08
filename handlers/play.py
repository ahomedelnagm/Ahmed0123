import os
from asyncio.queues import QueueEmpty
from os import path
from typing import Callable

import aiofiles
import aiohttp
import converter
import ffmpeg
import requests
from cache.admins import admins as a
from callsmusic import callsmusic
from callsmusic.callsmusic import client as USER
from callsmusic.queues import queues
from config import (
    ASSISTANT_NAME,
    BOT_NAME,
    BOT_USERNAME,
    DURATION_LIMIT,
    GROUP_SUPPORT,
    THUMB_IMG,
    UPDATES_CHANNEL,
    que,
)
from downloaders import youtube
from helpers.admins import get_administrators
from helpers.channelmusic import get_chat_id
from helpers.decorators import authorized_users_only
from helpers.filters import command, other_filters
from helpers.gets import get_file_name
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from youtube_search import YoutubeSearch

aiohttpsession = aiohttp.ClientSession()
chat_id = None
useer ="NaN"
DISABLED_GROUPS = []


def cb_admin_check(func: Callable) -> Callable:
    async def decorator(client, cb):
        admemes = a.get(cb.message.chat.id)
        if cb.from_user.id in admemes:
            return await func(client, cb)
        await cb.answer("🦹🏻 يمكن للمسؤول فقط النقر فوق هذا الزر", show_alert=True)
        return
    return decorator                                                                       
                                          
                                                                                    
def transcode(filename):
    ffmpeg.input(filename).output(
        "input.raw",
        format="s16le",
        acodec="pcm_s16le",
        ac=2,
        ar="48k"
    ).overwrite_output().run() 
    os.remove(filename)

# Convert seconds to mm:ss
def convert_seconds(seconds):
    seconds = seconds % (24 * 3600)
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%02d:%02d" % (minutes, seconds)


# Convert hh:mm:ss to seconds
def time_to_seconds(time):
    stringt = str(time)
    return sum(int(x) * 60 ** i for i, x in enumerate(reversed(stringt.split(":"))))


# Change image size
def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    newImage = image.resize((newWidth, newHeight))
    return newImage


async def generate_cover(title, thumbnail):
    async with aiohttp.ClientSession() as session:
        async with session.get(thumbnail) as resp:
            if resp.status == 200:
                f = await aiofiles.open("background.png", mode="wb")
                await f.write(await resp.read())
                await f.close()
    image1 = Image.open("./background.png")
    image2 = Image.open("etc/foreground.png")
    image3 = changeImageSize(1280, 720, image1)
    image4 = changeImageSize(1280, 720, image2)
    image5 = image3.convert("RGBA")
    image6 = image4.convert("RGBA")
    Image.alpha_composite(image5, image6).save("temp.png")
    img = Image.open("temp.png")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("etc/font.otf", 60)
    draw.text((40, 550), "Playing here...", (0, 0, 0), font=font)
    draw.text((40, 630), f"{title[:25]}...", (0, 0, 0), font=font)
    img.save("final.png")
    os.remove("temp.png")
    os.remove("background.png")


@Client.on_message(command(["playlist", f"playlist@{BOT_USERNAME}"]) & filters.group & ~filters.edited)
async def playlist(client, message):
    global que
    if message.chat.id in DISABLED_GROUPS:
        return
    queue = que.get(message.chat.id)
    if not queue:
        await message.reply_text("❌ **لا توجد موسيقى قيد التشغيل حاليًا**")
    temp = []
    for t in queue:
        temp.append(t)
    now_playing = temp[0][0]
    by = temp[0][1].mention(style="md")
    msg = "🎉 **مشغل الان** on {}".format(message.chat.title)
    msg += "\n\n• "+ now_playing
    msg += "\n• Req By "+by
    temp.pop(0)
    if temp:
        msg += "\n\n"
        msg += "**Queued Song**"
        for song in temp:
            name = song[0]
            usr = song[1].mention(style="md")
            msg += f"\n• {name}"
            msg += f"\n• Req by {usr}\n"
    await message.reply_text(msg)
                            
# ============================= Settings =========================================
def updated_stats(chat, queue, vol=100):
    if chat.id in callsmusic.pytgcalls.active_calls:
        stats = "✨ ︙ إعدادات الـتشغيل **{}**".format(chat.title)
        if len(que) > 0:
            stats += "\n\n"
            stats += "💡 ︙ الحجم: {}%\n".format(vol)
            stats += "🎉 ︙ الاغنيه المشغله : `{}`\n".format(len(que))
            stats += "🍥 ︙ قيد التشغيل الآن: **{}**\n".format(queue[0][0])
            stats += "🔮 ︙ طلب من: {}".format(queue[0][1].mention)
    else:
        stats = None
    return stats

def r_ply(type_):
    if type_ == "play":
        pass
    else:
        pass
    mar = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏹", "ترك"),
                InlineKeyboardButton("⏸", "توقف"),
                InlineKeyboardButton("▶️", "تشغيل"),
                InlineKeyboardButton("⏭", "تخطي")
            ],
            [
                InlineKeyboardButton("🎉︙قائمه التشغيل ", "playlist"),
            ],
            [       
                InlineKeyboardButton("🔻الغاء", "cls")
            ]        
        ]
    )
    return mar


@Client.on_message(command(["player", f"player@{BOT_USERNAME}"]) & filters.group & ~filters.edited)
@authorized_users_only
async def settings(client, message):
    playing = None
    if message.chat.id in callsmusic.pytgcalls.active_calls:
        playing = True
    queue = que.get(message.chat.id)
    stats = updated_stats(message.chat, queue)
    if stats:
        if playing:
            await message.reply(stats, reply_markup=r_ply("pause"))
            
        else:
            await message.reply(stats, reply_markup=r_ply("play"))
    else:
        await message.reply("❌ ** لم يتم العثور على الدردشة الصوتية **\n\n» لرجاء تشغيل الدردشة الصوتية أولاً")


@Client.on_message(
    command(["musicplayer", f"musicplayer@{BOT_USERNAME}"]) & ~filters.edited & ~filters.bot & ~filters.private
)
@authorized_users_only
async def music_onoff(_, message):
    global DISABLED_GROUPS
    try:
        user_id = message.from_user.id
    except:
        return
    if len(message.command) != 2:
        await message.reply_text(
            "**لتعطيل او الفتح ارسل احد الامرين** `/musicplayer on` **and** `/musicplayer off`"
        )
        return
    status = message.text.split(None, 1)[1]
    message.chat.id
    if status == "ON" or status == "on" or status == "On":
        lel = await message.reply("`يتم المعالجة...`")
        if not message.chat.id in DISABLED_GROUPS:
            await lel.edit("**تم تنشيط مشغل الموسيقى بالفعل.**")
            return
        DISABLED_GROUPS.remove(message.chat.id)
        await lel.edit(
            f"✅ **تم تنشيط مشغل الموسيقى في هذه الدردشة.**\n\n💬 `{message.chat.id}`"
        )

    elif status == "OFF" or status == "off" or status == "Off":
        lel = await message.reply("`يتم المعالجة...`")
        
        if message.chat.id in DISABLED_GROUPS:
            await lel.edit("**مشغل الموسيقى معطل بالفعل.**")
            return
        DISABLED_GROUPS.append(message.chat.id)
        await lel.edit(
            f"✅ **تم إلغاء تنشيط مشغل الموسيقى في هذه الدردشة.**\n\n💬 `{message.chat.id}`"
        )
    else:
        await message.reply_text(
            "**لتعطيل او الفتح ارسل احد الامرين** `/musicplayer on` **and** `/musicplayer off`"
        )


@Client.on_callback_query(filters.regex(pattern=r"^(playlist)$"))
async def p_cb(b, cb):
    global que    
    que.get(cb.message.chat.id)
    type_ = cb.matches[0].group(1)
    cb.message.chat.id
    cb.message.chat
    cb.message.reply_markup.inline_keyboard[1][0].callback_data
    if type_ == "playlist":
        queue = que.get(cb.message.chat.id)
        if not queue:
            await cb.message.edit("❌ **لا توجد موسيقى قيد التشغيل حاليًا**")
        temp = []
        for t in queue:
            temp.append(t)
        now_playing = temp[0][0]
        by = temp[0][1].mention(style="md")
        msg = "🎉 **now playing** on {}".format(cb.message.chat.title)
        msg += "\n\n• " + now_playing
        msg += "\n• Req by " + by
        temp.pop(0)
        if temp:
            msg += "\n\n"
            msg += "**Queued Song**"
            for song in temp:
                name = song[0]
                usr = song[1].mention(style="md")
                msg += f"\n• {name}"
                msg += f"\n• Req by {usr}\n"
        await cb.message.edit(msg)      


@Client.on_callback_query(
    filters.regex(pattern=r"^(play|pause|skip|leave|puse|resume|menu|cls)$")
)
@cb_admin_check
async def m_cb(b, cb):
    global que   
    if (
        cb.message.chat.title.startswith("Channel Music : ")
        and chat.title[14:].isnumeric()
    ):
        chet_id = int(chat.title[13:])
    else:
        chet_id = cb.message.chat.id
    qeue = que.get(chet_id)
    type_ = cb.matches[0].group(1)
    cb.message.chat.id
    m_chat = cb.message.chat

    the_data = cb.message.reply_markup.inline_keyboard[1][0].callback_data
    if type_ == "pause":
        if (
            chet_id not in callsmusic.pytgcalls.active_calls
                ) or (
                    callsmusic.pytgcalls.active_calls[chet_id] == "paused"
                ):
            await cb.answer("المساعد غير متصل بالمحادثة الصوتية !", show_alert=True)
        else:
            callsmusic.pytgcalls.pause_stream(chet_id)
            
            await cb.answer("متوقف مؤقتا!")
            await cb.message.edit(updated_stats(m_chat, qeue), reply_markup=r_ply("play"))
                
    elif type_ == "play":       
        if (
            chet_id not in callsmusic.pytgcalls.active_calls
            ) or (
                callsmusic.pytgcalls.active_calls[chet_id] == "playing"
            ):
                await cb.answer("المساعد غير متصل بالمحادثة الصوتية !", show_alert=True)
        else:
            callsmusic.pytgcalls.resume_stream(chet_id)
            await cb.answer("متوقف مؤقتا!")
            await cb.message.edit(updated_stats(m_chat, qeue), reply_markup=r_ply("pause"))

    elif type_ == "playlist":
        queue = que.get(cb.message.chat.id)
        if not queue:   
            await cb.message.edit("لا شيء في التدفق !")
        temp = []
        for t in queue:
            temp.append(t)
        now_playing = temp[0][0]
        by = temp[0][1].mention(style="md")
        msg = "**Now playing** in {}".format(cb.message.chat.title)
        msg += "\n• "+ now_playing
        msg += "\n• Req by "+by
        temp.pop(0)
        if temp:
             msg += "\n\n"
             msg += "**Queued Song**"
             for song in temp:
                 name = song[0]
                 usr = song[1].mention(style="md")
                 msg += f"\n• {name}"
                 msg += f"\n• Req by {usr}\n"
        await cb.message.edit(msg)      
                      
    elif type_ == "resume":     
        if (
            chet_id not in callsmusic.pytgcalls.active_calls
            ) or (
                callsmusic.pytgcalls.active_calls[chet_id] == "playing"
            ):
                await cb.answer("الدردشة الصوتية ليست متصلة أو قيد التشغيل بالفعل", show_alert=True)
        else:
            callsmusic.pytgcalls.resume_stream(chet_id)
            await cb.answer("استئناف الموسيقى!")
     
    elif type_ == "puse":         
        if (
            chet_id not in callsmusic.pytgcalls.active_calls
                ) or (
                    callsmusic.pytgcalls.active_calls[chet_id] == "paused"
                ):
            await cb.answer("الدردشة الصوتية غير متصلة أو متوقفة مؤقتًا بالفعل", show_alert=True)
        else:
            callsmusic.pytgcalls.pause_stream(chet_id)
            
            await cb.answer("الاغاني موقفه!")

    elif type_ == "cls":          
        await cb.answer("قائمة مغلقة")
        await cb.message.delete()       

    elif type_ == "menu":  
        stats = updated_stats(cb.message.chat, qeue)  
        await cb.answer("تم فتح القائمه")
        marr = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⏹", "ترك"),
                    InlineKeyboardButton("⏸", "توقف"),
                    InlineKeyboardButton("▶️", "تشغيل"),
                    InlineKeyboardButton("⏭", "تخطي")
                
                ],
                [
                    InlineKeyboardButton("حفظ في قائمه التشغيل", "playlist"),
                
                ],
                [       
                    InlineKeyboardButton("الغاء", "cls")
                ]        
            ]
        )
        await cb.message.edit(stats, reply_markup=marr)

    elif type_ == "skip":        
        if qeue:
            qeue.pop(0)
        if chet_id not in callsmusic.pytgcalls.active_calls:
            await cb.answer("assistant is not connected to voice chat !", show_alert=True)
        else:
            callsmusic.queues.task_done(chet_id)

            if callsmusic.queues.is_empty(chet_id):
                callsmusic.pytgcalls.leave_group_call(chet_id)

                await cb.message.edit("•لا مزيد من قائمة التشغيل \ n • مغادرة الدردشة الصوتية")
            else:
                callsmusic.pytgcalls.change_stream(
                    chet_id, callsmusic.queues.get(chet_id)["file"]
                )
                await cb.answer("skipped")
                await cb.message.edit((m_chat, qeue), reply_markup=r_ply(the_data))
                await cb.message.reply_text(
                    f"⫸ skipped track\n⫸ now playing : **{qeue[0][0]}**"
                )

    elif type_ == "leave":
        if chet_id in callsmusic.pytgcalls.active_calls:
            try:
                callsmusic.queues.clear(chet_id)
            except QueueEmpty:
                pass

            callsmusic.pytgcalls.leave_group_call(chet_id)
            await cb.message.edit("✅ انتهى تشغيل الموسيقى")
        else:
            await cb.answer("المساعد غير متصل بالمحادثة الصوتية !", show_alert=True)


@Client.on_message(command(["play", f"play@{BOT_USERNAME}"]) & other_filters)
async def play(_, message: Message):
    global que
    global useer
    if message.chat.id in DISABLED_GROUPS:
        return    
    lel = await message.reply("** جاري التحميل ...🎉 **")
    administrators = await get_administrators(message.chat)
    chid = message.chat.id
    try:
        user = await USER.get_me()
    except:
        user.first_name = "music assistant"
    usar = user
    wew = usar.id
    try:
        # chatdetails = await USER.get_chat(chid)
        await _.get_chat_member(chid, wew)
    except:
        for administrator in administrators:
            if administrator == message.from_user.id:
                if message.chat.title.startswith("channel music "):
                    await lel.edit(
                        f"<b> please add the userbot to your channel first.</b>",
                    )
                    pass
                try:
                    invitelink = await _.export_chat_invite_link(chid)
                except:
                   await lel.edit(
                        "<b> 🦹🏻 لاستخدامي ، يجب أن أكون مسؤولاً مع الأذونات: \ n \ n »_🍥_ حذف الرسائل __ \ n» 🗼 __ حظر المستخدمين __ \ n »__ 🎐مستخدمو AdAd __ \ n» __ 🎉__إدارة الدردشة الصوتية __ \ n \ n * * ثم اكتب / أعد التحميل </ b>",
                    )
                    
                try:
                    await USER.join_chat(invitelink)
                    await USER.send_message(
                        message.chat.id, "🦹🏻: لقد انضممت إلى هذه المجموعة لتشغيل الموسيقى على الدردشة الصوتية"
                    )
                    await lel.edit(
                        f"✅ ** انضم userbot بنجاح لهذه المجموعة **",
                    )
                except UserAlreadyParticipant:
                    pass
                except Exception:
                    # print(e)
                    await lel.edit(
                        f"<b> Flood Wait Error  \n\لا يمكن لـ الحساب المساعد الانضمام إلى هذه المجموعة بسبب العديد من طلبات الانضمام إلى userbot."
                       +f"\n\nor add @{ASSISTANT_NAME} to this group manually then try again.</b>",
                    )
    try:
        await USER.get_chat(chid)
    except:
        await lel.edit(
            f"» **تم حظر userbot في هذه المجموعة !**\n\n**اطلب من المشرف إلغاء الحظر @{ASSISTANT_NAME} وإضافته مرة أخرى إلى هذه المجموعة يدويًا."
        )
        return
    text_links = None
    if message.reply_to_message:
        if message.reply_to_message.audio or message.reply_to_message.voice:
            pass
        entities = []
        toxt = message.reply_to_message.text or message.reply_to_message.caption
        if message.reply_to_message.entities:
            entities = message.reply_to_message.entities + entities
        elif message.reply_to_message.caption_entities:
            entities = message.reply_to_message.entities + entities
        urls = [entity for entity in entities if entity.type == 'url']
        text_links = [
            entity for entity in entities if entity.type == 'text_link'
        ]
    else:
        urls = None
    if text_links:
        urls = True
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    rpk = "[" + user_name + "](tg://user?id=" + str(user_id) + ")"
    audio = (
        (message.reply_to_message.audio or message.reply_to_message.voice)
        if message.reply_to_message
        else None
    )
    if audio:
        if round(audio.duration / 60) > DURATION_LIMIT:
            raise DurationLimitError(
                f"❌ *الموسيقى مع مدة أطول من** `{DURATION_LIMIT}` **دقائق ، لا يمكن  التشغيل !**"
            )
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("القائمه", callback_data="menu"),
                    InlineKeyboardButton("الغاء", callback_data="cls"),
                ],[
                    InlineKeyboardButton("القناه", url=f"https://t.me/{UPDATES_CHANNEL}")
                ],
            ]
        )
        file_name = get_file_name(audio)
        title = file_name
        thumb_name = "https://telegra.ph/file/25118a5429201b7742986.jpg"
        thumbnail = thumb_name
        duration = round(audio.duration / 60)
        views = "Locally added"
        requested_by = message.from_user.first_name
        await generate_cover(title, thumbnail)
        file_path = await converter.convert(
            (await message.reply_to_message.download(file_name))
            if not path.isfile(path.join("downloads", file_name))
            else file_name
        )
    elif urls:
        query = toxt
        await lel.edit("**جاري التحميل ...🎉**")
        ydl_opts = {"format": "bestaudio[ext=m4a]"}
        try:
            results = YoutubeSearch(query, max_results=1).to_dict()
            url = f"https://youtube.com{results[0]['url_suffix']}"
            # print(results)
            title = results[0]["title"][:60]
            thumbnail = results[0]["thumbnails"][0]
            thumb_name = f"thumb-{title}-hama.jpg"
            thumb = requests.get(thumbnail, allow_redirects=True)
            open(thumb_name, "wb").write(thumb.content)
            duration = results[0]["duration"]
            results[0]["url_suffix"]
            views = results[0]["views"]
        except Exception as e:
            await lel.edit(
                "🎉 **تعذر العثور على الأغنية التي طلبتها ** \ n \ n »** يرجى تقديم اسم الأغنية الصحيح أو تضمين اسم الفنان أيضًا**"
            )
            print(str(e))
            return
        patch-8
        dlurl=url
        dlurl = dlurl.replace("youtube","youtubepp")

        dlurl = url
        dlurl=dlurl.replace("youtube","youtubepp")
        main
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("القائمه", callback_data="menu"),
                    InlineKeyboardButton("الغاء", callback_data="cls"),
                ],[
                    InlineKeyboardButton("القناه", url=f"https://t.me/{UPDATES_CHANNEL}")
                ],
            ]
        )
        requested_by = message.from_user.first_name
        await generate_cover(title, thumbnail)
        file_path = await converter.convert(youtube.download(url))        
    else:
        query = ""
        for i in message.command[1:]:
            query += " " + str(i)
        print(query)
        ydl_opts = {"format": "bestaudio[ext=m4a]"}
        
        try:
          results = YoutubeSearch(query, max_results=5).to_dict()
        except:
          await lel.edit("🍥 **لم يتم اكتشاف اسم الأغنية ** \ n \ n »** يرجى تقديم اسم الأغنية التي تريد تشغيلها**")
        # veez project
        try:
            toxxt = "\n"
            j = 0
            user = user_name
            emojilist = ["« 1 »","« 2 »","« 3 »","« 4 »","« 5 »"]
            while j < 5:
                toxxt += f"{emojilist[j]} [{results[j]['title'][:25]}...](https://youtube.com{results[j]['url_suffix']})\n"
                toxxt += f"  VOICE TIme ➧ :** - {results[j]['duration']}\n"
                toxxt += f"  JOIN ➧ : @NiNJa_SuPPoORT\n ››››››››››››››››››››››››››\n"
                j += 1            
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("« 1 »", callback_data=f'plll 0|{query}|{user_id}'),
                        InlineKeyboardButton("« 2 »", callback_data=f'plll 1|{query}|{user_id}'),
                        InlineKeyboardButton("« 3 »", callback_data=f'plll 2|{query}|{user_id}'),
                    ],
                    [
                        InlineKeyboardButton("« 4 »", callback_data=f'plll 3|{query}|{user_id}'),
                        InlineKeyboardButton("« 5 »", callback_data=f'plll 4|{query}|{user_id}'),
                    ],
                    [InlineKeyboardButton(text="الغاء", callback_data="cls")],
                ]
            )
            await message.reply_photo(
                photo=f"{THUMB_IMG}",
                caption=toxxt,
                reply_markup=keyboard
            )

            await lel.delete()
            # hama project
            return
            # hama project
        except:
            await lel.edit("__no more results to choose, starting to playing...__")
                        
            # print(results)
            try:
                url = f"https://youtube.com{results[0]['url_suffix']}"
                title = results[0]["title"][:60]
                thumbnail = results[0]["thumbnails"][0]
                thumb_name = f"thumb-{title}-hama.jpg"
                thumb = requests.get(thumbnail, allow_redirects=True)
                open(thumb_name, "wb").write(thumb.content)
                duration = results[0]["duration"]
                results[0]["url_suffix"]
                views = results[0]["views"]
            except Exception as e:
                await lel.edit(
                    "🎉 **تعذر العثور على الأغنية التي طلبتها ** \ n \ n »** يرجى تقديم اسم الأغنية الصحيح أو تضمين اسم الفنان أيضًا**"
                )
                print(str(e))
                return
            dlurl=url
            dlurl=dlurl.replace("youtube","youtubepp")
            keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("قائمه التشغيل ", callback_data="menu"),
                    InlineKeyboardButton("الغاء", callback_data="cls"),
                ],[
                    InlineKeyboardButton("القناه", url=f"https://t.me/{UPDATES_CHANNEL}")
                ],
            ]
            )
            requested_by = message.from_user.first_name
            await generate_cover(title, thumbnail)
            file_path = await converter.convert(youtube.download(url))   
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.pytgcalls.active_calls:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await message.reply_photo(
            photo="final.png",
            caption=f"🧸 **Track added to the queue**\n\n🧸 **name :** [{title[:35]}]({url})\n⏱ **Duration:** `{duration}`\n🔮 **wanted by me :** {message.from_user.mention}\n" \
                   +f"🔢 **At Position:** » `{position}` «",
            reply_markup=keyboard
        )
    else:
        chat_id = get_chat_id(message.chat)
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        try:
            callsmusic.pytgcalls.join_group_call(chat_id, file_path)
        except:
            await lel.edit("🎉 ** لم يتم العثور على الدردشة الصوتية الرجاء تشغيل الدردشة الصوتية أولاً")
            return
        await message.reply_photo(
            photo="final.png",
            caption=f"🧸 **name :** [{title[:35]}]({url})\n⏱ **Duration:** `{duration}`\n🔉 **Status:** `Playing`\n" \
                   +f"🔮 **wanted by me :** {message.from_user.mention}",
            reply_markup=keyboard
        )
        os.remove("final.png")
        return await lel.delete()


@Client.on_callback_query(filters.regex(pattern=r"plll"))
async def lol_cb(b, cb):
    global que
    cbd = cb.data.strip()
    chat_id = cb.message.chat.id
    typed_ = cbd.split(None, 1)[1]
    try:
        x, query, useer_id = typed_.split("|")      
    except:
        await cb.message.edit("🎉  ** تعذر العثور على الأغنية التي طلبتها  يرجى تقديم اسم الأغنية الصحيح أو تضمين اسم الفنان أيضًا**")
        return
    useer_id = int(useer_id)
    if cb.from_user.id != useer_id:
        await cb.answer("🦹🏻 آسف ، هذا ليس لك !", show_alert=True)
        return
    #await cb.message.edit("🔁 **processing...**")
    x = int(x)
    try:
        useer_name = cb.message.reply_to_message.from_user.first_name
    except:
        useer_name = cb.message.from_user.first_name
    results = YoutubeSearch(query, max_results=5).to_dict()
    resultss = results[x]["url_suffix"]
    title = results[x]["title"][:60]
    thumbnail = results[x]["thumbnails"][0]
    duration = results[x]["duration"]
    views = results[x]["views"]
    url = f"https://www.youtube.com{resultss}"
    try:    
        secmul, dur, dur_arr = 1, 0, duration.split(":")
        for i in range(len(dur_arr)-1, -1, -1):
            dur += (int(dur_arr[i]) * secmul)
            secmul *= 60
        if (dur / 60) > DURATION_LIMIT:
             await cb.message.edit(f"❌ *الموسيقى التي تزيد مدتها عن ** `{DURATION_LIMIT}` ** دقيقة ، يتعذر تشغيلها !**")
             return
    except:
        pass
    try:
        thumb_name = f"thumb-{title}-hama.jpg"
        thumb = requests.get(thumbnail, allow_redirects=True)
        open(thumb_name, "wb").write(thumb.content)
    except Exception as e:
        print(e)
        return
    dlurl = url
    dlurl = dlurl.replace("youtube", "youtubepp")
    keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("قائمه التشغيل  ", callback_data="menu"),
                    InlineKeyboardButton("الغاء", callback_data="cls"),
                ],[
                    InlineKeyboardButton("القناه", url=f"https://t.me/{UPDATES_CHANNEL}")
                ],
            ]
    )
    requested_by = useer_name
    await generate_cover(title, thumbnail)
    file_path = await converter.convert(youtube.download(url))
    if chat_id in callsmusic.pytgcalls.active_calls:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        try:
            r_by = cb.message.reply_to_message.from_user
        except:
            r_by = cb.message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await cb.message.delete()
        await b.send_photo(
        chat_id,
        photo="final.png",
        caption=f"🚪 **Track added to the queue**\n\n🧸 **name :** [{title[:35]}]({url})\n⏱ **Duration:** `{duration}`\n🔮 **wanted by me :** {r_by.mention}\n" \
               +f"🔢 **At Position:** » `{position}` «",
        reply_markup=keyboard,
        )
    else:
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        try:
            r_by = cb.message.reply_to_message.from_user
        except:
            r_by = cb.message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        callsmusic.pytgcalls.join_group_call(chat_id, file_path)
        await cb.message.delete()
        await b.send_photo(
        chat_id,
        photo="final.png",
        caption=f"🧸 **name :** [{title[:35]}]({url})\n⏱ **Duration :** `{duration}`\n🔉 **Status :** `Playing`\n" \
               +f"🔮 **wanted by me :** {r_by.mention}",
        reply_markup=keyboard,
        )
    if path.exists("final.png"):
        os.remove("final.png")


@Client.on_message(command(["ytp", f"ytp@{BOT_USERNAME}"]) & other_filters)
async def ytplay(_, message: Message):
    global que
    if message.chat.id in DISABLED_GROUPS:
        return
    lel = await message.reply("**جارس التحميل...🎉**")
    administrators = await get_administrators(message.chat)
    chid = message.chat.id

    try:
        user = await USER.get_me()
    except:
        user.first_name = "music assistant"
    usar = user
    wew = usar.id
    try:
        # chatdetails = await USER.get_chat(chid)
        await _.get_chat_member(chid, wew)
    except:
        for administrator in administrators:
            if administrator == message.from_user.id:
                if message.chat.title.startswith("Channel Music: "):
                    await lel.edit(
                        f"🎉 ** يرجى إضافة Userbot إلى قناتك أولاً**",
                    )
                try:
                    invitelink = await _.export_chat_invite_link(chid)
                except:
                    await lel.edit(
                        "🎉 ** لاستخدامي ، يجب أن أكون مسؤولاً مع الأذونات: \ n \ n »❌ __ حذف الرسائل __ \ n» 🍥 __ حظر المستخدمين __ \ n »🦹🏻 __إضافة مستخدمين __ \ n» 🗼 __إدارة الدردشة الصوتية __ \ n \ n ** بعد ذلك اكتب / إعادة التحميل ****",
                    )
                    return

                try:
                    await USER.join_chat(invitelink)
                    await USER.send_message(
                        message.chat.id, "🦹🏻: لقد انضممت إلى هذه المجموعة لتشغيل الموسيقى في الدردشة الصوتية"
                    )
                    await lel.edit(
                        f"✅ ** انضم userbot بنجاح إلى هذه المجموعة.**",
                    )

                except UserAlreadyParticipant:
                    pass
                except Exception:
                    # print(e)
                    await lel.edit(
                        f"🎉 **Flood Wait Error** 🎉 \n\n**{user.first_name} can't join this group due to many join requests for userbot.**"
                        f"\n\n**or add @{ASSISTANT_NAME} to this group manually then try again.**",
                    )
    try:
        await USER.get_chat(chid)
    except:
        await lel.edit(
            f"🎉 ** تم حظر userbot في هذه المجموعة! اطلب من المشرف إلغاء حظر @ {ASSISTANT_NAME} وأضف إلى هذه المجموعة مرة أخرى يدويًا.**"
        )
        return
    
    message.from_user.id
    message.from_user.first_name

    query = ""
    for i in message.command[1:]:
        query += " " + str(i)
    print(query)
    await lel.edit("♻️ ** الاتصال بـ vcg...**")
    ydl_opts = {"format": "bestaudio/best"}
    try:
        results = YoutubeSearch(query, max_results=1).to_dict()
        url = f"https://youtube.com{results[0]['url_suffix']}"
        # print(results)
        title = results[0]["title"][:60]
        thumbnail = results[0]["thumbnails"][0]
        thumb_name = f"thumb-{title}-hama.jpg"
        thumb = requests.get(thumbnail, allow_redirects=True)
        open(thumb_name, "wb").write(thumb.content)
        duration = results[0]["duration"]
        results[0]["url_suffix"]
        views = results[0]["views"]

    except Exception as e:
        await lel.edit("🎉 ** تعذر العثور على الأغنية التي طلبتها  يرجى تقديم اسم الأغنية الصحيح أو تضمين اسم الفنان أيضًا **")
        print(str(e))
        return
    try:
        secmul, dur, dur_arr = 1, 0, duration.split(":")
        for i in range(len(dur_arr) - 1, -1, -1):
            dur += int(dur_arr[i]) * secmul
            secmul *= 60
        if (dur / 60) > DURATION_LIMIT:
            await lel.edit(
                f"❌ ** موسيقى بمدة تزيد عن** `{DURATION_LIMIT}` **دقائق ، لا يمكن اللعب !**"
            )
            return
    except:
        pass
    dlurl = url
    dlurl = dlurl.replace("youtube", "youtubepp")
    keyboard = InlineKeyboardMarkup(
            [   
                [
                    InlineKeyboardButton("قائمه التشغيل ", callback_data="menu"),
                    InlineKeyboardButton("الغاء", callback_data="cls"),

                ],
                [
                    InlineKeyboardButton("- ♫︎༆𝙈𝙐𝙎𝙄𝘾_𝙀𝙇𝙆𝙀𝘼𝙏𝙄𝘽༆♫︎ ›", url=f"https://t.me/{UPDATES_CHANNEL}"),
                    InlineKeyboardButton(" - 𝘽𝘼𝙍_𝙀𝙇𝙆𝙀𝘼𝙏𝙄𝘽 ›", url=f"https://t.me/{GROUP_SUPPORT}")
                ]                             
            ]
        )
    requested_by = message.from_user.first_name
    await generate_cover(title, thumbnail)
    file_path = await converter.convert(youtube.download(url))
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.pytgcalls.active_calls:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await message.reply_photo(
            photo="final.png",
       caption=f"🚪 **Track added to the queue**\n\n🧸 **name :** [{title[:35]}]({url})\n⏱ **Duration:** `{duration}`\n🔮 **wanted by me :** {r_by.mention}\n" \
               +f"🔢 **At Position:** » `{position}` «",
        reply_markup=keyboard
        )
    else:
        chat_id = get_chat_id(message.chat)
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        try:
            callsmusic.pytgcalls.join_group_call(chat_id, file_path)
        except:
            await lel.edit("🎉 **voice chat not found**\n\n» please turn on the voice chat first")
            return
        await message.reply_photo(
            photo="final.png",
       caption=f"🧸 **name :** [{title[:35]}]({url})\n⏱ **Duration :** `{duration}`\n🔉 **Status :** `Playing`\n" \
               +f"🔮 **wanted by me :** {r_by.mention}",
        reply_markup=keyboard,
        )
        os.remove("final.png")
        return await lel.delete()
