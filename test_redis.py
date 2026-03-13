from redis_client import save_session, get_session, delete_session

phone = "919876543210"

# Save
save_session(phone, {
    "current_module": "menu_order",
    "conversation_stage": "browsing",
    "cart_items": [{"item": "Paneer Tikka", "qty": 2, "price": 320}],
    "cart_total": 320,
    "last_intent": "menu_order"
})
print("✅ Session saved")

# Get
session = get_session(phone)
print("✅ Session fetched:", session)

# Delete
delete_session(phone)
print("✅ Session deleted")
