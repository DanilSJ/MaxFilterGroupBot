import os
from dotenv import load_dotenv
from maxapi import Bot
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    TOKEN: str = os.getenv("TOKEN")


settings = Settings()
bot = Bot(token=settings.TOKEN)