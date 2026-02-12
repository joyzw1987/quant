from datetime import datetime


ORDER_STATUS_NEW = "NEW"
ORDER_STATUS_ACKED = "ACKED"
ORDER_STATUS_PARTIAL = "PARTIAL"
ORDER_STATUS_FILLED = "FILLED"
ORDER_STATUS_CANCELING = "CANCELING"
ORDER_STATUS_CANCELED = "CANCELED"
ORDER_STATUS_REJECTED = "REJECTED"

TERMINAL_STATES = {ORDER_STATUS_FILLED, ORDER_STATUS_CANCELED, ORDER_STATUS_REJECTED}

_ALLOWED = {
    ORDER_STATUS_NEW: {ORDER_STATUS_ACKED, ORDER_STATUS_REJECTED, ORDER_STATUS_FILLED},
    ORDER_STATUS_ACKED: {ORDER_STATUS_PARTIAL, ORDER_STATUS_FILLED, ORDER_STATUS_CANCELING, ORDER_STATUS_REJECTED},
    ORDER_STATUS_PARTIAL: {ORDER_STATUS_PARTIAL, ORDER_STATUS_FILLED, ORDER_STATUS_CANCELING, ORDER_STATUS_REJECTED},
    ORDER_STATUS_CANCELING: {ORDER_STATUS_CANCELED, ORDER_STATUS_FILLED, ORDER_STATUS_REJECTED},
}


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class OrderStateMachine:
    def __init__(self):
        self.orders = {}

    def create_order(self, order_id, symbol, direction, price, size, order_type="LIMIT"):
        order = {
            "order_id": order_id,
            "symbol": symbol,
            "direction": direction,
            "price": float(price),
            "size": float(size),
            "filled": 0.0,
            "status": ORDER_STATUS_NEW,
            "order_type": order_type,
            "created_at": _now(),
            "updated_at": _now(),
            "message": "",
        }
        self.orders[order_id] = order
        return order

    def get(self, order_id):
        return self.orders.get(order_id)

    def transition(self, order_id, new_status, filled=None, message=""):
        order = self.orders.get(order_id)
        if order is None:
            return False, "ORDER_NOT_FOUND"

        old_status = order.get("status")
        if old_status in TERMINAL_STATES:
            return False, f"TERMINAL_STATE:{old_status}"

        allowed = _ALLOWED.get(old_status, set())
        if new_status not in allowed:
            return False, f"INVALID_TRANSITION:{old_status}->{new_status}"

        if filled is not None:
            order["filled"] = float(filled)
        order["status"] = new_status
        order["updated_at"] = _now()
        if message:
            order["message"] = str(message)
        return True, ""

    def all_orders(self):
        return list(self.orders.values())
