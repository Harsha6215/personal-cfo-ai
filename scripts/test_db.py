"""Quick test: can we connect to PostgreSQL from Python?"""
import asyncio
import asyncpg

async def main():
    try:
        conn = await asyncpg.connect(
            host="127.0.0.1",
            port=5432,
            user="postgres",
            password="postgres",
            database="personal_cfo",
        )
        val = await conn.fetchval("SELECT 1")
        print(f"SUCCESS: connected, SELECT 1 = {val}")
        await conn.close()
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")

asyncio.run(main())
