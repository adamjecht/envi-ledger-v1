ENVI Ledger

ENVI Ledger is the economy-only Discord bot for the Exordium Nexus.

It manages Nexus Credits, citizen balances, shop purchases, inventories, item usage, transaction logs, and staff-facing economy reports.

Currency:

```text
₦C — Nexus Credits
````

---

## Current Version

```text
Version: V1.5 Ledger Polish
Status: Local development / testing
```

V1.5 expands the original economy system with item metadata, inventory upgrades, usable items, limited stock, economy statistics, and SIN News economy reporting.

---

## Core Citizen Commands

### `/balance`

View your current Nexus Credit balance.

### `/daily`

Claim your Civic Dividend.

### `/work`

Complete a Shift Assignment for Nexus Credits.

Current cooldown:

```text
4 hours
```

### `/pay`

Transfer Nexus Credits to another citizen.

### `/leaderboard`

View the top Nexus Credit holders.

---

## Commercial Exchange Commands

### `/shop`

View the ENVI Commercial Exchange.

Shop items display:

```text
Name
Price
Category
Rarity
Stock
Description
```

### `/shop category:`

Filter the shop by item category.

Current categories:

```text
General
Food & Drink
Luxury
Transit
Access Passes
Obsession Items
Eclipse Items
Foxy Delights Items
Black Badge / Civic
Collectibles
Event Items
```

### `/buy`

Purchase an item from the ENVI Commercial Exchange.

Limited-stock items reduce stock when purchased. Sold-out items cannot be bought.

### `/inventory`

View your owned items.

Inventory entries display:

```text
Quantity
Name
Category
Rarity
Use Status
Type
Description
```

### `/use`

Use an owned item from your inventory.

Usable item types:

```text
Consumable — removed from inventory after use
Permanent — remains in inventory after use
```

Non-usable items may be collectibles, decorative items, or staff-controlled RP assets.

---

## Item Metadata

V1.5 shop items may include:

```text
category
rarity
usable
consumable
use_message
stock
```

### Category

Used to organize the shop.

### Rarity

Current rarity values:

```text
Common
Uncommon
Rare
Luxury
Restricted
Exordium-Class
```

### Usable

Determines whether the item can be used with `/use`.

### Consumable

Determines whether using the item removes one quantity from inventory.

### Use Message

Custom message displayed when the item is used.

### Stock

Controls limited item availability.

```text
NULL / blank = Unlimited
0 = Sold Out
Positive number = Remaining stock
```

---

## Staff Commands

All staff commands are grouped under:

```text
/admin
```

### `/admin addcredits`

Add Nexus Credits to a citizen.

### `/admin removecredits`

Remove Nexus Credits from a citizen.

### `/admin setbalance`

Set a citizen balance.

### `/admin resetbalance`

Reset a citizen balance.

### `/admin additem`

Create a new shop item.

Supported metadata:

```text
name
price
description
category
rarity
stock
```

### `/admin edititem`

Edit an existing shop item.

Supported edits include:

```text
name
price
description
active status
category
rarity
stock
```

### `/admin removeitem`

Deactivate a shop item without deleting historical records.

### `/admin transactions`

View recent ENVI Ledger transactions for a citizen.

### `/admin status`

View bot maintenance and status information.

### `/admin economy`

View economy-wide statistics.

Includes:

```text
Total users
Credits in circulation
Highest balance
Credits generated
Credits removed
Net economy change
Shop purchases
Shop spending
Transfers
Transfer volume
Active shop items
Limited stock items
Sold out items
Total inventory quantity held by citizens
```

### `/admin economyreport`

Generate a SIN News Financial Pulse economy report.

Default behavior is private.

Use:

```text
public: True
```

to post the report publicly in the current channel.

---

## Logging

ENVI Ledger sends major economy activity to the configured staff log channel.

Logged activity includes:

```text
Admin credit actions
Shop item creation/editing/deactivation
Purchases
Transfers
Item use
Economy-relevant activity
```

The log channel is configured with:

```env
LOG_CHANNEL_ID=
```

---

## Environment Variables

Create a `.env` file with:

```env
DISCORD_TOKEN=
GUILD_ID=
ADMIN_ROLE_ID=
LOG_CHANNEL_ID=
```

For local testing, use a separate test bot and test server.

Do not use the live Railway bot token locally while Railway is running.

---

## Local Development

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the bot:

```powershell
python bot.py
```

Recommended local setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python bot.py
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

---

## Database

ENVI Ledger uses SQLite.

Default local database path:

```text
data/envi_ledger.db
```

Railway deployment uses a persistent volume mounted at:

```text
/app/data
```

Database setup runs automatically when the bot starts.

V1.5 migrations are handled by:

```text
services/migration_service.py
```

Current migrated shop fields:

```text
category
rarity
usable
consumable
use_message
stock
```

---

## Deployment Notes

The live bot is deployed on Railway.

Before deploying:

```powershell
python -m py_compile bot.py cogs\admin.py cogs\economy.py cogs\help.py services\*.py utils\*.py db\database.py
```

Then test locally with the test bot before pushing changes.

---

## V1 Scope

ENVI Ledger V1 focused on the basic economy system:

```text
Nexus Credits
User accounts
Balance
Daily claim
Work payout
Transfers
Shop
Purchases
Inventory
Leaderboard
Admin credit tools
Transaction logs
Persistent database
```

---

## V1.5 Scope

ENVI Ledger V1.5 adds:

```text
Shop categories
Item rarity
Improved shop display
Improved inventory display
Usable items
Consumable/permanent item behavior
Custom use messages
Limited stock
Stock-aware purchases
Admin economy statistics
SIN News economy report
Updated help and documentation
```

---

## Not In V1.5

These features are intentionally reserved for later versions:

```text
Businesses
Properties
Taxes
Loans
Crime
Gambling
Warrants
Black Badge fines
Faction banks
Influence
Job levels
Auctions
Item trading
Crafting
Dashboards
Automatic scheduled payouts
```

---

## Project Identity

ENVI Ledger is part of the Exordium Nexus civic infrastructure.

In-world framing:

```text
ENVI tracks the credits.
The Endless Reserve watches the flow.
Sin City remembers the receipt.
```

````