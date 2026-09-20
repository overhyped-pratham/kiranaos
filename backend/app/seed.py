import datetime
from sqlalchemy.orm import Session
from backend.app.database import engine, SessionLocal, Base
from backend.app.models import (
    Product,
    Customer,
    Order,
    OrderItem,
    InventoryLog,
    CustomerPreference
)

def seed_database():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        # Check if already seeded
        if db.query(Product).first():
            print("Database already contains product data.")
            return

        print("Seeding initial Kirana catalog...")

        products = [
            Product(
                id="prod_atta_aashirvaad_5kg",
                name="Aashirvaad Shudh Chakki Atta 5kg",
                brand="Aashirvaad",
                category="Atta & Flours",
                size="5kg",
                unit="bag",
                price=240.0,
                stock=25,
                low_stock_threshold=5,
                aliases=[
                    "aashirvaad atta", "aashirwad aata", "aata", "atta", 
                    "wheat flour", "आटा", "5 kilo wala aata", "5kg atta", 
                    "aashirvad", "ashirwad", "5 kilo wheat flour", "aata 5kg"
                ],
                active=True
            ),
            Product(
                id="prod_atta_aashirvaad_10kg",
                name="Aashirvaad Shudh Chakki Atta 10kg",
                brand="Aashirvaad",
                category="Atta & Flours",
                size="10kg",
                unit="bag",
                price=460.0,
                stock=10,
                low_stock_threshold=3,
                aliases=[
                    "10 kilo aata", "10kg atta", "bada atta packet", 
                    "aashirvaad 10kg", "10 kilo wheat flour", "aata 10kg"
                ],
                active=True
            ),
            Product(
                id="prod_oil_fortune_1l",
                name="Fortune Sunlite Refined Sunflower Oil 1L",
                brand="Fortune",
                category="Edible Oils",
                size="1L",
                unit="pouch",
                price=145.0,
                stock=15,
                low_stock_threshold=4,
                aliases=[
                    "fortune oil", "fortune tel", "oil", "tel", "cooking oil", 
                    "refined oil", "sunflower oil", "फॉर्च्यून तेल", "तेल", "fortune"
                ],
                active=True
            ),
            Product(
                id="prod_maggi_70g",
                name="Maggi 2-Minute Masala Instant Noodles 70g",
                brand="Maggi",
                category="Instant Food",
                size="70g",
                unit="packet",
                price=14.0,
                stock=50,
                low_stock_threshold=10,
                aliases=[
                    "maggi", "noodles", "maggi noodles", "masala noodles", 
                    "मैगी", "2 minute noodles", "magi", "maggie"
                ],
                active=True
            ),
            Product(
                id="prod_milk_amul_taaza_500ml",
                name="Amul Taaza Homogenised Toned Milk 500ml",
                brand="Amul",
                category="Dairy",
                size="500ml",
                unit="pouch",
                price=27.0,
                stock=30,
                low_stock_threshold=6,
                aliases=[
                    "amul milk", "milk", "doodh", "taaza", "toned milk", 
                    "दूध", "अमूल दूध", "amul taaza"
                ],
                active=True
            ),
            Product(
                id="prod_surf_excel_1kg",
                name="Surf Excel Quick Wash Detergent Powder 1kg",
                brand="Surf Excel",
                category="Laundry & Detergents",
                size="1kg",
                unit="packet",
                price=150.0,
                stock=12,
                low_stock_threshold=3,
                aliases=[
                    "surf excel", "surf", "detergent", "washing powder", 
                    "kapde dhone ka powder", "detergent powder", "surf excel matic"
                ],
                active=True
            ),
            Product(
                id="prod_ariel_matic_1kg",
                name="Ariel Matic Top Load Detergent Powder 1kg",
                brand="Ariel",
                category="Laundry & Detergents",
                size="1kg",
                unit="packet",
                price=195.0,
                stock=10,
                low_stock_threshold=3,
                aliases=[
                    "ariel", "ariel matic", "washing powder", "detergent", 
                    "ariel detergent"
                ],
                active=True
            ),
            Product(
                id="prod_salt_tata_1kg",
                name="Tata Salt Vacuum Evaporated Iodised Salt 1kg",
                brand="Tata",
                category="Spices & Essentials",
                size="1kg",
                unit="packet",
                price=28.0,
                stock=40,
                low_stock_threshold=8,
                aliases=[
                    "tata namak", "salt", "namak", "tata salt", "iodised salt", 
                    "नमक", "टाटा नमक"
                ],
                active=True
            ),
            Product(
                id="prod_biscuit_parle_g_250g",
                name="Parle-G Gluco Biscuits 250g",
                brand="Parle",
                category="Snacks & Biscuits",
                size="250g",
                unit="packet",
                price=25.0,
                stock=35,
                low_stock_threshold=8,
                aliases=[
                    "parle g", "biscuit", "biskut", "parle", "बिस्कुट", 
                    "parleg", "glucon d biscuit"
                ],
                active=True
            ),
            Product(
                id="prod_soap_dettol_75g",
                name="Dettol Original Bathing Soap Bar 75g",
                brand="Dettol",
                category="Personal Care",
                size="75g",
                unit="bar",
                price=38.0,
                stock=20,
                low_stock_threshold=5,
                aliases=[
                    "dettol soap", "soap", "sabun", "dettol", "साबुन", "डेटोल"
                ],
                active=True
            ),
        ]

        db.add_all(products)
        db.commit()

        # Log initial inventory
        for p in products:
            db.add(InventoryLog(
                product_id=p.id,
                order_id=None,
                change_amount=p.stock,
                previous_stock=0,
                new_stock=p.stock,
                reason="initial_stock"
            ))
        db.commit()

        # Seed Customers
        customers = [
            Customer(
                id="cust_9876543210",
                phone="+919876543210",
                name="Rahul Sharma",
                default_address="Flat 402, Shanti Kunj, Sector 14, Gurugram",
                preferences={
                    "frequent_items": [
                        {"product_id": "prod_atta_aashirvaad_5kg", "quantity": 1},
                        {"prod_id": "prod_oil_fortune_1l", "quantity": 1},
                        {"product_id": "prod_maggi_70g", "quantity": 3}
                    ],
                    "preferred_payment": "COD"
                }
            ),
            Customer(
                id="cust_9811122233",
                phone="+919811122233",
                name="Priya Verma",
                default_address="B-12, Green Park Extension, New Delhi",
                preferences={
                    "frequent_items": [
                        {"product_id": "prod_milk_amul_taaza_500ml", "quantity": 2},
                        {"product_id": "prod_biscuit_parle_g_250g", "quantity": 1}
                    ]
                }
            )
        ]
        db.add_all(customers)
        db.commit()

        # Seed Customer Preferences for "usual samaan" memory
        prefs = [
            CustomerPreference(
                customer_id="cust_9876543210",
                product_id="prod_atta_aashirvaad_5kg",
                frequency=5,
                preferred_quantity=2,
                last_ordered_at=datetime.datetime.utcnow() - datetime.timedelta(days=7)
            ),
            CustomerPreference(
                customer_id="cust_9876543210",
                product_id="prod_oil_fortune_1l",
                frequency=4,
                preferred_quantity=1,
                last_ordered_at=datetime.datetime.utcnow() - datetime.timedelta(days=12)
            ),
            CustomerPreference(
                customer_id="cust_9876543210",
                product_id="prod_maggi_70g",
                frequency=8,
                preferred_quantity=3,
                last_ordered_at=datetime.datetime.utcnow() - datetime.timedelta(days=3)
            )
        ]
        db.add_all(prefs)
        db.commit()

        # Seed past orders for historical context
        past_order = Order(
            id="ORD-20260910-001",
            customer_id="cust_9876543210",
            status="delivered",
            subtotal=667.0,
            delivery_charge=20.0,
            total=687.0,
            idempotency_key="seed_order_rahul_1",
            delivery_status="delivered",
            delivery_address="Flat 402, Shanti Kunj, Sector 14, Gurugram",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=10)
        )
        db.add(past_order)
        db.commit()

        items = [
            OrderItem(order_id="ORD-20260910-001", product_id="prod_atta_aashirvaad_5kg", product_name="Aashirvaad Shudh Chakki Atta 5kg", quantity=2, unit_price=240.0, line_total=480.0),
            OrderItem(order_id="ORD-20260910-001", product_id="prod_oil_fortune_1l", product_name="Fortune Sunlite Refined Sunflower Oil 1L", quantity=1, unit_price=145.0, line_total=145.0),
            OrderItem(order_id="ORD-20260910-001", product_id="prod_maggi_70g", product_name="Maggi 2-Minute Masala Instant Noodles 70g", quantity=3, unit_price=14.0, line_total=42.0)
        ]
        db.add_all(items)
        db.commit()

        print("Database seeded successfully with realistic Kirana catalog, inventory, and customers.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
