import sys
import asyncio
import json
import secrets
import hmac
import threading
from pathlib import Path
from functools import wraps

from flask import (
    Flask, jsonify, request, render_template,
    redirect, url_for, session
)

ROOT = Path(__file__).resolve().parent.parent
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from chronosmatch.matching_engine import MatchingEngine
from chronosmatch.trade_ledger import TradeLedger
from chronosmatch.market_simulator import MarketSimulator
from chronosmatch.trading_pipeline import run_trading_pipeline

from auth import create_user, authenticate_user, get_user_by_id


# --------------------------------------------------
# Flask configuration
# --------------------------------------------------

secret_file = BASE_DIR / ".secret_key"

if not secret_file.exists():
    raise RuntimeError("Session secret missing. Create web_dashboard/.secret_key first.")

app = Flask(__name__)
app.secret_key = secret_file.read_text().strip()

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,  # Set True when deployed behind HTTPS.
    PERMANENT_SESSION_LIFETIME=3600,
)


# --------------------------------------------------
# Per-user trading state
# --------------------------------------------------

USER_DATA_DIR = BASE_DIR / "user_data"
USER_DATA_DIR.mkdir(exist_ok=True)

user_states = {}
global_lock = threading.RLock()


def get_user_state(user_id):
    """Return isolated in-memory trading state for one account."""
    with global_lock:
        if user_id not in user_states:
            user_states[user_id] = {
                "engine": MatchingEngine(),
                "next_order_id": 1,
                "orders_processed": 0,
            }

        return user_states[user_id]


def get_user_ledger_path(user_id):
    return USER_DATA_DIR / f"user_{user_id}.db"


def get_orderbook(engine):
    bids = []
    asks = []

    for price in sorted(engine.bids.keys(), reverse=True):
        quantity = sum(order.quantity for order in engine.bids[price])
        bids.append({"price": price, "quantity": quantity})

    for price in sorted(engine.asks.keys()):
        quantity = sum(order.quantity for order in engine.asks[price])
        asks.append({"price": price, "quantity": quantity})

    open_orders = []

    for side, book in (("BUY", engine.bids), ("SELL", engine.asks)):
        for price, queue in book.items():
            for order in queue:
                open_orders.append({
                    "order_id": order.order_id,
                    "side": side,
                    "price": order.price,
                    "quantity": order.quantity,
                })

    open_orders.sort(key=lambda order: order["order_id"])

    return {
        "bids": bids,
        "asks": asks,
        "open_orders": open_orders,
    }


def trade_to_dict(trade):
    return {
        "buy_order_id": trade.buy_order_id,
        "sell_order_id": trade.sell_order_id,
        "price": trade.price,
        "quantity": trade.quantity,
    }


# --------------------------------------------------
# CSRF protection
# --------------------------------------------------

def get_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)

    return session["csrf_token"]


def csrf_valid():
    expected = session.get("csrf_token", "")
    supplied = (
        request.form.get("csrf_token", "")
        if request.form
        else request.headers.get("X-CSRF-Token", "")
    )

    return bool(expected and supplied and hmac.compare_digest(expected, supplied))


def require_csrf():
    if not csrf_valid():
        if request.path.startswith("/api/"):
            return jsonify({
                "success": False,
                "error": "Invalid or missing security token. Refresh the page."
            }), 400

        return "Invalid or expired security token. Please refresh the page.", 400

    return None


# --------------------------------------------------
# Authentication helpers
# --------------------------------------------------

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")

        if not user_id or not get_user_by_id(user_id):
            session.clear()

            if request.path.startswith("/api/"):
                return jsonify({
                    "success": False,
                    "error": "Please login to continue."
                }), 401

            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


