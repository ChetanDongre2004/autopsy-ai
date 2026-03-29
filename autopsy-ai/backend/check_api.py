import httpx
import asyncio

async def run():
    async with httpx.AsyncClient() as client:
        resp = await client.post('http://localhost:8000/api/review/', json={'code':'print)hello"','language':'python'}, timeout=10.0)
        print("Response", resp.text)

asyncio.run(run())
