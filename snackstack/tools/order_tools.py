"""
tools/order_tools.py — Tools available to the Order Agent.

Supports lookup by order ID, tracking ID, or customer email.
"""

from langchain_core.tools import tool
from snackstack.data.orders import ORDER_DATABASE


def find_order(key: str) -> tuple[str | None, dict | None]:
    """Search ORDER_DATABASE by order ID, tracking ID, or email.

    Returns (order_id, order_dict) or (None, None) if not found.
    """
    key = key.strip()

    # 1. Direct order ID match (e.g. ORD-201)
    upper_key = key.upper()
    if upper_key in ORDER_DATABASE:
        return upper_key, ORDER_DATABASE[upper_key]

    # 2. Search by tracking ID or email
    for oid, order in ORDER_DATABASE.items():
        if order["tracking_id"].upper() == upper_key:
            return oid, order
        if order["customer_email"].lower() == key.lower():
            return oid, order

    return None, None


def format_order(order_id: str, order: dict) -> str:
    """Format order details into a readable string."""
    return (
        f"Order {order_id} Details:\n"
        f"  Item       : {order['item_name']}\n"
        f"  Customer   : {order['customer_name']}\n"
        f"  Email      : {order['customer_email']}\n"
        f"  Status     : {order['status']}\n"
        f"  Price      : ₹{order['price']}\n"
        f"  Ordered on : {order['order_date']}\n"
        f"  Est. delivery: {order['estimated_delivery']}\n"
        f"  Tracking ID: {order['tracking_id']}"
    )


@tool
def get_order_status(lookup_key: str) -> str:
    """Look up the current status of a customer's order.

    Args:
        lookup_key: An order ID (e.g. 'ORD-201'), tracking ID (e.g. 'SS201TRK'),
                    or customer email (e.g. 'priya@example.com').

    Returns:
        Formatted order details including status and estimated delivery,
        or an error message if no matching order was found.
    """
    order_id, order = find_order(lookup_key)

    if not order:
        return (
            f"No order found for '{lookup_key}'. "
            "Please double-check and provide a valid Order ID (e.g. ORD-201), "
            "Tracking ID (e.g. SS201TRK), or email address."
        )

    return format_order(order_id, order)


# Convenient list for binding to the LLM / building ToolNodes
order_tools_list = [get_order_status]