@app.get("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    error = None

    if request.method == "POST":
        csrf_error = require_csrf()
        if csrf_error:
            return csrf_error

        username = request.form.get("username", "")
        email = request.form.get("email", "")
        password = request.form.get("password", "")

        success, message = create_user(username, email, password)

        if success:
            user = authenticate_user(email, password)
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            get_csrf_token()
            return redirect(url_for("dashboard"))

        error = message

    return render_template(
        "auth.html",
        mode="signup",
        error=error,
        csrf_token=get_csrf_token(),
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    error = None

    if request.method == "POST":
        csrf_error = require_csrf()
        if csrf_error:
            return csrf_error

        email = request.form.get("email", "")
        password = request.form.get("password", "")

        user = authenticate_user(email, password)

        if user:
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            get_csrf_token()
            return redirect(url_for("dashboard"))

        error = "Invalid email or password."

    return render_template(
        "auth.html",
        mode="login",
        error=error,
        csrf_token=get_csrf_token(),
    )


@app.post("/logout")
@login_required
def logout():
    csrf_error = require_csrf()
    if csrf_error:
        return csrf_error

    session.clear()
    return redirect(url_for("login"))


# --------------------------------------------------
# Dashboard
# --------------------------------------------------

@app.get("/dashboard")
@login_required
def dashboard():
    return render_template(
        "index.html",
        username=session.get("username", "User"),
        csrf_token=get_csrf_token(),
    )


# --------------------------------------------------
# API: status
# --------------------------------------------------

@app.get("/api/status")
@login_required
def status():
    user_id = session["user_id"]
    state = get_user_state(user_id)

    with global_lock:
        with TradeLedger(get_user_ledger_path(user_id)) as ledger:
            book = get_orderbook(state["engine"])
            saved_count = ledger.count_trades()

            return jsonify({
                "status": "online",
                "username": session.get("username"),
                "orders_processed": state["orders_processed"],
                "executed_trades": saved_count,
                "stored_trades": saved_count,
                "best_bid": state["engine"].best_bid(),
                "best_ask": state["engine"].best_ask(),
                "orderbook": book,
            })


# --------------------------------------------------
# API: submit order
# --------------------------------------------------

@app.post("/api/order")
@login_required
def submit_order():
    csrf_error = require_csrf()
    if csrf_error:
        return csrf_error

    user_id = session["user_id"]
    state = get_user_state(user_id)
    data = request.get_json(silent=True) or {}

    try:
        side = str(data.get("side", "")).upper()
        price = int(data.get("price"))
        quantity = int(data.get("quantity"))

        if side not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL.")

        if price <= 0 or quantity <= 0:
            raise ValueError("Price and quantity must be positive.")

        with global_lock:
            order_id = state["next_order_id"]

            with TradeLedger(get_user_ledger_path(user_id)) as ledger:
                new_trades = state["engine"].submit_order(
                    order_id, side, price, quantity
                )
                if new_trades:
                    ledger.save_trades(new_trades)

            state["next_order_id"] += 1
            state["orders_processed"] += 1

            return jsonify({
                "success": True,
                "order_id": order_id,
                "side": side,
                "price": price,
                "quantity": quantity,
                "new_trades": [trade_to_dict(t) for t in new_trades],
                "orderbook": get_orderbook(state["engine"]),
            }), 201

    except (ValueError, TypeError) as error:
        return jsonify({"success": False, "error": str(error)}), 400


# --------------------------------------------------
# API: cancel order
# --------------------------------------------------

@app.post("/api/order/cancel")
@login_required
def cancel_order():
    csrf_error = require_csrf()
    if csrf_error:
        return csrf_error

    user_id = session["user_id"]
    state = get_user_state(user_id)
    data = request.get_json(silent=True) or {}

    try:
        order_id = int(data.get("order_id"))

        if order_id <= 0:
            raise ValueError("Invalid order ID.")

        with global_lock:
            cancelled = state["engine"].cancel_order(order_id)

            if not cancelled:
                return jsonify({
                    "success": False,
                    "error": "Order not found or no longer open."
                }), 404

            return jsonify({
                "success": True,
                "order_id": order_id,
                "orderbook": get_orderbook(state["engine"]),
            })

    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "A valid order ID is required."
        }), 400


# --------------------------------------------------
# Market simulator
# --------------------------------------------------

class OffsetSimulator:
    def __init__(self, offset):
        self.simulator = MarketSimulator()
        self.offset = offset

    async def generate_orders(self, count, batch_size=1000):
        async for order_id, price, quantity in self.simulator.generate_orders(
            count, batch_size
        ):
            yield order_id + self.offset, price, quantity


@app.post("/api/simulate")
@login_required
def simulate():
    csrf_error = require_csrf()
    if csrf_error:
        return csrf_error

    user_id = session["user_id"]
    state = get_user_state(user_id)
    data = request.get_json(silent=True) or {}

    try:
        count = int(data.get("count", 100))

        if count < 1 or count > 10000:
            raise ValueError("Count must be between 1 and 10000.")

        with global_lock:
            offset = state["next_order_id"] - 1

            with TradeLedger(get_user_ledger_path(user_id)) as ledger:
                result = asyncio.run(run_trading_pipeline(
                    count=count,
                    batch_size=100,
                    simulator=OffsetSimulator(offset),
                    engine=state["engine"],
                    ledger=ledger,
                ))

            state["next_order_id"] += count
            state["orders_processed"] += result.orders_processed

            with TradeLedger(get_user_ledger_path(user_id)) as ledger:
                total_trades = ledger.count_trades()

            return jsonify({
                "success": True,
                "orders_processed": result.orders_processed,
                "total_trades": total_trades,
                "new_best_bid": result.best_bid,
                "new_best_ask": result.best_ask,
                "orderbook": get_orderbook(state["engine"]),
            })

    except (ValueError, TypeError) as error:
        return jsonify({"success": False, "error": str(error)}), 400


# --------------------------------------------------
# API: trade history
# --------------------------------------------------

@app.get("/api/trades")
@login_required
def trades():
    user_id = session["user_id"]

    with global_lock:
        with TradeLedger(get_user_ledger_path(user_id)) as ledger:
            saved_trades = ledger.get_trades()

            return jsonify({
                "count": len(saved_trades),
                "trades": [trade_to_dict(t) for t in saved_trades],
            })


@app.get("/api/orderbook")
@login_required
def orderbook():
    user_id = session["user_id"]
    state = get_user_state(user_id)

    with global_lock:
        return jsonify(get_orderbook(state["engine"]))


@app.get("/api/benchmarks")
@login_required
def benchmarks():
    folder = ROOT / "benchmarks"
    results = []

    for file in sorted(folder.glob("results*.json")):
        try:
            with file.open("r", encoding="utf-8") as source:
                data = json.load(source)

            results.append({"file": file.name, "data": data})

        except (OSError, json.JSONDecodeError):
            results.append({
                "file": file.name,
                "error": "Could not read benchmark file",
            })

    return jsonify({"count": len(results), "results": results})


@app.get("/api/health")
def health():
    return jsonify({"status": "healthy"})


# --------------------------------------------------
# Security response headers
# --------------------------------------------------

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


if __name__ == "__main__":
    print("ChronosMatch authenticated dashboard starting...")
    print("Open http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
