import psycopg2
from decimal import Decimal
from datetime import datetime
from config import DB_CONFIG

class TikTokShopifyBridge:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.cur = self.conn.cursor()
        except Exception as e:
            print(f"Connection Error: {e}")

    def get_shopify_sku(self, tiktok_sku):
        """Matches TikTok SKU to Shopify SKU using the mapping table"""
        self.cur.execute("SELECT shopify_sku FROM sku_mapping WHERE tiktok_sku = %s", (tiktok_sku,))
        result = self.cur.fetchone()
        return result[0] if result else None

    def process_new_order(self, tk_order):
        """Processes order, calculates fees, and detects affiliate involvement"""
        sp_sku = self.get_shopify_sku(tk_order['sku'])
        
        if not sp_sku:
            print(f"Skipping Order {tk_order['id']}: SKU {tk_order['sku']} not mapped.")
            return

        # Financial Calculations
        gross = Decimal(tk_order['total'])
        tiktok_fee = gross * Decimal('0.06') # Standard 6% platform fee
        aff_comm = Decimal(tk_order.get('affiliate_comm_paid', 0))
        net = gross - tiktok_fee - aff_comm

        # Affiliate Revenue Logic
        is_affiliate = tk_order.get('is_affiliate_order', False)
        aff_rev = gross if is_affiliate else Decimal('0.00')

        try:
            self.cur.execute("""
                INSERT INTO orders_integration 
                (tiktok_order_id, customer_email, customer_phone, gross_sales, 
                 tiktok_fees, affiliate_commissions, net_revenue, 
                 is_affiliate_order, affiliate_revenue, sync_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'synced')
                ON CONFLICT (tiktok_order_id) DO NOTHING
            """, (tk_order['id'], tk_order['email'], tk_order['phone'], gross, 
                  tiktok_fee, aff_comm, net, is_affiliate, aff_rev))
            
            self.conn.commit()
            print(f"Successfully processed Order: {tk_order['id']}")
        except Exception as e:
            print(f"Database Error: {e}")
            self.conn.rollback()

    def record_gmv_max_spend(self, date_str, amount):
        """Records daily GMV Max ad spending (Marketing Spend)"""
        try:
            self.cur.execute("""
                INSERT INTO ad_spend (spend_date, gmv_max_cost)
                VALUES (%s, %s)
                ON CONFLICT (spend_date) DO UPDATE SET gmv_max_cost = EXCLUDED.gmv_max_cost
            """, (date_str, amount))
            self.conn.commit()
            print(f"Recorded €{amount} GMV Max spend for {date_str}")
        except Exception as e:
            print(f"Error recording spend: {e}")
            self.conn.rollback()

    def get_thorough_dashboard(self):
        """Generates the detailed KPI dashboard requested by GOFOR360"""
        query = """
            SELECT 
                COALESCE(SUM(gross_sales), 0), 
                (SELECT COALESCE(SUM(gmv_max_cost), 0) FROM ad_spend),
                COALESCE(SUM(affiliate_revenue), 0),
                COALESCE(SUM(affiliate_commissions), 0),
                (COALESCE(SUM(net_revenue), 0) - (SELECT COALESCE(SUM(gmv_max_cost), 0) FROM ad_spend))
            FROM orders_integration;
        """
        self.cur.execute(query)
        gmv, gmv_max, aff_rev, aff_comm, net_profit = self.cur.fetchone()

        print("\n" + "="*45)
        print("      GOFOR360 - TIKTOK SHOP ANALYTICS")
        print("="*45)
        print(f"TOTAL GMV:               €{gmv:,.2f}")
        print(f"GMV MAX SPENDING (ADS):  €{gmv_max:,.2f}")
        print("-" * 45)
        print(f"AFFILIATES' REVENUE:     €{aff_rev:,.2f}")
        print(f"COMMISSIONS PAID:        €{aff_comm:,.2f}")
        print("-" * 45)
        print(f"TOTAL NET REVENUE:       €{net_profit:,.2f}")
        print("="*45 + "\n")

    def close(self):
        self.cur.close()
        self.conn.close()

# --- EXECUTION BLOCK (TEST DATA) ---
if __name__ == "__main__":
    bridge = TikTokShopifyBridge()

    # 1. Clear/Record Ad Spend for various days
    bridge.record_gmv_max_spend("2026-01-10", 12.50)
    bridge.record_gmv_max_spend("2026-01-11", 18.00)
    bridge.record_gmv_max_spend("2026-01-12", 25.00)

    # 2. Process a mix of orders (Organic and Affiliate)
    test_orders = [
        {
            "id": "TT-ORG-001", 
            "sku": "TK-IT-BLUE-S",
            "total": "45.00",
            "email": "organic_user@gmail.com",
            "phone": "+39 331 000000",
            "is_affiliate_order": False,
            "affiliate_comm_paid": "0.00"
        },
        {
            "id": "TT-AFF-002", 
            "sku": "TK-IT-BLUE-M",
            "total": "100.00",
            "email": "affiliate_user@yahoo.it",
            "phone": "+39 332 999999",
            "is_affiliate_order": True,
            "affiliate_comm_paid": "10.00"
        }
    ]

    for order in test_orders:
        bridge.process_new_order(order)

    # 3. Final Output
    bridge.get_thorough_dashboard()
    
    bridge.close()