import httpx
from core.config import settings


async def get_group(group_id: int):
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{settings.API_URL}/group/max/{group_id}/")
            return r
        except Exception as e:
            print(e)


async def create_account(max_id: int):
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(f"{settings.API_URL}/user/max/", json={"max_id": max_id})
            return r
        except Exception as e:
            print(e)