"""Food Ordering AI Agent — Streamlit chat app.

Run it:
    pip install streamlit
    streamlit run food_order_app.py

Your browser opens a chat window where you type (or paste) orders like
"2 farmhouse pizzas and a coke", see the cart, totals, and a Swiggy
Instamart redirect button — same as the canvas version.
"""

import re
from urllib.parse import quote

import streamlit as st

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

MENU = [
    {"id": "margherita", "name": "Margherita Pizza", "category": "Pizza", "price": 249,
     "keywords": ["margherita", "cheese pizza"]},
    {"id": "pepperoni", "name": "Pepperoni Pizza", "category": "Pizza", "price": 299,
     "keywords": ["pepperoni"]},
    {"id": "farmhouse", "name": "Farmhouse Pizza", "category": "Pizza", "price": 349,
     "keywords": ["farmhouse", "veggie pizza", "vegetarian pizza"]},
    {"id": "burger", "name": "Cheeseburger", "category": "Burgers", "price": 179,
     "keywords": ["cheeseburger", "burger"]},
    {"id": "veg-burger", "name": "Veggie Burger", "category": "Burgers", "price": 149,
     "keywords": ["veggie burger", "vegetable burger"]},
    {"id": "fries", "name": "French Fries", "category": "Sides", "price": 99,
     "keywords": ["fries", "french fries", "chips"]},
    {"id": "nuggets", "name": "Chicken Nuggets", "category": "Sides", "price": 189,
     "keywords": ["nuggets"]},
    {"id": "coke", "name": "Coca-Cola", "category": "Drinks", "price": 60,
     "keywords": ["coke", "coca-cola", "cola"]},
    {"id": "sprite", "name": "Sprite", "category": "Drinks", "price": 60,
     "keywords": ["sprite", "lemon soda"]},
    {"id": "lassi", "name": "Mango Lassi", "category": "Drinks", "price": 90,
     "keywords": ["lassi", "mango lassi"]},
    {"id": "brownie", "name": "Chocolate Brownie", "category": "Dessert", "price": 129,
     "keywords": ["brownie", "chocolate brownie"]},
    {"id": "icecream", "name": "Vanilla Ice Cream", "category": "Dessert", "price": 79,
     "keywords": ["ice cream", "icecream", "vanilla"]},
]

