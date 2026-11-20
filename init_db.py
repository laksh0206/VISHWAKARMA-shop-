"""
Database initialization and configuration for VISHWAKARMA HARDWARE & SANITARY.
Owner: Yuvraj Saini
Location: Main Road, Adda Parmanand (Near HDFC Bank), Pathankot, Punjab
Timings: 9:00 AM - 8:00 PM (All 7 Days)
WhatsApp / Call: 9855016374
Email: lakshdeepsaini72@gmail.com
PIN: 0206
"""
import sqlite3
import json
import os
from pathlib import Path

DB_FILE = Path(__file__).parent / "store.db"

# The user explicitly requested an empty catalog so they can add their own products via the Admin Portal
SAMPLE_PRODUCTS = []

STORE_SETTINGS = {
    "shop_name": "VISHWAKARMA HARDWARE & SANITARY",
    "owner_name": "Yuvraj Saini",
    "tagline": "Quality Hardware, Luxury Sanitaryware & Plumbing Solutions | Pathankot, Punjab",
    "phone": "+91 98550 16374",
    "whatsapp": "9855016374",
    "email": "lakshdeepsaini72@gmail.com",
    "address": "Main Road, Adda Parmanand (Near HDFC Bank), Pathankot, Punjab",
    "city": "Pathankot, Punjab",
    "timings": "9:00 AM - 8:00 PM (Open All 7 Days)",
    "admin_pin": "0206",
    "currency_symbol": "₹",
    "google_maps_url": "https://maps.app.goo.gl/miQgZFEjnFEwSdhT7",
    "upi_id": "9855016374@upi",
    "tax_note": "Prices shown are store wholesale-friendly rates.",
    "banner_announcement": "Welcome to VISHWAKARMA HARDWARE & SANITARY • Owner: Yuvraj Saini • Call or WhatsApp: +91 98550 16374 • Open 9 AM to 8 PM (All 7 Days)"
}

def init_database(force_clean=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Products Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        brand TEXT NOT NULL,
        price REAL NOT NULL,
        mrp REAL NOT NULL,
        stock_status TEXT NOT NULL DEFAULT 'in_stock',
        stock_count INTEGER DEFAULT 10,
        rating REAL DEFAULT 4.8,
        reviews_count INTEGER DEFAULT 15,
        image_url TEXT NOT NULL,
        description TEXT NOT NULL,
        specs TEXT DEFAULT '{}',
        featured INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Bookings Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id TEXT PRIMARY KEY,
        customer_name TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        customer_email TEXT DEFAULT '',
        booking_type TEXT NOT NULL DEFAULT 'store_pickup',
        delivery_address TEXT DEFAULT '',
        preferred_date TEXT DEFAULT '',
        preferred_time TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        items_json TEXT NOT NULL,
        subtotal REAL NOT NULL,
        discount_amount REAL DEFAULT 0,
        estimated_total REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Store Settings Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    if force_clean:
        # Clear products as requested by user
        c.execute("DELETE FROM products")
        c.execute("DELETE FROM bookings")

    # Insert or update settings
    for k, v in STORE_SETTINGS.items():
        c.execute("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (k, str(v)))

    conn.commit()
    conn.close()
    print("Database configured successfully at:", DB_FILE)
    print("Catalog cleared for custom product entry. Admin PIN set to: 0206")

if __name__ == "__main__":
    init_database(force_clean=False)
