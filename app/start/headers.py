import re

from maxapi import Router, F
from maxapi.types import MessageCreated, Command
from app.api.api import get_group

router = Router()

go = False


async def check_words_in_text(text, word_list):
    words_in_text = set(text.lower().split())
    target_words = set(word.lower() for word in word_list)

    return bool(words_in_text & target_words)


async def has_link(text):
    """
    Проверяет наличие ссылок с разными протоколами
    """
    url_pattern = r'(?:https?://|ftp://|www\.)[^\s<>"\'{}|\\^`\[\]]+(?:/[^\s<>"\'{}|\\^`\[\]]*)?'

    return bool(re.search(url_pattern, text, re.IGNORECASE))

@router.message_created(Command('start'))
async def start(event: MessageCreated):
    await event.message.answer("Привет, чтобы настроить нажми кнопки приложения")

@router.message_created(F.message)
async def echo(event: MessageCreated):
    group_id = 0
    r = await get_group(group_id)

    if r["bad_words"] == "true":
        check = await check_words_in_text(event.message.body.text, r["bad_words_text"])
        if check:
            await event.message.delete()
            if r["message_delete"] == "true":
                return await event.message.answer(r["message_delete_text"])

    elif r["repost"] == "true":
        if await event.message.link:
            await event.message.delete()
            if r["message_delete"] == "true":
                return await event.message.answer(r["message_delete_text"])

    elif r["stop_word"] == "true":
        check = await check_words_in_text(event.message.body.text, r["stop_word_text"])
        if check:
            await event.message.delete()
            if r["message_delete"] == "true":
                return await event.message.answer(r["message_delete_text"])

    elif r["link"] == "true":
        check = await has_link(event.message.body.text)
        if check:
            await event.message.delete()
            if r["message_delete"] == "true":
                return await event.message.answer(r["message_delete_text"])

    elif r["message_delete"] == "true":
        await event.message.delete()
        return await event.message.answer(r["message_delete_text"])

    return True