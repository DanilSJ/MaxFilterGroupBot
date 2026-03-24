import string
from maxapi import Router
from maxapi.types import MessageCreated, Command
from app.api.api import get_group
from maxapi.enums.parse_mode import ParseMode
from core.config import bot

router = Router()


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
    """
    Проверяет наличие ссылок в тексте с более строгими правилами
    """

    try:
        if hasattr(event, 'message') and hasattr(event.message, 'body'):
            if hasattr(event.message.body, 'markup') and event.message.body.markup:
                for markup_item in event.message.body.markup:
                    if hasattr(markup_item, 'type'):
                        if markup_item.type == 'link' or markup_item.type == 'LINK':
                            return True
                        if hasattr(markup_item.type, 'LINK') and markup_item.type.LINK:
                            return True
    except (IndexError, AttributeError, TypeError):
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


@router.message_created()
async def echo(event: MessageCreated):
    group_id = abs(event.chat.chat_id)

    r = await get_group(group_id)

    if r.status_code != 200:
        return False
    r = r.json()

    try:
        user = event.message.sender

        is_admin_user = await is_chat_admin(event.chat.chat_id, user.user_id)

        if is_admin_user:
            return True

        if r["bad_words"]:
            check = await check_words_in_text(event.message.body.text, r["bad_words_text"])
            if check:
                await event.message.delete()
                if r["message_delete"]:
                    message_text = await format_message_with_username(r["message_bad_text"], user)
                    if message_text:
                        return await event.message.answer(
                            message_text,
                            parse_mode=ParseMode.HTML
                        )

        if r["repost"]:
            if event.message.link:
                await event.message.delete()
                if r["message_delete"]:
                    message_text = await format_message_with_username(r["message_repost_text"], user)
                    if message_text:
                        return await event.message.answer(
                            message_text,
                            parse_mode=ParseMode.HTML
                        )

        if r["stop_word"]:
            check = await check_words_in_text(event.message.body.text, r["stop_word_text"])
            if check:
                await event.message.delete()
                if r["message_delete"]:
                    message_text = await format_message_with_username(r["message_stop_word_text"], user)
                    if message_text:
                        return await event.message.answer(
                            message_text,
                            parse_mode=ParseMode.HTML
                        )

        if r["link"]:
            check = await has_link(event)
            if check:
                await event.message.delete()
                if r["message_delete"]:
                    message_text = await format_message_with_username(r["message_link_text"], user)
                    if message_text:
                        return await event.message.answer(
                            message_text,
                            parse_mode=ParseMode.HTML
                        )

    except Exception as e:
        print(f"Error: {e}")
        pass

    return True