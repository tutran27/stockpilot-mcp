import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/stockpilot",
)

pool: asyncpg.Pool | None = None


# ==============================================================================
# 1. QUẢN LÝ KẾT NỐI (Connection Pool)
# ==============================================================================

async def init_db() -> None:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)


async def close_db() -> None:
    global pool
    if pool is not None:
        await pool.close()
        pool = None


def get_pool() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("Database pool chưa được khởi tạo. Hãy gọi init_db() trước.")
    return pool


# ==============================================================================
# 2. CÁC HÀM ĐỌC DỮ LIỆU (Read Operations)
# ==============================================================================

async def get_stock(product_id: str) -> dict | None:
    """Lấy thông tin tồn kho và chi tiết một sản phẩm theo ID."""
    row = await get_pool().fetchrow(
        "SELECT * FROM products WHERE id = $1;",
        product_id,
    )
    return dict(row) if row else None


async def find_products(name_or_sku: str) -> list[dict]:
    """Tìm kiếm sản phẩm theo tên hoặc mã SKU."""
    rows = await get_pool().fetch(
        """
        SELECT id, sku, name, unit, current_quantity, minimum_quantity, is_active 
        FROM products 
        WHERE (name ILIKE $1 OR sku ILIKE $1) AND is_active = TRUE
        LIMIT 10;
        """,
        f"%{name_or_sku}%",
    )
    return [dict(r) for r in rows]


async def get_list_products(limit: int = 10) -> list[dict]:
    """Lấy danh sách tất cả sản phẩm đang hoạt động."""
    rows = await get_pool().fetch(
        """
        SELECT id, sku, name, unit, current_quantity, minimum_quantity 
        FROM products 
        WHERE is_active = TRUE
        LIMIT $1;
        """,
        limit,
    )
    return [dict(r) for r in rows]


async def get_low_stock_products(limit: int = 10) -> list[dict]:
    """Lấy danh sách sản phẩm có tồn kho thấp (current_quantity <= minimum_quantity)."""
    rows = await get_pool().fetch(
        """
        SELECT id, sku, name, unit, current_quantity, minimum_quantity 
        FROM products 
        WHERE current_quantity <= minimum_quantity AND is_active = TRUE
        LIMIT $1;
        """,
        limit,
    )
    return [dict(r) for r in rows]


async def get_transactions_limit(limit: int) -> list[dict]:
    """Lấy danh sách các giao dịch xuất/nhập kho gần nhất kèm thông tin sản phẩm."""
    rows = await get_pool().fetch(
        """
        SELECT 
            t.id,
            t.product_id,
            p.sku,
            p.name AS product_name,
            t.quantity,
            t.quantity_before,
            t.quantity_after,
            t.partner,
            t.reference_notes,
            t.note,
            t.idempotency_key,
            t.created_at
        FROM stock_transactions t
        JOIN products p ON t.product_id = p.id
        ORDER BY t.created_at DESC
        LIMIT $1;
        """,
        limit,
    )
    return [dict(r) for r in rows]


# ==============================================================================
# 3. CÁC HÀM GHI DỮ LIỆU (Write Operations)
# ==============================================================================

async def add_product(sku: str, name: str, unit: str, current_quantity: int = 0, minimum_quantity: int = 5) -> dict | None:
    """Thêm sản phẩm mới vào danh mục."""
    row = await get_pool().fetchrow(
        """
        INSERT INTO products (sku, name, unit, current_quantity, minimum_quantity)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *;
        """,
        sku,
        name,
        unit,
        current_quantity,
        minimum_quantity,
    )
    return dict(row) if row else None


import uuid


async def update_stock(product_id: str, quantity_delta: int) -> None:
    """Cập nhật tăng/giảm số lượng tồn kho của một sản phẩm."""
    await get_pool().execute(
        """
        UPDATE products 
        SET current_quantity = current_quantity + $2, updated_at = NOW() 
        WHERE id = $1::uuid;
        """,
        product_id,
        quantity_delta,
    )


async def create_transaction(
    product_id: str,
    quantity: int,
    qty_before: int,
    qty_after: int,
    partner: str | None = None,
    reference_notes: str | None = None,
    note: str | None = None,
    idempotency_key: str | None = None,
) -> None:
    """Ghi nhận một bản ghi giao dịch kho."""
    key = idempotency_key.strip() if idempotency_key else ""
    if not key:
        key = str(uuid.uuid4())

    await get_pool().execute(
        """
        INSERT INTO stock_transactions (
            product_id, quantity, quantity_before, quantity_after,
            partner, reference_notes, note, idempotency_key
        )
        VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8);
        """,
        product_id,
        quantity,
        qty_before,
        qty_after,
        partner or None,
        reference_notes or None,
        note or None,
        key,
    )


async def receive_stock(
    product_id: str,
    quantity: int,
    partner: str = "",
    reference_notes: str = "",
    note: str = "",
    idempotency_key: str = "",
) -> None:
    """Nghiệp vụ nhập kho: Tăng tồn kho và tạo giao dịch."""
    product = await get_stock(product_id)
    if not product:
        raise ValueError(f"Không tìm thấy sản phẩm: {product_id}")
    if not product.get("is_active"):
        raise ValueError(f"Sản phẩm đang bị vô hiệu hóa: {product_id}")
    if quantity <= 0:
        raise ValueError(f"Số lượng nhập phải > 0 (nhận: {quantity})")

    qty_before = product.get("current_quantity", 0)
    qty_after = qty_before + quantity

    key = idempotency_key.strip() if idempotency_key else str(uuid.uuid4())

    async with get_pool().acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                UPDATE products 
                SET current_quantity = current_quantity + $2, updated_at = NOW() 
                WHERE id = $1::uuid;
                """,
                product_id,
                quantity,
            )
            await conn.execute(
                """
                INSERT INTO stock_transactions (
                    product_id, quantity, quantity_before, quantity_after,
                    partner, reference_notes, note, idempotency_key
                )
                VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8);
                """,
                product_id,
                quantity,
                qty_before,
                qty_after,
                partner or None,
                reference_notes or None,
                note or None,
                key,
            )


async def issue_stock(
    product_id: str,
    quantity: int,
    partner: str = "",
    reference_notes: str = "",
    note: str = "",
    idempotency_key: str = "",
) -> None:
    """Nghiệp vụ xuất kho: Kiểm tra số lượng, giảm tồn kho và tạo giao dịch."""
    product = await get_stock(product_id)
    if not product:
        raise ValueError(f"Không tìm thấy sản phẩm: {product_id}")
    if not product.get("is_active"):
        raise ValueError(f"Sản phẩm đang bị vô hiệu hóa: {product_id}")
    if quantity <= 0:
        raise ValueError(f"Số lượng xuất phải > 0 (nhận: {quantity})")

    qty_before = product.get("current_quantity", 0)
    if qty_before < quantity:
        raise ValueError(f"Không đủ hàng để xuất: hiện còn {qty_before}, yêu cầu {quantity}")

    qty_after = qty_before - quantity
    key = idempotency_key.strip() if idempotency_key else str(uuid.uuid4())

    async with get_pool().acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                UPDATE products 
                SET current_quantity = current_quantity + $2, updated_at = NOW() 
                WHERE id = $1::uuid;
                """,
                product_id,
                -quantity,
            )
            await conn.execute(
                """
                INSERT INTO stock_transactions (
                    product_id, quantity, quantity_before, quantity_after,
                    partner, reference_notes, note, idempotency_key
                )
                VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8);
                """,
                product_id,
                -quantity,
                qty_before,
                qty_after,
                partner or None,
                reference_notes or None,
                note or None,
                key,
            )