import string
import time
from maxapi import Router, F
from maxapi.types import MessageCreated, Command
from app.api.api import get_group, create_account
from maxapi.enums.parse_mode import ParseMode
from core.config import bot
import asyncio
from maxapi.context import State, StatesGroup, MemoryContext


router = Router()

bot_messages = []

group_cache = {}
CACHE_TTL = 60


class GetForm(StatesGroup):
    wait = State()

async def check_words_in_text(text, word_list):
    """
    Проверяет наличие слов из списка в тексте
    """
    if not text or not word_list:
        return False

    text_clean = text.lower().translate(str.maketrans('', '', string.punctuation))
    words_in_text = set(text_clean.split())

    if isinstance(word_list, str):
        target_words = set(word.lower().strip() for word in word_list.split() if word.strip())
    else:
        target_words = set(word.lower() for word in word_list if word)

    return bool(words_in_text & target_words)


async def has_link(event):
    try:
        if not hasattr(event, 'message') or not hasattr(event.message, 'body'):
            return False

        body = event.message.body

        if getattr(body, 'markup', None):
            for m in body.markup:
                if getattr(m, 'type', '').lower() == 'link':
                    return True

        if getattr(body, 'attachments', None):
            for att in body.attachments:
                payload = getattr(att, 'payload', None)

                if att.type == 'image':
                    continue

                if att.type == 'video':
                    continue

                if att.type == 'link':
                    return True

                if payload:
                    has_url = hasattr(payload, 'url') and payload.url

                    is_media = (
                        hasattr(payload, 'photo_id') or
                        hasattr(payload, 'duration') or
                        hasattr(payload, 'thumbnail')
                    )

                    if has_url and not is_media:
                        return True

    except Exception:
        return False

    return False

async def format_message_with_username(message_text, user):
    """
    Заменяет @username в тексте сообщения на упоминание пользователя
    """
    if not message_text or not user:
        return message_text

    display_name = user.full_name if user.full_name else f"Пользователь {user.user_id}"
    user_link = f"max://user/{user.user_id}"

    if '@username' in message_text:
        mention = f'<a href="{user_link}">{display_name}</a>'
        return message_text.replace('@username', mention)

    return message_text


async def is_chat_admin(chat_id, user_id):
    """
    Проверяет, является ли пользователь администратором чата
    """
    try:
        admins = await bot.get_list_admin_chat(chat_id)

        if hasattr(admins, 'members') and admins.members:
            for member in admins.members:
                if member.is_admin and member.user_id == user_id:
                    return True


        return False

    except Exception as e:
        print(f"Error checking admin status: {e}")
        return False


@router.message_created(Command('start'))
async def start(event: MessageCreated):
    await event.message.answer("Привет, чтобы настроить зайди в miniapp")


async def get_group_cached(group_id: int):
    """
    Получает данные группы с кэшированием
    """
    current_time = time.time()

    # Проверяем наличие данных в кэше и их актуальность
    if group_id in group_cache:
        cached_data, cached_time = group_cache[group_id]
        if current_time - cached_time < CACHE_TTL:
            return cached_data

    # Если данных нет или они устарели, делаем запрос
    try:
        r = await get_group(group_id)
        if r.status_code == 200:
            data = r.json()
            group_cache[group_id] = (data, current_time)
            return data
        else:
            return None
    except Exception as e:
        print(f"Error fetching group {group_id}: {e}")
        return None


async def invalidate_group_cache(group_id: int):
    """
    Очищает кэш для конкретной группы (можно вызывать при обновлении настроек)
    """
    if group_id in group_cache:
        del group_cache[group_id]

def is_blocked(user_id: int, block_users: list[dict]) -> bool:
    return any(u["max_id"] == user_id for u in block_users)

@router.message_created(Command('get'))
async def get_cmd(event: MessageCreated, context: MemoryContext):
    await context.set_state(GetForm.wait)

    await event.message.answer("Отправь любое сообщение")

@router.message_created(GetForm.wait)
async def get_any_message(event: MessageCreated, context: MemoryContext):
    await context.set_state(None)
    await event.message.answer(f"ID: {event.message.link.sender.user_id} UserName: {event.message.link.sender.username}\nName: {event.message.link.sender.first_name} {event.message.link.sender.last_name}")

@router.message_created()
async def echo(event: MessageCreated):
    group_id = abs(event.chat.chat_id)
    user_id = event.from_user.user_id
    print(user_id)
    await create_account(user_id)

    r = await get_group_cached(group_id)

    if not r:
        return False

    if is_blocked(user_id, r["grid"].get("block_users", [])):
        return await event.message.delete()

    try:
        user = event.message.sender

        # Быстрая проверка на админа (тоже можно закэшировать)
        is_admin_user = await is_chat_admin(event.chat.chat_id, user.user_id)
        if is_admin_user:
            return True

        # Проверки с ранним выходом для оптимизации
        text = event.message.body.text if hasattr(event.message.body, 'text') else ""

        # Проверка плохих слов
        if r.get("bad_words", False) and r.get("bad_words_text"):
            if await check_words_in_text(text, r["bad_words_text"]):
                await event.message.delete()
                if r.get("message_delete", False):
                    message_text = await format_message_with_username(
                        r.get("message_bad_text", ""), user
                    )
                    if message_text:
                        msg = await event.message.answer(
                            message_text,
                            parse_mode=ParseMode.HTML
                        )
                        bot_messages.append(msg.message.body.mid)
                        return msg

        # Проверка репостов
        if r.get("repost", False) and event.message.link:
            await event.message.delete()
            if r.get("message_delete", False):
                message_text = await format_message_with_username(
                    r.get("message_repost_text", ""), user
                )
                if message_text:
                    msg = await event.message.answer(
                        message_text,
                        parse_mode=ParseMode.HTML
                    )
                    bot_messages.append(msg.message.body.mid)
                    return msg

        # Проверка стоп-слов
        if r.get("stop_word", False) and r.get("stop_word_text"):
            if await check_words_in_text(text, r["stop_word_text"]):
                await event.message.delete()
                if r.get("message_delete", False):
                    message_text = await format_message_with_username(
                        r.get("message_stop_word_text", ""), user
                    )
                    if message_text:
                        msg = await event.message.answer(
                            message_text,
                            parse_mode=ParseMode.HTML
                        )
                        bot_messages.append(msg.message.body.mid)
                        return msg

        # Проверка ссылок
        if r.get("link", False):
            if await has_link(event):
                await event.message.delete()
                if r.get("message_delete", False):
                    message_text = await format_message_with_username(
                        r.get("message_link_text", ""), user
                    )
                    if message_text:
                        msg = await event.message.answer(
                            message_text,
                            parse_mode=ParseMode.HTML
                        )
                        print(msg.message.body.mid)
                        bot_messages.append(msg.message.body.mid)
                        return msg

    except Exception as e:
        print(f"Error processing message: {e}")

    return True

async def auto_delete_messages():
    global bot_messages

    while True:
        await asyncio.sleep(120)

        messages_to_delete = bot_messages
        bot_messages = []

        for mid in messages_to_delete:
            try:
                print(f"Удаляю: {mid}")
                print(await bot.delete_message(mid))

            except Exception as e:
                print(f"Ошибка удаления {mid}: {e}")