NUM_WORDS = {
    "one": 1, "a": 1, "an": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

DELIVERY_FEE = 39
GST_RATE = 0.05

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def safe_num(n):
    try:
        n = float(n)
        return n if n == n else 0
    except (TypeError, ValueError):
        return 0


def rupees(n):
    return "₹" + str(int(round(safe_num(n))))


def cart_totals(cart):
    item_total = safe_num(sum(l["price"] * l.get("qty", 1) for l in cart))
    count = int(safe_num(sum(l.get("qty", 1) for l in cart)))
    delivery = DELIVERY_FEE if cart else 0
    taxes = int(round(item_total * GST_RATE))
    grand = int(item_total + delivery + taxes)
    return {"item_total": int(item_total), "count": count,
            "delivery": delivery, "taxes": taxes, "grand_total": grand}


def group_cart(cart):
    grouped = {}
    for l in cart:
        g = grouped.setdefault(l["id"], {"name": l["name"], "price": l["price"], "qty": 0})
        g["qty"] += l.get("qty", 1)
    return grouped


def instamart_url(cart):
    query = ", ".join(
        f"{g['qty']} {g['name']}" if g["qty"] > 1 else g["name"]
        for g in group_cart(cart).values()
    )
    return f"https://www.swiggy.com/instamart/search?query={quote(query)}"


# ---------------------------------------------------------------------------
# Order parser
# ---------------------------------------------------------------------------

REMOVE_WORDS = ("remove", "delete", "cancel", "drop", "without")


def parse_order(text):
    lower = " " + text.lower() + " "
    adds, removes = [], []
    is_remove = any(f" {w} " in lower for w in REMOVE_WORDS)

    for item in MENU:
        for kw in item["keywords"] + [item["name"].lower()]:
            m = lower.find(" " + kw)
            if m == -1:
                m = lower.find(kw + " ")
            if m == -1:
                continue
            before = lower[max(0, m - 12):m].strip().split()
            last_tok = before[-1] if before else ""
            qty = NUM_WORDS.get(last_tok, int(last_tok) if last_tok.isdigit() else 1)
            qty = max(1, min(int(safe_num(qty)), 20))
            nearby = lower[max(0, m - 25):m + len(kw)]
            if is_remove and any(f" {w} " in nearby for w in REMOVE_WORDS):
                removes.append({"item": item, "qty": qty})
            else:
                adds.append({"item": item, "qty": qty})
            break
    return adds, removes


# ---------------------------------------------------------------------------
# Agent logic
# ---------------------------------------------------------------------------


def agent_reply(text, cart):
    """Return (reply_message, new_cart, extras)."""
    lower = text.lower()

    if re.match(r"^(hi|hello|hey)\b", lower):
        return ("Hi! I'm your food ordering assistant. Tell me what you'd like — "
                'e.g. "2 pepperoni pizzas and a coke". Ask "menu" or "cart" anytime.'), cart, {}

    if any(w in lower for w in ("menu", "options", "what can i order")):
        lines = "\n".join(f"- {it['name']} ({it['category']}) — {rupees(it['price'])}" for it in MENU)
        return "Here's our menu:\n" + lines, cart, {"menu": True}

    if ("cart" in lower or "order so far" in lower) and "clear" not in lower and "empty" not in lower:
        if not cart:
            return "Your cart is empty. What can I get you?", cart, {}
        t = cart_totals(cart)
        lines = "\n".join(
            f"- {g['qty']} × {g['name']} — {rupees(g['price'] * g['qty'])}"
            for g in group_cart(cart).values())
        return (f"Your current cart ({t['count']} items):\n{lines}\n"
                f"Item total {rupees(t['item_total'])}, "
                f"{rupees(t['grand_total'])} including delivery and GST. "
                'Say "checkout" when ready.'), cart, {"cart": True}

    if ("clear" in lower or "empty" in lower or "reset" in lower) and ("cart" in lower or "order" in lower):
        return "Cart cleared. What would you like instead?", [], {}

    if any(w in lower for w in ("checkout", "place order", "place the order",
                                "confirm", "done", "that's all")):
        if not cart:
            return "Your cart is empty — add something first!", cart, {}
        t = cart_totals(cart)
        lines = "\n".join(
            f"- {g['qty']} × {g['name']} — {rupees(g['price'] * g['qty'])}"
            for g in group_cart(cart).values())
        msg = (f"You ordered {t['count']} items:\n{lines}\n\n"
               f"Item total {rupees(t['item_total'])} + delivery {rupees(t['delivery'])} "
               f"+ GST {rupees(t['taxes'])} = **{rupees(t['grand_total'])}** total.\n"
               "Tap the button below to order on Instamart. 🎉")
        return msg, [], {"checkout": True, "url": instamart_url(cart), "order": cart}

    adds, removes = parse_order(text)
    if not adds and not removes:
        if any(w in lower for w in ("delivery", "how long", "time")):
            return "Delivery typically takes 30–40 minutes after checkout.", cart, {}
        if any(w in lower for w in ("pay", "payment", "upi", "card", "cash")):
            return "We accept UPI, cards, and cash on delivery. Payment happens at checkout.", cart, {}
        return ("Sorry, I didn't catch that. Try naming a menu item "
                '(e.g. "add a farmhouse pizza"), or ask "menu".'), cart, {}

    next_cart = list(cart)
    for r in removes:
        for i, l in enumerate(next_cart):
            if l["id"] == r["item"]["id"]:
                next_cart.pop(i)
                break
    for a in adds:
        next_cart.append({"id": a["item"]["id"], "name": a["item"]["name"],
                          "price": a["item"]["price"], "qty": a["qty"]})

    reply = " ".join(
        [f"Removed {r['item']['name']}." for r in removes] +
        [f"Added {a['qty']} × {a['item']['name']} ({rupees(a['item']['price'] * a['qty'])})."
         for a in adds])
    if not next_cart:
        reply += " Your cart is now empty."
    else:
        t = cart_totals(next_cart)
        reply += (f" That's {t['count']} items in your cart, item total "
                  f"{rupees(t['item_total'])}, and {rupees(t['grand_total'])} "
                  'including delivery and GST. Anything else, or say "checkout".')
    return reply, next_cart, {}


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Food Ordering AI Agent", page_icon="🍕", layout="centered")

st.title("🍕 Food Ordering AI Agent")
st.caption("Chat with me to build your order — then redirect to Swiggy Instamart")

if "cart" not in st.session_state:
    st.session_state.cart = []
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant",
         "content": 'Hi! I\'m your food ordering assistant. Tell me what you\'d like — '
                    'e.g. "2 farmhouse pizzas, fries and a coke", "menu", or "checkout".'}
    ]

# sidebar: bill summary
with st.sidebar:
    st.header("🛒 Your Cart")
    if st.session_state.cart:
        for g in group_cart(st.session_state.cart).values():
            st.write(f"{g['qty']} × {g['name']} — {rupees(g['price'] * g['qty'])}")
        t = cart_totals(st.session_state.cart)
        st.markdown("---")
        st.write(f"Item total: **{rupees(t['item_total'])}**")
        st.write(f"Delivery: {rupees(t['delivery'])}")
        st.write(f"GST (5%): {rupees(t['taxes'])}")
        st.markdown(f"### Grand total: {rupees(t['grand_total'])}")
        st.link_button("🛍️ Order on Instamart", instamart_url(st.session_state.cart))
        if st.button("Clear cart"):
            st.session_state.cart = []
            st.rerun()
    else:
        st.write("Cart is empty. Order something!")

# chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=False)
        if msg.get("checkout"):
            st.success("✅ Order placed! Estimated delivery: 35 minutes.")
            st.link_button("🛍️ Order on Instamart", msg["url"])

# input
if prompt := st.chat_input("e.g. 2 farmhouse pizzas, fries and a coke"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    reply, new_cart, extras = agent_reply(prompt, st.session_state.cart)
    st.session_state.cart = new_cart
    st.session_state.messages.append(
        {"role": "assistant", "content": reply, **extras})
    with st.chat_message("assistant"):
        st.markdown(reply)
        if extras.get("checkout"):
            st.success("✅ Order placed! Estimated delivery: 35 minutes.")
            st.link_button("🛍️ Order on Instamart", extras["url"])