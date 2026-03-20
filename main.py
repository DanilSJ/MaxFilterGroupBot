import asyncio
from maxapi import Dispatcher
from core.config import bot

dp = Dispatcher()

async def main():
    dp.include_routers()

    await asyncio.gather(
        dp.start_polling(bot)
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")