"""
data/orders.py — Order database and delivery/refund policies.
"""

ORDER_DATABASE: dict = {
    "ORD-201": {
        "item_id": "DISH003",
        "item_name": "Butter Chicken",
        "customer_name": "Priya Nair",
        "customer_email": "priya@example.com",
        "status": "Out for Delivery",
        "price": 379,
        "order_date": "2026-03-05",
        "estimated_delivery": "2026-03-05 19:30",
        "tracking_id": "SS201TRK",
    },
    "ORD-202": {
        "item_id": "DISH001",
        "item_name": "Margherita Pizza",
        "customer_name": "Arjun Mehta",
        "customer_email": "arjun@example.com",
        "status": "Placed",
        "price": 299,
        "order_date": "2026-03-06",
        "estimated_delivery": "2026-03-06 20:00",
        "tracking_id": "SS202TRK",
    },
    "ORD-203": {
        "item_id": "DISH005",
        "item_name": "Classic Cheeseburger",
        "customer_name": "Sneha Roy",
        "customer_email": "sneha@example.com",
        "status": "Preparing",
        "price": 259,
        "order_date": "2026-03-06",
        "estimated_delivery": "2026-03-06 19:45",
        "tracking_id": "SS203TRK",
    },
    "ORD-204": {
        "item_id": "DISH004",
        "item_name": "Vegan Buddha Bowl",
        "customer_name": "Rahul Das",
        "customer_email": "rahul@example.com",
        "status": "Delivered",
        "price": 319,
        "order_date": "2026-03-05",
        "estimated_delivery": "2026-03-05 18:00",
        "tracking_id": "SS204TRK",
    },
    "ORD-205": {
        "item_id": "DISH006",
        "item_name": "Paneer Tikka",
        "customer_name": "Kavya Sharma",
        "customer_email": "kavya@example.com",
        "status": "Placed",
        "price": 199,
        "order_date": "2026-03-06",
        "estimated_delivery": "2026-03-06 20:15",
        "tracking_id": "SS205TRK",
    },
}


DELIVERY_POLICIES = """\
DELIVERY OPTIONS:
- Express (30 min): ₹49, available in metro cities
- Standard (60 min): ₹29
- Scheduled (choose time): Free on orders over ₹500

CANCELLATION & REFUND POLICY:
| Order Status       | Refund         | Processing Time   |
|--------------------|----------------|-------------------|
| Placed             | 100% refund    | 1-2 business days |
| Preparing          | 50% refund     | 2-3 business days |
| Out for Delivery   | No refund      | N/A               |
| Delivered          | No refund      | N/A               |

ESCALATION:
- Customers can request human support for unresolved complaints.
- Target response time: 30 minutes.
"""
