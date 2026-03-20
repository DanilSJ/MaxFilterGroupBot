import httpx
from core.config import settings


async def get_group(group_id: int):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{settings.API_URL}/group/{group_id}")
        return r.json()