import asyncio
from maxapi import Dispatcher
from core.config import bot
from app.start.headers import router as start_router, auto_delete_messages

dp = Dispatcher()

async def main():
    dp.include_routers(start_router)

    await asyncio.gather(
        dp.start_polling(bot),
        # auto_delete_messages()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")