import sqlite3

from db.database import get_connection
from services.economy_service import utc_now
from utils.constants import (
    DEFAULT_ITEM_CONSUMABLE,
    DEFAULT_ITEM_RARITY,
    DEFAULT_ITEM_USABLE,
    DEFAULT_SHOP_CATEGORY,
    ITEM_RARITIES,
    SHOP_CATEGORIES,
)


DEFAULT_SHOP_ITEMS: tuple[
    dict[str, object],
    ...,
] = (
    {
        "name": "Eclipse Drink Voucher",
        "price": 250,
        "description": (
            "A voucher redeemable for one standard drink "
            "at Eclipse."
        ),
        "category": "Eclipse Items",
        "rarity": "Common",
        "usable": True,
        "consumable": True,
        "use_message": (
            "Voucher redeemed. Eclipse recognizes your "
            "indulgence. Please make poor choices "
            "responsibly."
        ),
        "stock": None,
        "seller_organization_name": "Eclipse",
    },
    {
        "name": "Obsession Perfume Sample",
        "price": 500,
        "description": (
            "A luxury fragrance sample from Maximillion's "
            "Obsession line."
        ),
        "category": "Obsession Items",
        "rarity": "Uncommon",
        "usable": True,
        "consumable": True,
        "use_message": (
            "Perfume sample applied. Obsession has made "
            "note of the version of you trying to surface."
        ),
        "stock": None,
        "seller_organization_name": "Obsession",
    },
    {
        "name": "Black Cab Transit Pass",
        "price": 400,
        "description": (
            "A short-distance private transit pass through "
            "Sin City."
        ),
        "category": "Transit",
        "rarity": "Common",
        "usable": True,
        "consumable": True,
        "use_message": (
            "Transit pass redeemed. Your route has been "
            "logged by ENVI. Comforting? No. Efficient? "
            "Yes."
        ),
        "stock": None,
        "seller_organization_name": None,
    },
    {
        "name": "Velvet Obelisk Visitor Pass",
        "price": 1500,
        "description": (
            "A limited visitor pass for approved Velvet "
            "Obelisk access."
        ),
        "category": "Access Passes",
        "rarity": "Rare",
        "usable": True,
        "consumable": False,
        "use_message": (
            "Visitor pass presented. Velvet Obelisk access "
            "credentials recognized. Behave like you were "
            "expensive to invite."
        ),
        "stock": None,
        "seller_organization_name": None,
    },
    {
        "name": "Luxury Gift Box",
        "price": 2000,
        "description": (
            "A premium social gift package for roleplay "
            "scenes."
        ),
        "category": "Luxury",
        "rarity": "Luxury",
        "usable": True,
        "consumable": True,
        "use_message": (
            "Luxury gift box opened. Someone either likes "
            "you, needs something from you, or both. "
            "Usually both."
        ),
        "stock": None,
        "seller_organization_name": None,
    },
    {
        "name": "After Dark Cocktail Flight",
        "price": 450,
        "description": (
            "A curated flight of three miniature Eclipse "
            "cocktails served beneath violet light."
        ),
        "category": "Eclipse Items",
        "rarity": "Uncommon",
        "usable": True,
        "consumable": True,
        "use_message": (
            "The flight is served beneath violet light. "
            "ENVI recommends making only two regrettable "
            "decisions tonight."
        ),
        "stock": None,
        "seller_organization_name": "Eclipse",
    },
    {
        "name": "Paradise’s Edge Guest Seal",
        "price": 2000,
        "description": (
            "A black-and-gold authenticated guest seal "
            "modeled after those issued for Eclipse's "
            "exclusive upper floor."
        ),
        "category": "Access Passes",
        "rarity": "Exordium-Class",
        "usable": True,
        "consumable": False,
        "use_message": (
            "The seal responds with a soft gold pulse. "
            "Paradise’s Edge recognizes the mark. "
            "Recognition is not the same as permission."
        ),
        "stock": 12,
        "seller_organization_name": "Eclipse",
    },
    {
        "name": "Obsession Identity Consultation",
        "price": 900,
        "description": (
            "A private Obsession consultation covering "
            "styling, fragrance, presentation, and curated "
            "personal transformation."
        ),
        "category": "Obsession Items",
        "rarity": "Rare",
        "usable": True,
        "consumable": True,
        "use_message": (
            "Your consultation has been accepted. "
            "Obsession will not ask who you are. It will "
            "ask who you intended to become."
        ),
        "stock": 30,
        "seller_organization_name": "Obsession",
    },
    {
        "name": "Gilded Indulgence Token",
        "price": 850,
        "description": (
            "A gold-edged service token accepted for one "
            "curated house indulgence at Forbidden Fruit."
        ),
        "category": "Luxury",
        "rarity": "Rare",
        "usable": True,
        "consumable": True,
        "use_message": (
            "The token disappears into velvet-gloved "
            "hands. Forbidden Fruit confirms that "
            "discretion has already been purchased."
        ),
        "stock": 30,
        "seller_organization_name": "Forbidden Fruit",
    },
    {
        "name": "Cobalt Inferno Reserve",
        "price": 700,
        "description": (
            "A rare blue-black spirit served with a faint "
            "crimson flame along the rim."
        ),
        "category": "Food & Drink",
        "rarity": "Rare",
        "usable": True,
        "consumable": True,
        "use_message": (
            "The reserve burns cold before turning warm. "
            "Inferno Lounge records that you handled it "
            "without embarrassing yourself."
        ),
        "stock": 28,
        "seller_organization_name": "Inferno Lounge",
    },
    {
        "name": "Pride’s Black-Glass Tumbler",
        "price": 1400,
        "description": (
            "A heavy obsidian-black tumbler with cobalt "
            "detailing and a discreet Inferno crest."
        ),
        "category": "Collectibles",
        "rarity": "Luxury",
        "usable": True,
        "consumable": False,
        "use_message": (
            "The glass catches the city lights without "
            "reflecting your flaws. Belial would consider "
            "that suspicious."
        ),
        "stock": 16,
        "seller_organization_name": "Inferno Lounge",
    },
    {
        "name": "Gilded Ledger Bond",
        "price": 1000,
        "description": (
            "A numbered decorative bond certificate issued "
            "by the Endless Reserve with no redeemable "
            "financial value."
        ),
        "category": "Collectibles",
        "rarity": "Rare",
        "usable": True,
        "consumable": False,
        "use_message": (
            "The bond authenticates successfully. It is "
            "worth exactly what someone wealthier can be "
            "convinced it is worth."
        ),
        "stock": 50,
        "seller_organization_name": "Endless Reserve",
    },
    {
        "name": "Endless Reserve Vault Key Replica",
        "price": 2500,
        "description": (
            "A weighted black-and-gold replica of an old "
            "Endless Reserve ceremonial vault key."
        ),
        "category": "Collectibles",
        "rarity": "Luxury",
        "usable": True,
        "consumable": False,
        "use_message": (
            "The key fits no public lock. ENVI notes that "
            "this has never stopped anyone ambitious."
        ),
        "stock": 10,
        "seller_organization_name": "Endless Reserve",
    },
    {
        "name": "Who Pissed Off Belial? Desk Mug",
        "price": 250,
        "description": (
            "A SIN News desk mug commemorating the "
            "network's least responsible recurring "
            "segment."
        ),
        "category": "Collectibles",
        "rarity": "Common",
        "usable": True,
        "consumable": False,
        "use_message": (
            "You take a measured sip. Today's answer "
            "remains under investigation."
        ),
        "stock": None,
        "seller_organization_name": "SIN News",
    },
    {
        "name": "Black Halo Benefit Ticket",
        "price": 1500,
        "description": (
            "An ENVI-authenticated admission ticket to the "
            "annual Black Halo Benefit."
        ),
        "category": "Event Items",
        "rarity": "Luxury",
        "usable": True,
        "consumable": True,
        "use_message": (
            "Admission authenticated. Formalwear is "
            "encouraged. Public disgrace remains optional."
        ),
        "stock": 25,
        "seller_organization_name": (
            "Obsidian Halo Entertainment"
        ),
    },
    {
        "name": "Fractured Halo Lightstick",
        "price": 950,
        "description": (
            "A black-chrome concert lightstick with violet "
            "illumination and a suspended fractured halo."
        ),
        "category": "Event Items",
        "rarity": "Rare",
        "usable": True,
        "consumable": False,
        "use_message": (
            "The fractured halo ignites in violet. Nearby "
            "VANTA//V fans immediately become louder."
        ),
        "stock": 30,
        "seller_organization_name": (
            "Obsidian Halo Entertainment"
        ),
    },
    {
        "name": "Saint Emiko Recovery Kit",
        "price": 350,
        "description": (
            "A sealed aftercare pack containing restorative "
            "tonic, sterile wraps, comfort patches, and "
            "supernatural-safe instructions."
        ),
        "category": "General",
        "rarity": "Common",
        "usable": True,
        "consumable": True,
        "use_message": (
            "Recovery protocol completed. Saint Emiko "
            "reminds you that surviving recklessness does "
            "not make it a treatment plan."
        ),
        "stock": None,
        "seller_organization_name": (
            "Saint Emiko Medical Complex"
        ),
    },
    {
        "name": "Sinlink Midnight Fare Token",
        "price": 200,
        "description": (
            "A single-use token valid for one late-night "
            "passage through the Sinlink transit system."
        ),
        "category": "Transit",
        "rarity": "Common",
        "usable": True,
        "consumable": True,
        "use_message": (
            "Fare accepted. Sinlink advises keeping your "
            "hands, belongings, and unresolved feuds inside "
            "the carriage."
        ),
        "stock": None,
        "seller_organization_name": (
            "Nexus Rail / Sinlink"
        ),
    },
    {
        "name": "Neon Route Map — Collector Edition",
        "price": 400,
        "description": (
            "A foldout black map of Sin City's rail network "
            "printed in reactive neon ink."
        ),
        "category": "Transit",
        "rarity": "Uncommon",
        "usable": True,
        "consumable": False,
        "use_message": (
            "The routes illuminate beneath your "
            "fingertips. Three stations appear that were "
            "not printed there before."
        ),
        "stock": None,
        "seller_organization_name": (
            "Nexus Rail / Sinlink"
        ),
    },
    {
        "name": "Sevenfold Civic Crest Challenge Coin",
        "price": 1100,
        "description": (
            "A heavy black-and-gold commemorative coin "
            "bearing the NCED's Sevenfold Civic Crest."
        ),
        "category": "Black Badge / Civic",
        "rarity": "Restricted",
        "usable": True,
        "consumable": False,
        "use_message": (
            "The crest catches a thin red light. Possession "
            "confirms nothing except that the NCED accepted "
            "your payment."
        ),
        "stock": 20,
        "seller_organization_name": (
            "Nexus Civic Enforcement Directorate"
        ),
    },
    {
        "name": "Civic Compliance Handbook — Revised Edition",
        "price": 175,
        "description": (
            "A thick guide to civic obligations, warrant "
            "etiquette, and avoiding unnecessary Hound "
            "Response attention."
        ),
        "category": "Black Badge / Civic",
        "rarity": "Common",
        "usable": True,
        "consumable": False,
        "use_message": (
            "You open the handbook. The first sentence "
            "reads: Ignorance of the mandate has been "
            "documented."
        ),
        "stock": None,
        "seller_organization_name": (
            "Nexus Civic Enforcement Directorate"
        ),
    },
    {
        "name": "Wax-Sealed Divination Candle",
        "price": 650,
        "description": (
            "A black hand-poured candle sealed in wine-red "
            "wax and prepared according to a private "
            "Gremlin's Brew divination ritual."
        ),
        "category": "Collectibles",
        "rarity": "Rare",
        "usable": True,
        "consumable": True,
        "use_message": (
            "The wax pools into a symbol you do not "
            "recognize. Gremlin's Brew does. It declines "
            "to explain."
        ),
        "stock": 24,
        "seller_organization_name": "Gremlin's Brew",
    },
    {
        "name": "Rooftop Garden Journal",
        "price": 400,
        "description": (
            "A soft clothbound journal with textured pages, "
            "a pressed-leaf bookmark, and the faint scent "
            "of old paper and rooftop soil."
        ),
        "category": "Collectibles",
        "rarity": "Uncommon",
        "usable": True,
        "consumable": False,
        "use_message": (
            "The journal opens to a clean page beneath the "
            "scent of paper and soil. The Cozy Tome "
            "considers silence a valid first draft."
        ),
        "stock": None,
        "seller_organization_name": "The Cozy Tome",
    },
    {
        "name": "Blossom-Wish Omamori",
        "price": 750,
        "description": (
            "A pale rose-and-ivory shrine charm containing "
            "a preserved sakura petal and space for one "
            "private wish."
        ),
        "category": "Collectibles",
        "rarity": "Rare",
        "usable": True,
        "consumable": False,
        "use_message": (
            "The charm warms beneath your fingers as petals "
            "stir without wind. The Sakura Shrine has heard "
            "the wish. Judgment was not requested."
        ),
        "stock": 30,
        "seller_organization_name": "Sakura Shrine",
    },
)


