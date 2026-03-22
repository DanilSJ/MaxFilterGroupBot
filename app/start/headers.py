import re
import string
from maxapi import Router, F
from maxapi.types import MessageCreated, Command
from app.api.api import get_group

router = Router()

go = False


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

async def has_link(text):
    """
    Проверяет наличие ссылок с разными протоколами
    """
    url_pattern = r'(?:https?://|ftp://|www\.)[^\s<>"\'{}|\\^`\[\]]+(?:/[^\s<>"\'{}|\\^`\[\]]*)?'
    return bool(re.search(url_pattern, text, re.IGNORECASE))

@router.message_created(Command('start'))
async def start(event: MessageCreated):
    await event.message.answer("Привет, чтобы настроить зайди в miniapp")


@router.message_created()
async def echo(event: MessageCreated):
    group_id = 1
    r = await get_group(group_id)

    if r.status_code != 200:
        return False
    r = r.json()


    if r["bad_words"]:
        check = await check_words_in_text(event.message.body.text, r["bad_words_text"])
        if check:
            await event.message.delete()
            if r["message_delete"]:
                return await event.message.answer(r["message_delete_text"])

    if r["repost"]:
        if event.message.link:
            await event.message.delete()
            if r["message_delete"]:
                return await event.message.answer(r["message_delete_text"])

    if r["stop_word"]:
        check = await check_words_in_text(event.message.body.text, r["stop_word_text"])
        if check:
            print("tru")
            await event.message.delete()

            if r["message_delete"]:
                return await event.message.answer(r["message_delete_text"])

    if r["link"]:
        check = await has_link(event.message.body.text)
        if check:
            await event.message.delete()
            if r["message_delete"]:
                return await event.message.answer(r["message_delete_text"])

    if r["message_delete"]:
        await event.message.delete()
        return await event.message.answer(r["message_delete_text"])

    return True
