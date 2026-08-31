import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/stockpilot",
)

pool = None


async def connect_db() -> None:
    global pool
    if pool is None:
        print(f"Connecting to {DATABASE_URL}")
        pool = await asyncpg.connect(DATABASE_URL)
        print("Connected to database")


async def close_db() -> None:
    global pool
    if pool is not None:
        await pool.close()
        pool = None
        print("Closed connection")


def get_pool():
    return pool


async def insert_or_update_product(product: dict) -> dict:
    return await get_pool().fetchrow(
        """
        INSERT INTO products (sku, name, unit, current_quantity, minimum_quantity, is_active)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (sku) DO UPDATE
        SET
            name = EXCLUDED.name,
            unit = EXCLUDED.unit,
            current_quantity = EXCLUDED.current_quantity,
            minimum_quantity = EXCLUDED.minimum_quantity,
            is_active = EXCLUDED.is_active,
            updated_at = NOW()
        RETURNING *;
        """,
        product["sku"],
        product["name"],
        product["unit"],
        product["current_quantity"],
        product.get("minimum_quantity", 5),
        product.get("is_active", True),
    )


async def main():
    await connect_db()
    
    sample_products = [
        {
            "sku": "LAPTOP-DELL-XPS13",
            "name": "Laptop Dell XPS 13 9315",
            "unit": "chiếc",
            "current_quantity": 15,
            "minimum_quantity": 5,
            "is_active": True,
        },
        {
            "sku": "MOUSE-LOGI-MX3S",
            "name": "Chuột không dây Logitech MX Master 3S",
            "unit": "chiếc",
            "current_quantity": 40,
            "minimum_quantity": 10,
            "is_active": True,
        },
        {
            "sku": "KEYBOARD-KEYCHRON-K2",
            "name": "Bàn phím cơ Keychron K2 V2",
            "unit": "chiếc",
            "current_quantity": 25,
            "minimum_quantity": 8,
            "is_active": True,
        },
        {
            "sku": "MONITOR-DELL-U2723QE",
            "name": "Màn hình Dell UltraSharp 27 4K",
            "unit": "chiếc",
            "current_quantity": 8,
            "minimum_quantity": 3,
            "is_active": True,
        },
        {
            "sku": "CABLE-TYPEC-100W",
            "name": "Cáp sạc Type-C 100W 2m",
            "unit": "sợi",
            "current_quantity": 120,
            "minimum_quantity": 30,
            "is_active": True,
        },
        {
            "sku": "HEADPHONE-SONY-XM5",
            "name": "Tai nghe chống ồn Sony WH-1000XM5",
            "unit": "chiếc",
            "current_quantity": 4,
            "minimum_quantity": 6,
            "is_active": True,
        },
    ]

    try:
        results = [await insert_or_update_product(p) for p in sample_products]
        print(f"\n✅ Đã nạp / cập nhật thành công {len(results)} sản phẩm vào Database:")
        for r in results:
            print(f"- [{r['sku']}] {r['name']}: {r['current_quantity']} {r['unit']} (Tối thiểu: {r['minimum_quantity']})")
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())