RETIRED_DEFAULT_SHOP_ITEMS = (
    "Foxy Delights Dessert Box",
)

SHOP_ITEM_SELECT = """
SELECT
    shop.item_id,
    shop.name,
    shop.price,
    shop.description,
    shop.category,
    shop.rarity,
    shop.usable,
    shop.consumable,
    shop.use_message,
    shop.stock,
    shop.seller_org_id,
    shop.active,
    shop.created_at,
    shop.updated_at,
    seller.name AS seller_org_name,
    seller.organization_type AS seller_org_type,
    seller.active AS seller_org_active
FROM shop_items AS shop
LEFT JOIN organizations AS seller
    ON seller.organization_id = shop.seller_org_id
"""


def validate_shop_category(category: str | None) -> str:
    """
    Validates and normalizes an item category.
    """

    if category is None:
        return DEFAULT_SHOP_CATEGORY

    clean_category = category.strip()

    if not clean_category:
        return DEFAULT_SHOP_CATEGORY

    if clean_category not in SHOP_CATEGORIES:
        valid_categories = ", ".join(SHOP_CATEGORIES)
        raise ValueError(f"Invalid category. Valid categories: {valid_categories}")

    return clean_category


def validate_item_rarity(rarity: str | None) -> str:
    """
    Validates and normalizes an item rarity.
    """

    if rarity is None:
        return DEFAULT_ITEM_RARITY

    clean_rarity = rarity.strip()

    if not clean_rarity:
        return DEFAULT_ITEM_RARITY

    if clean_rarity not in ITEM_RARITIES:
        valid_rarities = ", ".join(ITEM_RARITIES)
        raise ValueError(f"Invalid rarity. Valid rarities: {valid_rarities}")

    return clean_rarity


