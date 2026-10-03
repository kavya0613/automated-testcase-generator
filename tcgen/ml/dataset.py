"""Synthetic training data for the TensorFlow classifiers (no sensitive data involved)."""
from __future__ import annotations

import random

ACTORS = ["a registered user", "a customer", "a new visitor", "a shopper", "an admin",
          "a logged-in user", "a member", "an account holder"]

CATEGORIES: dict[str, dict] = {
    "Authentication": {
        "goals": ["log in using my email and password", "reset my forgotten password using an email link",
                  "sign in with my mobile number and a one-time passcode", "log out securely from my account",
                  "change my password from the account settings page"],
        "benefits": ["I can access my account", "my account stays secure", "I can regain access quickly"],
        "details": ["Invalid credentials must show an error.", "Accounts lock after five failed attempts."],
        "short": ["login", "sign in", "logout", "password reset", "authentication"],
    },
    "Payment": {
        "goals": ["pay for my order using a credit card", "pay using UPI or net banking",
                  "save a card for faster checkout", "receive a payment receipt by email",
                  "request a refund for a cancelled order"],
        "benefits": ["I can complete my purchase", "my payment is processed securely", "I have proof of purchase"],
        "details": ["Declined cards must show a clear message.", "Card details must be encrypted."],
        "short": ["payment", "checkout payment", "card payment", "refund", "pay online"],
    },
    "Registration": {
        "goals": ["create an account with my name, email and password", "register using my phone number",
                  "verify my email address after signing up", "accept the terms and conditions while signing up",
                  "sign up with my social media account"],
        "benefits": ["I can use the application", "my account is verified", "I can personalise my experience"],
        "details": ["Email must be unique.", "Passwords must be at least eight characters."],
        "short": ["registration", "sign up", "create account", "email verification", "new user signup"],
    },
    "Search": {
        "goals": ["search for products using keywords", "filter search results by price and rating",
                  "sort search results by relevance or date", "see suggestions while typing in the search box",
                  "view a clear message when no results are found"],
        "benefits": ["I can find items quickly", "I can narrow down my choices", "I do not waste time"],
        "details": ["Search must be case insensitive.", "Results must load within three seconds."],
        "short": ["search", "product search", "search filter", "search suggestions", "keyword search"],
    },
    "Shopping Cart": {
        "goals": ["add items to my shopping cart", "update the quantity of an item in my cart",
                  "remove an item from my cart", "apply a discount coupon in my cart",
                  "see the total price of my cart including taxes"],
        "benefits": ["I can buy several items together", "I can control what I purchase", "I know what I will pay"],
        "details": ["Quantity cannot exceed available stock.", "The cart must persist after logout."],
        "short": ["cart", "add to cart", "cart quantity", "coupon code", "remove from cart"],
    },
    "Profile": {
        "goals": ["update my name and phone number in my profile", "upload a profile picture",
                  "view my personal details on a profile page", "change my communication preferences",
                  "delete my profile permanently"],
        "benefits": ["my information stays current", "my account looks personal", "I control my data"],
        "details": ["Mandatory fields cannot be blank.", "Pictures must be JPG or PNG under 2 MB."],
        "short": ["profile", "edit profile", "profile picture", "account settings", "profile update"],
    },
    "Notification": {
        "goals": ["receive an email notification when my order ships", "enable or disable push notifications",
                  "see unread notifications in a notification centre", "mark notifications as read",
                  "choose which events trigger an alert"],
        "benefits": ["I stay informed", "I am not disturbed unnecessarily", "I do not miss important updates"],
        "details": ["Notifications must be delivered within one minute.", "Users can unsubscribe at any time."],
        "short": ["notification", "email alert", "push notification", "alert settings", "reminder"],
    },
    "Data Management": {
        "goals": ["create a new employee record", "edit an existing record", "delete a record after confirming",
                  "import records from a CSV file", "export records to a spreadsheet"],
        "benefits": ["the data stays accurate", "I can manage records efficiently", "I can share data with my team"],
        "details": ["Mandatory fields must be validated.", "Deleted records require confirmation."],
        "short": ["data entry", "record management", "csv import", "export data", "edit records"],
    },
}

VAGUE_TEMPLATES = [
    "The system should handle {s} properly and be fast, etc.",
    "As a user, I want {s} to work somehow in an appropriate way.",
    "Make the {s} better and user-friendly, and so on.",
    "{S} should be good and flexible as needed.",
    "I want {s} to be nice and easy and work properly.",
]
INCOMPLETE_TEMPLATES = ["User should {s}.", "{S} feature needed.", "Add {s}.", "Need {s}.", "Support {s}."]


def generate_dataset(n_complete: int = 40, n_incomplete: int = 20, n_ambiguous: int = 20, seed: int = 7):
    """Return a list of {text, category, quality} rows."""
    rng = random.Random(seed)
    rows = []
    for cat, d in CATEGORIES.items():
        for _ in range(n_complete):
            actor, goal, ben = rng.choice(ACTORS), rng.choice(d["goals"]), rng.choice(d["benefits"])
            if rng.random() < 0.25:
                text = f"As {actor}, I need to {goal}, so that {ben}."
            else:
                text = f"As {actor}, I want to {goal} so that {ben}."
            if rng.random() < 0.6:
                text += " " + rng.choice(d["details"])
            rows.append({"text": text, "category": cat, "quality": "Complete"})
        for _ in range(n_incomplete):
            s = rng.choice(d["short"])
            text = rng.choice(INCOMPLETE_TEMPLATES).format(s=s, S=s.capitalize())
            rows.append({"text": text, "category": cat, "quality": "Incomplete"})
        for _ in range(n_ambiguous):
            s = rng.choice(d["short"])
            text = rng.choice(VAGUE_TEMPLATES).format(s=s, S=s.capitalize())
            rows.append({"text": text, "category": cat, "quality": "Ambiguous"})
    rng.shuffle(rows)
    return rows
