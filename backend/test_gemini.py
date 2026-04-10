import asyncio
from openai import AsyncOpenAI

async def test(model):
    client = AsyncOpenAI(
        api_key="AIzaSyBhY-Vjkwfuz-MPmY07l047ucGDA-Uyj1s",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    try:
        res = await client.chat.completions.create(model=model, messages=[{"role": "user", "content": "hi"}], max_tokens=10)
        print("Success with", model)
    except Exception as e:
        print("Failed with", model, e)

async def main():
    await test("gemini-1.5-flash")
    await test("gemini-2.5-flash")
    await test("gemini-1.5-pro")

asyncio.run(main())