def normalize_bool(value: bool | None, default: bool) -> bool:
    """
    Normalizes optional boolean values.
    """

    if value is None:
        return default

    return bool(value)


def normalize_use_message(use_message: str | None) -> str | None:
    """
    Normalizes item use messages.

    Blank messages become None.
    """

    if use_message is None:
        return None

    clean_message = use_message.strip()

    if not clean_message:
        return None

    return clean_message


def normalize_stock(stock: int | None) -> int | None:
    """
    Normalizes stock values.

    None means unlimited stock.
    Any provided stock value must be 0 or greater.
    """

    if stock is None:
        return None

    if stock < 0:
        raise ValueError("Stock cannot be negative.")

    return stock


def validate_use_settings(
    usable: bool,
    consumable: bool,
    use_message: str | None,
) -> None:
    """
    Validates item use behavior.
    """

    if consumable and not usable:
        raise ValueError("Consumable items must also be usable.")

    if use_message is not None and not usable:
        raise ValueError("Items with a use message must also be usable.")

def _validate_seller_organization(
    connection: sqlite3.Connection,
    seller_org_id: int | None,
) -> dict | None:
    """
    Validates a newly selected shop seller.

    None represents the system-owned ENVI Commercial
    Exchange.

    Only active registered organizations may receive a new
    item assignment.
    """
    if seller_org_id is None:
        return None

    if (
        isinstance(seller_org_id, bool)
        or not isinstance(seller_org_id, int)
        or seller_org_id <= 0
    ):
        raise ValueError(
            "Seller organization ID must be a positive "
            "integer."
        )

    row = connection.execute(
        """
        SELECT
            organization_id,
            name,
            organization_type,
            active
        FROM organizations
        WHERE organization_id = ?
        """,
        (seller_org_id,),
    ).fetchone()

    if row is None:
        raise ValueError(
            "Selected seller organization is not registered."
        )

    if int(row["active"]) != 1:
        raise ValueError(
            "Inactive organizations cannot receive new "
            "shop-item assignments."
        )

    return dict(row)


