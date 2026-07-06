# ENVI Ledger constants

CURRENCY_NAME = "Nexus Credits"
CURRENCY_SYMBOL = "₦C"

STARTING_BALANCE = 0

DAILY_AMOUNT = 500
DAILY_COOLDOWN_SECONDS = 24 * 60 * 60

WORK_MIN_AMOUNT = 150
WORK_MAX_AMOUNT = 500
WORK_COOLDOWN_SECONDS = 4 * 60 * 60

LEADERBOARD_LIMIT = 10

# ENVI green from the Exordium Nexus visual system
ENVI_GREEN = 0x40EF5B

TRANSACTION_DAILY = "DAILY_CLAIM"
TRANSACTION_WORK = "WORK_PAYOUT"
TRANSACTION_TRANSFER_SENT = "USER_TRANSFER_SENT"
TRANSACTION_TRANSFER_RECEIVED = "USER_TRANSFER_RECEIVED"
TRANSACTION_SHOP_PURCHASE = "SHOP_PURCHASE"
TRANSACTION_ADMIN_ADD = "ADMIN_ADD"
TRANSACTION_ADMIN_REMOVE = "ADMIN_REMOVE"
TRANSACTION_ADMIN_SET = "ADMIN_SET"
TRANSACTION_ADMIN_RESET = "ADMIN_RESET"


# -----------------------------
# V1.5 Shop Metadata
# -----------------------------

DEFAULT_SHOP_CATEGORY = "General"
DEFAULT_ITEM_RARITY = "Common"

SHOP_CATEGORIES = (
    "General",
    "Food & Drink",
    "Luxury",
    "Transit",
    "Access Passes",
    "Obsession Items",
    "Eclipse Items",
    "Foxy Delights Items",
    "Black Badge / Civic",
    "Collectibles",
    "Event Items",
)

ITEM_RARITIES = (
    "Common",
    "Uncommon",
    "Rare",
    "Luxury",
    "Restricted",
    "Exordium-Class",
)