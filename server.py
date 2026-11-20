"""
VISHWAKARMA HARDWARE & SANITARY
Modern Full-Stack Server
Uses Python Standard Library (ThreadingHTTPServer + SQLite3)
"""
import os
import sys
import json
import sqlite3
import mimetypes
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from datetime import datetime
import random

BASE_DIR = Path(__file__).parent.resolve()
PUBLIC_DIR = BASE_DIR / "public"
DB_FILE = BASE_DIR / "store.db"

# Ensure DB is initialized
if not DB_FILE.exists():
    from init_db import init_database
    init_database()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

class StoreHTTPRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def end_headers(self):
        # Enable CORS and disable aggressive caching for development
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Admin-Pin, Authorization")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message, status=400):
        self.send_json({"error": message, "status": status}, status=status)

    def parse_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw)
        except Exception as e:
            return {}

    def is_admin_authorized(self):
        # Admin auth check: pin sent via header X-Admin-Pin or query param pin
        pin = self.headers.get("X-Admin-Pin")
        if not pin:
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            pin = qs.get("pin", [None])[0]

        if not pin:
            return False

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key='admin_pin'")
        row = c.fetchone()
        conn.close()
        expected = row["value"] if row else "0206"
        return str(pin).strip() == str(expected).strip()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        # Route web pages
        if path == "/" or path == "/index.html":
            self.path = "/index.html"
            return super().do_GET()
        elif path == "/admin" or path == "/admin.html":
            self.path = "/admin.html"
            return super().do_GET()

        # Route API
        if path.startswith("/api/"):
            return self.handle_api_get(path, qs)

        # Static assets
        return super().do_GET()

    def handle_api_get(self, path, qs):
        conn = get_db()
        c = conn.cursor()

        try:
            # 1. Store settings
            if path == "/api/settings":
                c.execute("SELECT key, value FROM settings")
                rows = c.fetchall()
                settings = {r["key"]: r["value"] for r in rows}
                # Mask admin pin unless authorized
                if not self.is_admin_authorized():
                    settings["admin_pin"] = "••••"
                return self.send_json(settings)

            # 2. Categories
            elif path == "/api/categories":
                c.execute("""
                    SELECT category, COUNT(*) as count 
                    FROM products 
                    GROUP BY category 
                    ORDER BY category ASC
                """)
                rows = c.fetchall()
                categories = [{"name": r["category"], "count": r["count"]} for r in rows]
                return self.send_json(categories)

            # 3. Products list with filters & sorting
            elif path == "/api/products":
                category = qs.get("category", [None])[0]
                search = qs.get("search", [None])[0]
                brand = qs.get("brand", [None])[0]
                stock_status = qs.get("stock", [None])[0]
                featured = qs.get("featured", [None])[0]
                sort_by = qs.get("sort", ["featured"])[0]

                query = "SELECT * FROM products WHERE 1=1"
                params = []

                if category and category.lower() != "all":
                    query += " AND category = ?"
                    params.append(category)

                if brand and brand.lower() != "all":
                    query += " AND brand = ?"
                    params.append(brand)

                if stock_status and stock_status.lower() != "all":
                    query += " AND stock_status = ?"
                    params.append(stock_status)

                if featured == "1":
                    query += " AND featured = 1"

                if search:
                    kw = f"%{search.strip()}%"
                    query += " AND (name LIKE ? OR brand LIKE ? OR category LIKE ? OR description LIKE ?)"
                    params.extend([kw, kw, kw, kw])

                # Sorting
                if sort_by == "price_asc":
                    query += " ORDER BY price ASC"
                elif sort_by == "price_desc":
                    query += " ORDER BY price DESC"
                elif sort_by == "name_asc":
                    query += " ORDER BY name ASC"
                elif sort_by == "newest":
                    query += " ORDER BY id DESC"
                else: # default featured and latest
                    query += " ORDER BY featured DESC, id DESC"

                c.execute(query, params)
                rows = c.fetchall()
                products = []
                for r in rows:
                    p = dict(r)
                    try:
                        p["specs"] = json.loads(p.get("specs") or "{}")
                    except Exception:
                        p["specs"] = {}
                    # Calculate discount percentage
                    if p["mrp"] > p["price"] and p["mrp"] > 0:
                        p["discount_pct"] = round(((p["mrp"] - p["price"]) / p["mrp"]) * 100)
                    else:
                        p["discount_pct"] = 0
                    products.append(p)
                return self.send_json(products)

            # 4. Single product by ID
            elif path.startswith("/api/products/"):
                parts = path.strip("/").split("/")
                if len(parts) == 3 and parts[2].isdigit():
                    prod_id = int(parts[2])
                    c.execute("SELECT * FROM products WHERE id = ?", (prod_id,))
                    row = c.fetchone()
                    if row:
                        p = dict(row)
                        try:
                            p["specs"] = json.loads(p.get("specs") or "{}")
                        except Exception:
                            p["specs"] = {}
                        if p["mrp"] > p["price"] and p["mrp"] > 0:
                            p["discount_pct"] = round(((p["mrp"] - p["price"]) / p["mrp"]) * 100)
                        else:
                            p["discount_pct"] = 0
                        return self.send_json(p)
                    else:
                        return self.send_error_json("Product not found", 404)

            # 5. Bookings list (Admin or public lookup with ID)
            elif path == "/api/bookings":
                status = qs.get("status", [None])[0]
                q = "SELECT * FROM bookings WHERE 1=1"
                params = []
                if status and status.lower() != "all":
                    q += " AND status = ?"
                    params.append(status)
                q += " ORDER BY created_at DESC"
                c.execute(q, params)
                rows = c.fetchall()
                bookings = []
                for r in rows:
                    b = dict(r)
                    try:
                        b["items"] = json.loads(b.get("items_json") or "[]")
                    except Exception:
                        b["items"] = []
                    bookings.append(b)
                return self.send_json(bookings)

            # 6. Single booking query by ID
            elif path.startswith("/api/bookings/"):
                booking_id = path.replace("/api/bookings/", "").strip()
                c.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
                row = c.fetchone()
                if row:
                    b = dict(row)
                    try:
                        b["items"] = json.loads(b.get("items_json") or "[]")
                    except Exception:
                        b["items"] = []
                    return self.send_json(b)
                else:
                    return self.send_error_json("Booking not found", 404)

            # 7. Dashboard Stats (Admin)
            elif path == "/api/stats":
                c.execute("SELECT COUNT(*) FROM products")
                total_products = c.fetchone()[0]

                c.execute("SELECT SUM(price * stock_count) FROM products")
                inv_val_row = c.fetchone()[0]
                total_inv_val = inv_val_row if inv_val_row else 0

                c.execute("SELECT COUNT(*) FROM products WHERE stock_status = 'out_of_stock' OR stock_count <= 2")
                low_stock = c.fetchone()[0]

                c.execute("SELECT COUNT(*) FROM bookings")
                total_bookings = c.fetchone()[0]

                c.execute("SELECT COUNT(*) FROM bookings WHERE status = 'pending'")
                pending_bookings = c.fetchone()[0]

                c.execute("SELECT SUM(estimated_total) FROM bookings WHERE status != 'cancelled'")
                booked_revenue = c.fetchone()[0] or 0

                c.execute("SELECT COUNT(DISTINCT category) FROM products")
                total_categories = c.fetchone()[0]

                stats = {
                    "total_products": total_products,
                    "total_inventory_value": round(total_inv_val, 2),
                    "low_stock_alerts": low_stock,
                    "total_bookings": total_bookings,
                    "pending_bookings": pending_bookings,
                    "booked_revenue": round(booked_revenue, 2),
                    "total_categories": total_categories
                }
                return self.send_json(stats)

            else:
                return self.send_error_json("Endpoint not found", 404)

        finally:
            conn.close()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.parse_json_body()

        conn = get_db()
        c = conn.cursor()

        try:
            # 1. Admin PIN verify
            if path == "/api/auth/verify-pin":
                pin = body.get("pin", "").strip()
                c.execute("SELECT value FROM settings WHERE key='admin_pin'")
                row = c.fetchone()
                expected = row["value"] if row else "0206"
                if pin == expected:
                    return self.send_json({"success": True, "token": f"pin-{pin}"})
                else:
                    return self.send_error_json("Invalid Admin PIN", 401)

            # 2. Create customer booking
            elif path == "/api/bookings":
                customer_name = body.get("customer_name", "").strip()
                customer_phone = body.get("customer_phone", "").strip()
                if not customer_name or not customer_phone:
                    return self.send_error_json("Customer name and phone number are required.")

                items = body.get("items", [])
                if not items:
                    return self.send_error_json("At least one product must be selected to book.")

                subtotal = 0.0
                for it in items:
                    subtotal += float(it.get("price", 0)) * int(it.get("qty", 1))

                discount_amount = float(body.get("discount_amount", 0))
                estimated_total = max(0.0, subtotal - discount_amount)

                # Generate Unique Booking ID
                random_digits = random.randint(1000, 9999)
                booking_id = f"VHS-{datetime.now().strftime('%y%m%d')}-{random_digits}"

                items_json = json.dumps(items)
                now_str = datetime.now().isoformat()

                c.execute("""
                INSERT INTO bookings 
                (id, customer_name, customer_phone, customer_email, booking_type, delivery_address, preferred_date, preferred_time, notes, items_json, subtotal, discount_amount, estimated_total, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """, (
                    booking_id,
                    customer_name,
                    customer_phone,
                    body.get("customer_email", ""),
                    body.get("booking_type", "store_pickup"),
                    body.get("delivery_address", ""),
                    body.get("preferred_date", ""),
                    body.get("preferred_time", ""),
                    body.get("notes", ""),
                    items_json,
                    subtotal,
                    discount_amount,
                    estimated_total,
                    now_str,
                    now_str
                ))
                conn.commit()

                # Get store contact info for WhatsApp redirection
                c.execute("SELECT key, value FROM settings WHERE key IN ('shop_name', 'phone', 'whatsapp')")
                settings_rows = c.fetchall()
                store_meta = {r["key"]: r["value"] for r in settings_rows}

                return self.send_json({
                    "success": True,
                    "booking_id": booking_id,
                    "customer_name": customer_name,
                    "customer_phone": customer_phone,
                    "estimated_total": estimated_total,
                    "items": items,
                    "status": "pending",
                    "store_meta": store_meta,
                    "message": "Booking submitted successfully!"
                }, status=201)

            # 3. Create Product (Admin only)
            elif path == "/api/products":
                if not self.is_admin_authorized():
                    return self.send_error_json("Unauthorized. Admin PIN required.", 401)

                name = body.get("name", "").strip()
                category = body.get("category", "General Hardware").strip()
                brand = body.get("brand", "Standard").strip()
                price = float(body.get("price", 0))
                mrp = float(body.get("mrp", price))
                stock_status = body.get("stock_status", "in_stock")
                stock_count = int(body.get("stock_count", 10))
                image_url = body.get("image_url", "").strip() or "https://images.unsplash.com/photo-1581783342308-f792dbdd27c5?auto=format&fit=crop&w=800&q=80"
                description = body.get("description", "").strip()
                specs = body.get("specs", {})
                specs_json = json.dumps(specs) if isinstance(specs, dict) else str(specs)
                featured = 1 if body.get("featured") else 0

                if not name or price <= 0:
                    return self.send_error_json("Product name and valid price are required.")

                c.execute("""
                INSERT INTO products 
                (name, category, brand, price, mrp, stock_status, stock_count, rating, reviews_count, image_url, description, specs, featured)
                VALUES (?, ?, ?, ?, ?, ?, ?, 4.9, 1, ?, ?, ?, ?)
                """, (
                    name, category, brand, price, mrp, stock_status, stock_count, image_url, description, specs_json, featured
                ))
                conn.commit()
                new_id = c.lastrowid
                return self.send_json({"success": True, "id": new_id, "message": "Product created successfully"}, status=201)

            # 4. Reset sample data (Admin only)
            elif path == "/api/reset-sample":
                if not self.is_admin_authorized():
                    return self.send_error_json("Unauthorized", 401)
                conn.close()
                from init_db import init_database
                # Re-seed
                if DB_FILE.exists():
                    os.remove(DB_FILE)
                init_database()
                return self.send_json({"success": True, "message": "Store database reset to original demo data."})

            else:
                return self.send_error_json("Endpoint not found", 404)

        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.parse_json_body()

        if not self.is_admin_authorized():
            return self.send_error_json("Unauthorized. Admin PIN required.", 401)

        conn = get_db()
        c = conn.cursor()

        try:
            # 1. Update product
            if path.startswith("/api/products/"):
                parts = path.strip("/").split("/")
                if len(parts) == 3 and parts[2].isdigit():
                    prod_id = int(parts[2])
                    name = body.get("name", "").strip()
                    category = body.get("category", "").strip()
                    brand = body.get("brand", "").strip()
                    price = float(body.get("price", 0))
                    mrp = float(body.get("mrp", price))
                    stock_status = body.get("stock_status", "in_stock")
                    stock_count = int(body.get("stock_count", 0))
                    image_url = body.get("image_url", "").strip()
                    description = body.get("description", "").strip()
                    specs = body.get("specs", {})
                    specs_json = json.dumps(specs) if isinstance(specs, dict) else str(specs)
                    featured = 1 if body.get("featured") else 0

                    c.execute("""
                    UPDATE products 
                    SET name=?, category=?, brand=?, price=?, mrp=?, stock_status=?, stock_count=?, image_url=?, description=?, specs=?, featured=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """, (
                        name, category, brand, price, mrp, stock_status, stock_count, image_url, description, specs_json, featured, prod_id
                    ))
                    conn.commit()
                    return self.send_json({"success": True, "message": "Product updated successfully"})

            # 2. Update store settings
            elif path == "/api/settings":
                for key, val in body.items():
                    c.execute("""
                    INSERT INTO settings (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value
                    """, (key, str(val)))
                conn.commit()
                return self.send_json({"success": True, "message": "Settings updated successfully"})

            return self.send_error_json("Endpoint not found", 404)

        finally:
            conn.close()

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.parse_json_body()

        if not self.is_admin_authorized():
            return self.send_error_json("Unauthorized. Admin PIN required.", 401)

        conn = get_db()
        c = conn.cursor()

        try:
            # Quick price change: /api/products/<id>/price
            if path.startswith("/api/products/") and path.endswith("/price"):
                parts = path.strip("/").split("/")
                prod_id = int(parts[2])
                price = float(body.get("price", 0))
                mrp = body.get("mrp")
                if mrp is not None:
                    c.execute("UPDATE products SET price=?, mrp=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (price, float(mrp), prod_id))
                else:
                    c.execute("UPDATE products SET price=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (price, prod_id))
                conn.commit()
                return self.send_json({"success": True, "message": "Price updated successfully"})

            # Quick stock status change: /api/products/<id>/stock
            elif path.startswith("/api/products/") and path.endswith("/stock"):
                parts = path.strip("/").split("/")
                prod_id = int(parts[2])
                stock_status = body.get("stock_status")
                stock_count = body.get("stock_count")
                if stock_count is not None:
                    c.execute("UPDATE products SET stock_status=?, stock_count=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (stock_status, int(stock_count), prod_id))
                else:
                    c.execute("UPDATE products SET stock_status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (stock_status, prod_id))
                conn.commit()
                return self.send_json({"success": True, "message": "Stock status updated successfully"})

            # Quick booking status update: /api/bookings/<id>/status
            elif path.startswith("/api/bookings/") and path.endswith("/status"):
                parts = path.strip("/").split("/")
                booking_id = parts[2]
                new_status = body.get("status")
                c.execute("UPDATE bookings SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (new_status, booking_id))
                conn.commit()
                return self.send_json({"success": True, "message": f"Booking marked as {new_status}"})

            return self.send_error_json("Endpoint not found", 404)

        finally:
            conn.close()

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if not self.is_admin_authorized():
            return self.send_error_json("Unauthorized. Admin PIN required.", 401)

        conn = get_db()
        c = conn.cursor()

        try:
            # Delete product: /api/products/<id>
            if path.startswith("/api/products/"):
                parts = path.strip("/").split("/")
                if len(parts) == 3 and parts[2].isdigit():
                    prod_id = int(parts[2])
                    c.execute("DELETE FROM products WHERE id=?", (prod_id,))
                    conn.commit()
                    return self.send_json({"success": True, "message": "Product deleted successfully"})

            # Delete booking: /api/bookings/<id>
            elif path.startswith("/api/bookings/"):
                parts = path.strip("/").split("/")
                if len(parts) == 3:
                    booking_id = parts[2]
                    c.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
                    conn.commit()
                    return self.send_json({"success": True, "message": "Booking deleted successfully"})

            return self.send_error_json("Endpoint not found", 404)

        finally:
            conn.close()

def run_server(port=8080):
    server_address = ("0.0.0.0", port)
    httpd = ThreadingHTTPServer(server_address, StoreHTTPRequestHandler)
    print(f"===========================================================")
    print(f" VISHWAKARMA HARDWARE & SANITARY (Pathankot, Punjab)")
    print(f" Owner: Yuvraj Saini | WhatsApp: +91 98550 16374")
    print(f" Modern Storefront & Admin Portal Running at:")
    print(f" -> Customer Storefront: http://localhost:{port}")
    print(f" -> Admin Portal:        http://localhost:{port}/admin")
    print(f" Default Admin PIN:      0206")
    print(f"===========================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server gracefully...")
        httpd.server_close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port)