def get_item_seller_mode(
    item: dict,
) -> str:
    """
    Returns the stored item-ownership mode.
    """
    if item.get("seller_org_id") is None:
        return "SYSTEM"

    return "ORGANIZATION"


def format_item_seller_name(
    item: dict,
) -> str:
    """
    Returns only the public-facing seller name.
    """
    if get_item_seller_mode(item) == "SYSTEM":
        return "ENVI Commercial Exchange"

    seller_org_id = item.get(
        "seller_org_id"
    )
    seller_name = item.get(
        "seller_org_name"
    )

    if (
        seller_name is not None
        and str(seller_name).strip()
    ):
        return str(seller_name).strip()

    return (
        f"Organization #{seller_org_id}"
        if seller_org_id is not None
        else "Unknown Organization"
    )


def format_item_seller(
    item: dict,
) -> str:
    """
    Formats complete seller metadata for staff output.
    """
    if get_item_seller_mode(item) == "SYSTEM":
        return (
            "ENVI Commercial Exchange "
            "(`System-Owned`)"
        )

    seller_org_id = item.get(
        "seller_org_id"
    )
    seller_name = format_item_seller_name(
        item
    )

    seller_status = (
        "Active"
        if int(
            item.get(
                "seller_org_active",
                0,
            )
        )
        == 1
        else "Inactive"
    )

    return (
        f"{seller_name} "
        f"(`Organization #{seller_org_id}`, "
        f"{seller_status})"
    )


def format_item_seller_mode(
    item: dict,
) -> str:
    """
    Formats ownership mode for public and staff displays.
    """
    if get_item_seller_mode(item) == "SYSTEM":
        return "System-Owned"

    return "Organization-Owned"


def format_item_purchase_status(
    item: dict,
) -> str:
    """
    Formats whether an active item can currently settle.

    System-owned items do not depend on an organization.
    """
    if get_item_seller_mode(item) == "SYSTEM":
        return "Available"

    if not item.get("seller_org_name"):
        return (
            "Unavailable — Seller Record Missing"
        )

    if int(
        item.get(
            "seller_org_active",
            0,
        )
    ) != 1:
        return (
            "Unavailable — Seller Inactive"
        )

    return "Available"


def format_item_settlement(
    item: dict,
) -> str:
    """
    Describes the item's purchase-settlement behavior.
    """
    if get_item_seller_mode(item) == "SYSTEM":
        return "System Exchange Credit Sink"

    return "Organization Commercial Revenue"

def format_stock(stock: int | None) -> str:
    """
    Formats stock for display.
    """

    if stock is None:
        return "Unlimited"

    if int(stock) == 0:
        return "Sold Out"

    return str(stock)

def decrease_item_stock(item_id: int, quantity: int) -> int | None:
    """
    Decreases stock for a limited-stock item.

    Returns None if the item has unlimited stock.
    Returns the remaining stock amount if the item has limited stock.
    """

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT stock
            FROM shop_items
            WHERE item_id = ? AND active = 1
            """,
            (item_id,),
        ).fetchone()

        if row is None:
            raise ValueError("Requested item is not registered in the active exchange.")

        current_stock = row["stock"]

        if current_stock is None:
            return None

        current_stock = int(current_stock)

        if current_stock <= 0:
            raise ValueError("Requested item is sold out.")

        if current_stock < quantity:
            raise ValueError(
                f"Requested quantity exceeds available stock. "
                f"Available stock: {current_stock}."
            )

        remaining_stock = current_stock - quantity

        connection.execute(
            """
            UPDATE shop_items
            SET stock = ?, updated_at = ?
            WHERE item_id = ?
            """,
            (remaining_stock, utc_now(), item_id),
        )

        connection.commit()

    return remaining_stock

def restock_limited_item(
    item_name: str,
    quantity: int,
) -> dict:
    """
    Adds stock to an existing limited-stock item.

    Active and inactive items may be restocked.
    Restocking does not change the item's active status.

    Returns the updated item along with:
    - old_stock
    - added_quantity
    - new_stock
    """

    clean_item_name = item_name.strip()

    if not clean_item_name:
        raise ValueError("Item name cannot be empty.")

    if quantity <= 0:
        raise ValueError("Restock quantity must be greater than zero.")

    with get_connection() as connection:
        item_row = connection.execute(
            """
            SELECT
                item_id,
                name,
                price,
                description,
                category,
                rarity,
                usable,
                consumable,
                use_message,
                stock,
                active
            FROM shop_items
            WHERE LOWER(name) = LOWER(?)
            """,
            (clean_item_name,),
        ).fetchone()

        if item_row is None:
            raise ValueError("Requested item is not registered.")

        if item_row["stock"] is None:
            raise ValueError(
                "Unlimited-stock items cannot be restocked."
            )

        old_stock = int(item_row["stock"])
        new_stock = old_stock + quantity

        connection.execute(
            """
            UPDATE shop_items
            SET
                stock = ?,
                updated_at = ?
            WHERE item_id = ?
            """,
            (
                new_stock,
                utc_now(),
                item_row["item_id"],
            ),
        )

        connection.commit()

        updated_row = connection.execute(
            """
            SELECT
                item_id,
                name,
                price,
                description,
                category,
                rarity,
                usable,
                consumable,
                use_message,
                stock,
                active
            FROM shop_items
            WHERE item_id = ?
            """,
            (item_row["item_id"],),
        ).fetchone()

    if updated_row is None:
        raise RuntimeError(
            "Item stock was updated, but the item could not be retrieved."
        )

    updated_item = dict(updated_row)

    updated_item["old_stock"] = old_stock
    updated_item["added_quantity"] = quantity
    updated_item["new_stock"] = new_stock

    return updated_item

def _get_default_seller_organization_id(
    connection: sqlite3.Connection,
    seller_organization_name: object,
) -> int | None:
    """
    Resolves one canonical default-item seller.

    None represents the system-owned ENVI Commercial
    Exchange.

    Inactive organizations remain valid stored sellers.
    Their items will display as unavailable until the
    organization is reactivated or the item is reassigned.
    """
    if seller_organization_name is None:
        return None

    if not isinstance(
        seller_organization_name,
        str,
    ):
        raise RuntimeError(
            "Default seller organization names must "
            "be text."
        )

    clean_name = (
        seller_organization_name.strip()
    )

    if not clean_name:
        raise RuntimeError(
            "Default seller organization names cannot "
            "be blank."
        )

    row = connection.execute(
        """
        SELECT
            organization_id,
            name,
            active
        FROM organizations
        WHERE name = ? COLLATE NOCASE
        """,
        (clean_name,),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            "Required default seller organization is "
            f"missing: {clean_name}."
        )

    return int(
        row["organization_id"]
    )

def seed_default_shop_items() -> dict:
    """
    Seeds the official 24-item Nexus catalog.

    Missing items are created with their complete metadata
    and canonical sellers.

    Existing items preserve:

    - Item IDs
    - Prices
    - Descriptions
    - Stock changes
    - Active or inactive status
    - Existing non-null seller assignments
    - Inventory ownership
    - Purchase history

    Legacy default metadata is upgraded only when it still
    uses the original generic values.

    Retired default items are deactivated rather than
    deleted.
    """
    now = utc_now()

    created_names: list[str] = []
    preserved_names: list[str] = []
    seller_assigned_names: list[str] = []
    retired_names: list[str] = []

    try:
        with get_connection() as connection:
            connection.execute(
                "BEGIN IMMEDIATE"
            )

            seller_ids: dict[
                object,
                int | None,
            ] = {}

            for item_definition in DEFAULT_SHOP_ITEMS:
                name = str(
                    item_definition["name"]
                )
                price = int(
                    item_definition["price"]
                )
                description = str(
                    item_definition["description"]
                )
                category = str(
                    item_definition["category"]
                )
                rarity = str(
                    item_definition["rarity"]
                )
                usable = bool(
                    item_definition["usable"]
                )
                consumable = bool(
                    item_definition["consumable"]
                )

                use_message_value = (
                    item_definition[
                        "use_message"
                    ]
                )
                use_message = (
                    str(use_message_value)
                    if use_message_value
                    is not None
                    else None
                )

                stock_value = item_definition[
                    "stock"
                ]
                stock = (
                    int(stock_value)
                    if stock_value is not None
                    else None
                )

                seller_name = item_definition[
                    "seller_organization_name"
                ]

                if seller_name not in seller_ids:
                    seller_ids[seller_name] = (
                        _get_default_seller_organization_id(
                            connection=connection,
                            seller_organization_name=(
                                seller_name
                            ),
                        )
                    )

                seller_org_id = seller_ids[
                    seller_name
                ]

                usable_value = (
                    1
                    if usable
                    else 0
                )
                consumable_value = (
                    1
                    if consumable
                    else 0
                )

                validate_shop_category(
                    category
                )
                validate_item_rarity(
                    rarity
                )
                validate_use_settings(
                    usable=usable,
                    consumable=consumable,
                    use_message=use_message,
                )
                normalize_stock(
                    stock
                )

                existing_row = connection.execute(
                    """
                    SELECT
                        item_id,
                        seller_org_id
                    FROM shop_items
                    WHERE name = ? COLLATE NOCASE
                    """,
                    (name,),
                ).fetchone()

                if existing_row is None:
                    connection.execute(
                        """
                        INSERT INTO shop_items (
                            name,
                            price,
                            description,
                            category,
                            rarity,
                            usable,
                            consumable,
                            use_message,
                            stock,
                            seller_org_id,
                            active,
                            created_at,
                            updated_at
                        )
                        VALUES (
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            1,
                            ?,
                            ?
                        )
                        """,
                        (
                            name,
                            price,
                            description,
                            category,
                            rarity,
                            usable_value,
                            consumable_value,
                            use_message,
                            stock,
                            seller_org_id,
                            now,
                            now,
                        ),
                    )

                    created_names.append(
                        name
                    )
                    continue

                preserved_names.append(
                    name
                )

                connection.execute(
                    """
                    UPDATE shop_items
                    SET
                        category = ?,
                        rarity = ?,
                        updated_at = ?
                    WHERE
                        item_id = ?
                        AND category = ?
                        AND rarity = ?
                    """,
                    (
                        category,
                        rarity,
                        now,
                        existing_row["item_id"],
                        DEFAULT_SHOP_CATEGORY,
                        DEFAULT_ITEM_RARITY,
                    ),
                )

                connection.execute(
                    """
                    UPDATE shop_items
                    SET
                        usable = ?,
                        consumable = ?,
                        use_message = ?,
                        updated_at = ?
                    WHERE
                        item_id = ?
                        AND usable = 0
                        AND consumable = 0
                        AND use_message IS NULL
                    """,
                    (
                        usable_value,
                        consumable_value,
                        use_message,
                        now,
                        existing_row["item_id"],
                    ),
                )

                if (
                    seller_org_id is not None
                    and existing_row[
                        "seller_org_id"
                    ]
                    is None
                ):
                    connection.execute(
                        """
                        UPDATE shop_items
                        SET
                            seller_org_id = ?,
                            updated_at = ?
                        WHERE item_id = ?
                        """,
                        (
                            seller_org_id,
                            now,
                            existing_row[
                                "item_id"
                            ],
                        ),
                    )

                    seller_assigned_names.append(
                        name
                    )

            for retired_name in (
                RETIRED_DEFAULT_SHOP_ITEMS
            ):
                retired_row = connection.execute(
                    """
                    SELECT
                        item_id,
                        active
                    FROM shop_items
                    WHERE name = ? COLLATE NOCASE
                    """,
                    (retired_name,),
                ).fetchone()

                if retired_row is None:
                    continue

                if int(
                    retired_row["active"]
                ) != 1:
                    continue

                connection.execute(
                    """
                    UPDATE shop_items
                    SET
                        active = 0,
                        updated_at = ?
                    WHERE item_id = ?
                    """,
                    (
                        now,
                        retired_row["item_id"],
                    ),
                )

                retired_names.append(
                    retired_name
                )

            connection.commit()

    except sqlite3.Error as error:
        raise RuntimeError(
            "The default shop catalog could not be seeded. "
            "No partial catalog changes were retained."
        ) from error

    result = {
        "total": len(
            DEFAULT_SHOP_ITEMS
        ),
        "created_count": len(
            created_names
        ),
        "preserved_count": len(
            preserved_names
        ),
        "seller_assigned_count": len(
            seller_assigned_names
        ),
        "retired_count": len(
            retired_names
        ),
        "created_names": tuple(
            created_names
        ),
        "preserved_names": tuple(
            preserved_names
        ),
        "seller_assigned_names": tuple(
            seller_assigned_names
        ),
        "retired_names": tuple(
            retired_names
        ),
    }

    print(
        "Default shop catalog ready: "
        f"{result['total']} active definitions, "
        f"{result['created_count']} created, "
        f"{result['preserved_count']} preserved, "
        f"{result['seller_assigned_count']} seller "
        "assignment(s) added, "
        f"{result['retired_count']} retired."
    )

    return result


def get_active_shop_items(
    category: str | None = None,
) -> list[dict]:
    """
    Returns all active shop items with seller metadata.

    If a category is provided, only active items in that
    category are returned.
    """
    with get_connection() as connection:
        if category is None:
            rows = connection.execute(
                f"""
                {SHOP_ITEM_SELECT}
                WHERE shop.active = 1
                ORDER BY
                    shop.price ASC,
                    shop.name ASC
                """
            ).fetchall()
        else:
            clean_category = validate_shop_category(
                category
            )

            rows = connection.execute(
                f"""
                {SHOP_ITEM_SELECT}
                WHERE
                    shop.active = 1
                    AND shop.category = ?
                ORDER BY
                    shop.price ASC,
                    shop.name ASC
                """,
                (clean_category,),
            ).fetchall()

    return [
        dict(row)
        for row in rows
    ]

def get_all_shop_items() -> list[dict]:
    """
    Returns every registered shop item with seller metadata.

    Active and inactive items are included so
    administrative commands can inspect, edit, or manage
    the complete item catalog.
    """
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            {SHOP_ITEM_SELECT}
            ORDER BY
                shop.active DESC,
                shop.name ASC
            """
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def get_shop_item_by_name(
    item_name: str,
) -> dict | None:
    """
    Finds an active shop item by name with seller metadata.

    Matching is case-insensitive.
    """
    with get_connection() as connection:
        row = connection.execute(
            f"""
            {SHOP_ITEM_SELECT}
            WHERE
                LOWER(shop.name) = LOWER(?)
                AND shop.active = 1
            """,
            (item_name,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def get_shop_item_by_id(
    item_id: int,
) -> dict | None:
    """
    Finds a shop item by ID with seller metadata.

    Active and inactive items are supported.
    """
    with get_connection() as connection:
        row = connection.execute(
            f"""
            {SHOP_ITEM_SELECT}
            WHERE shop.item_id = ?
            """,
            (item_id,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def get_shop_item_by_name_any_status(
    item_name: str,
) -> dict | None:
    """
    Finds a shop item by name with seller metadata.

    Active and inactive items are supported. Matching is
    case-insensitive.
    """
    with get_connection() as connection:
        row = connection.execute(
            f"""
            {SHOP_ITEM_SELECT}
            WHERE LOWER(shop.name) = LOWER(?)
            """,
            (item_name,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def create_shop_item(
    name: str,
    price: int,
    description: str,
    category: str | None = None,
    rarity: str | None = None,
    usable: bool | None = None,
    consumable: bool | None = None,
    use_message: str | None = None,
    stock: int | None = None,
    seller_org_id: int | None = None,
) -> dict:
    """
    Creates a new active shop item.

    A seller_org_id of None creates a system-owned item.
    Any organization seller must be registered and active.
    """
    clean_name = name.strip()
    clean_description = description.strip()
    clean_category = validate_shop_category(
        category
    )
    clean_rarity = validate_item_rarity(
        rarity
    )
    clean_usable = normalize_bool(
        usable,
        DEFAULT_ITEM_USABLE,
    )
    clean_consumable = normalize_bool(
        consumable,
        DEFAULT_ITEM_CONSUMABLE,
    )
    clean_use_message = normalize_use_message(
        use_message
    )
    clean_stock = normalize_stock(
        stock
    )

    validate_use_settings(
        usable=clean_usable,
        consumable=clean_consumable,
        use_message=clean_use_message,
    )

    if not clean_name:
        raise ValueError(
            "Item name cannot be empty."
        )

    if (
        isinstance(price, bool)
        or not isinstance(price, int)
        or price <= 0
    ):
        raise ValueError(
            "Price must be greater than zero."
        )

    if not clean_description:
        raise ValueError(
            "Item description cannot be empty."
        )

    existing_item = (
        get_shop_item_by_name_any_status(
            clean_name
        )
    )
    if existing_item is not None:
        raise ValueError(
            "An item with that name already exists."
        )

    now = utc_now()

    with get_connection() as connection:
        connection.execute(
            "BEGIN IMMEDIATE"
        )

        _validate_seller_organization(
            connection=connection,
            seller_org_id=seller_org_id,
        )

        cursor = connection.execute(
            """
            INSERT INTO shop_items (
                name,
                price,
                description,
                category,
                rarity,
                usable,
                consumable,
                use_message,
                stock,
                seller_org_id,
                active,
                created_at,
                updated_at
            )
            VALUES (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                1,
                ?,
                ?
            )
            """,
            (
                clean_name,
                price,
                clean_description,
                clean_category,
                clean_rarity,
                1 if clean_usable else 0,
                1 if clean_consumable else 0,
                clean_use_message,
                clean_stock,
                seller_org_id,
                now,
                now,
            ),
        )

        connection.commit()

    item_id = int(
        cursor.lastrowid
    )

    item = get_shop_item_by_id(
        item_id
    )

    if item is None:
        raise RuntimeError(
            "Shop item was created, but could not be "
            "retrieved."
        )

    return item


def update_shop_item(
    current_name: str,
    new_name: str | None = None,
    price: int | None = None,
    description: str | None = None,
    active: bool | None = None,
    category: str | None = None,
    rarity: str | None = None,
    usable: bool | None = None,
    consumable: bool | None = None,
    use_message: str | None = None,
    stock: int | None = None,
    seller_org_id: int | None = None,
    update_seller: bool = False,
) -> dict:
    """
    Updates an existing shop item.

    Any field left as None will stay unchanged.
    """

    item = get_shop_item_by_name_any_status(current_name.strip())

    if item is None:
        raise ValueError("Requested item is not registered.")

    updates = []
    values = []

    next_usable = bool(item["usable"])
    next_consumable = bool(item["consumable"])
    next_use_message = item["use_message"]

    if new_name is not None:
        clean_new_name = new_name.strip()

        if not clean_new_name:
            raise ValueError("New item name cannot be empty.")

        duplicate_item = get_shop_item_by_name_any_status(clean_new_name)

        if duplicate_item is not None and duplicate_item["item_id"] != item["item_id"]:
            raise ValueError("Another item already uses that name.")

        updates.append("name = ?")
        values.append(clean_new_name)

    if price is not None:
        if price <= 0:
            raise ValueError("Price must be greater than zero.")

        updates.append("price = ?")
        values.append(price)

    if description is not None:
        clean_description = description.strip()

        if not clean_description:
            raise ValueError("Description cannot be empty.")

        updates.append("description = ?")
        values.append(clean_description)

    if category is not None:
        clean_category = validate_shop_category(category)

        updates.append("category = ?")
        values.append(clean_category)

    if rarity is not None:
        clean_rarity = validate_item_rarity(rarity)

        updates.append("rarity = ?")
        values.append(clean_rarity)

    if usable is not None:
        next_usable = bool(usable)

    if consumable is not None:
        next_consumable = bool(consumable)

    if use_message is not None:
        next_use_message = normalize_use_message(use_message)

    validate_use_settings(
        usable=next_usable,
        consumable=next_consumable,
        use_message=next_use_message,
    )

    if usable is not None:
        updates.append("usable = ?")
        values.append(1 if next_usable else 0)

    if consumable is not None:
        updates.append("consumable = ?")
        values.append(1 if next_consumable else 0)

    if use_message is not None:
        updates.append("use_message = ?")
        values.append(next_use_message)

    if stock is not None:
        clean_stock = normalize_stock(stock)

        updates.append("stock = ?")
        values.append(clean_stock)

    if active is not None:
        updates.append("active = ?")
        values.append(1 if active else 0)

    with get_connection() as connection:
        connection.execute(
            "BEGIN IMMEDIATE"
        )

        if update_seller:
            _validate_seller_organization(
                connection=connection,
                seller_org_id=seller_org_id,
            )

            current_seller_org_id = item.get(
                "seller_org_id"
            )

            if (
                current_seller_org_id
                != seller_org_id
            ):
                updates.append(
                    "seller_org_id = ?"
                )
                values.append(
                    seller_org_id
                )

        if not updates:
            raise ValueError(
                "No item changes were provided."
            )

        updates.append(
            "updated_at = ?"
        )
        values.append(
            utc_now()
        )
        values.append(
            item["item_id"]
        )

        connection.execute(
            f"""
            UPDATE shop_items
            SET {", ".join(updates)}
            WHERE item_id = ?
            """,
            tuple(values),
        )

        connection.commit()

    updated_item = get_shop_item_by_id(item["item_id"])

    if updated_item is None:
        raise RuntimeError("Shop item was updated, but could not be retrieved.")

    return updated_item


def deactivate_shop_item(item_name: str) -> dict:
    """
    Deactivates a shop item instead of deleting it.
    """

    item = get_shop_item_by_name_any_status(item_name.strip())

    if item is None:
        raise ValueError("Requested item is not registered.")

    if int(item["active"]) == 0:
        raise ValueError("Requested item is already inactive.")

    updated_item = update_shop_item(
        current_name=item["name"],
        active=False,
    )

    return updated_item