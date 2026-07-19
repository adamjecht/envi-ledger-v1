# ENVI Ledger

ENVI Ledger is the economy-only Discord bot for the Exordium Nexus.

It manages Nexus Credits, citizen accounts, organizations, commercial purchases, inventories, Black Badge citations, transaction ledgers, staff auditing, and economy reporting.

```text
Currency: ₦C — Nexus Credits
```

## Current Release Status

```text
Version: V2.0 — Institutions & Consequences
Status: Stable release
Production: Live on Railway
Release Tag: v2.0.0
Released: July 18, 2026
```

Release thesis:

> Citizens earn. Businesses trade. Institutions pay. ENVI records. The Black Badge collects.

---

# Public Commands

## Citizen Economy

### `/ping`

Confirm that ENVI Ledger is online.

### `/balance`

View your own balance or another citizen’s registered balance.

### `/daily`

Claim the Civic Dividend.

### `/work`

Complete a Nexus Shift Assignment.

Current cooldown:

```text
4 hours
```

### `/pay`

Transfer Nexus Credits to another citizen.

### `/leaderboard`

View the leading citizen balances.

### `/help`

View the V2 command, permissions, and citation guide.

---

# Commercial Exchange and Inventory

### `/shop`

Opens the interactive ENVI Commercial Exchange storefront.

- Displays three items per page
- Supports category filtering and page navigation
- Shows item price, rarity, category, stock, seller, and settlement
- Shows the citizen’s available balance
- Allows immediate one-unit purchases
- Refreshes balance and stock after a purchase
- Sold-out goods remain visible but cannot be selected
- Shop sessions expire after five minutes

Use `/buy` for purchases involving multiple units.

### `/buy`

Purchase one or more copies of an active item.

The command supports item autocomplete, limited stock, sold-out protection, inventory updates, and atomic seller settlement.

### `/inventory`

View a citizen’s owned items and their metadata.

### `/use`

Use an eligible owned item.

Consumables lose one quantity after successful use. Permanent items remain in inventory. Invalid item names receive contextual guidance and suggestions.

---

# Black Badge Citations

### `/fines`

Privately review your OPEN citations and recent PAID or VOID history.

Private administrative notes are never displayed in the citizen view.

### `/payfine`

Pay one OPEN citation issued to your own account.

Rules:

```text
Only the cited citizen may pay
The full amount is required
Partial payment is not supported
The citizen balance cannot become negative
PAID citations cannot be paid again
VOID citations cannot be paid
Payment removes credits from circulation
```

Citation states:

```text
OPEN — unresolved and eligible for payment, collection, or voiding
PAID — resolved through citizen payment or administrative collection
VOID — cancelled by authorized staff
```

PAID and VOID are terminal states.

---

# Organizations

Organization types supported by V2:

```text
BUSINESS
INSTITUTION
GOVERNMENT
```

`FACTION` is reserved in the schema for future development.

## Public Organization Commands

### `/org info`

View an active organization’s public profile.

### `/org balance`

View an organization balance when your membership role permits it.

### `/org members`

View an organization roster when authorized.

### `/org deposit`

Deposit personal credits into an organization to which you belong.

### `/org payuser`

Pay a citizen from an organization account.

### `/org payorg`

Pay another active organization.

### `/org ledger`

Review private organization transaction history when authorized.

## Organization Roles

### `OWNER`

Owners have full organization authority, including financial commands and leadership control.

The final active owner cannot be accidentally removed or demoted.

### `MANAGER`

Managers may:

```text
Deposit funds
Pay citizens
Pay organizations
View private balances
View organization membership
View the private organization ledger
```

Managers cannot seize ownership or remove the final owner.

### `MEMBER`

Members may inspect permitted organization and membership information but cannot issue unrestricted organization payments.

Users outside an organization have no private organization access.

Inactive organizations and inactive memberships cannot authorize new financial activity.

---

# Administrative Commands

All staff commands require the configured ENVI Ledger administrator role.

## General Economy

### `/admin status`

Confirm administrator access.

### `/admin addcredits`

Create credits in a citizen account. A reason is required.

### `/admin removecredits`

Remove available credits from a citizen account. The balance cannot become negative.

### `/admin setbalance`

Set a citizen balance exactly. A reason is required.

### `/admin transactions`

Review recent personal transaction records.

### `/admin economy`

View the complete citizen, organization, commercial, citation, generation, removal, inventory, and reconciliation snapshot.

### `/admin economyreport`

Generate the SIN News Financial Pulse.

The report is private by default. Set `public: True` to post it in the current channel.

## Item Administration

### `/admin additem`

Create a shop item with complete metadata and an optional seller organization.

### `/admin edititem`

Edit an existing item while preserving purchase and ownership history.

### `/admin removeitem`

Deactivate an item without deleting historical records.

### `/admin iteminfo`

Inspect all item metadata, ownership, purchase, seller, stock, and settlement information.

### `/admin restock`

Add stock to a limited-stock item.

Unlimited items, zero quantities, and negative quantities are rejected.

## Maintenance

### `/admin clearcooldowns`

Clear a citizen’s daily and work cooldown records for controlled testing.

### `/admin resetuser`

Reset one citizen’s local/test economy data after explicit confirmation.

This is a destructive maintenance command and should not be used casually against production users.

## Organization Administration

### `/admin org create`

Create an organization.

### `/admin org edit`

Edit its name, type, or description while preserving history.

### `/admin org deactivate`

Block new organization activity without deleting balances, memberships, or transaction history.

### `/admin org reactivate`

Restore an inactive organization without changing its preserved financial history.

### `/admin org addmember`

Add or reactivate an organization member.

### `/admin org removemember`

Deactivate membership while preserving its historical record.

### `/admin org setrole`

Change an organization member’s role while enforcing final-owner protection.

### `/admin org revenue`

Create controlled organization revenue.

This is external credit generation and appears in economy statistics.

### `/admin org setbalance`

Set an organization balance exactly with a required audited reason.

## Black Badge Administration

### `/admin fine issue`

Issue an OPEN citation.

Issuing a citation does not immediately move credits.

### `/admin fine view`

Inspect the complete staff-facing citation record.

### `/admin fine void`

Permanently transition an OPEN citation to VOID.

Voiding does not alter the citizen balance.

### `/admin fine collect`

Collect an eligible OPEN citation from a citizen who holds the full amount.

Partial collection and negative balances are not allowed.

---

# Financial Settlement Model

ENVI Ledger separates external generation, external removal, and internal circulation.

## External Generation

```text
Daily rewards
Work rewards
Administrative citizen additions or positive corrections
Generated organization revenue
Positive organization balance corrections
```

## External Removal

```text
System-owned shop purchases
Administrative citizen removals or negative corrections
Fine payments
Administrative fine collections
Negative organization balance corrections
```

## Internal Circulation

```text
Citizen-to-citizen transfers
Citizen deposits into organizations
Organization payments to citizens
Organization-to-organization payments
Commercial purchases
Business shop-sale revenue
```

Internal circulation changes ownership but does not create or destroy currency.

---

# Staff Logs

Major activity is sent to the configured staff audit channel.

Examples include:

```text
Citizen credit changes
Transfers
System and commercial purchases
Item administration and use
Organization creation and editing
Membership changes
Organization deposits and payments
Organization revenue and balance corrections
Citation issue, void, payment, and collection
Unexpected command failures
```

Central log handling:

```text
Enforces Discord embed limits
Adds a timestamp
Uses V2 staff-audit branding
Suppresses user and role mentions
Does not crash completed commands when logging is unavailable
```

Configure the channel with:

```env
LOG_CHANNEL_ID=
```

---

# Error Handling

Expected validation failures receive command-specific guidance.

Unexpected failures receive:

```text
A safe public explanation
An incident reference
A sanitized staff-channel record
A full console traceback for development diagnosis
```

Raw database messages, table names, query fragments, filesystem details, and exception text are not posted to users or Discord staff logs.

---

# Database

ENVI Ledger uses SQLite.

Default local path:

```text
data/envi_ledger.db
```

Railway persistent-volume path:

```text
/app/data
```

Core tables:

```text
users
cooldowns
shop_items
inventory
transactions
organizations
organization_members
organization_transactions
citations
schema_migrations
```

Foreign keys are enabled on database connections.

---

# Migration History

Migrations are controlled by:

```text
services/migration_service.py
```

Current versions:

| Version | Migration | Purpose |
|---:|---|---|
| 150 | `verify_v1_5_item_schema` | Adds/verifies item metadata and stock fields |
| 200 | `create_v2_organization_schema` | Creates organizations, membership, and organization ledgers |
| 210 | `add_v2_shop_seller_organization` | Links shop items to optional seller organizations |
| 220 | `create_v2_citation_schema` | Creates the Black Badge citation ledger |

Migration behavior:

```text
Runs during startup
Records completed versions in schema_migrations
Skips already-applied versions
Rolls back a failed migration
Can be tested against disposable database copies
Preserves existing citizen, inventory, and transaction data
```

---

# Environment Variables

Create a `.env` file containing:

```env
DISCORD_TOKEN=
GUILD_ID=
ADMIN_ROLE_ID=
LOG_CHANNEL_ID=
```

Use a separate bot token and test server during local development.

Do not run the production Railway token locally while the Railway deployment is active.

---

# Local Development

Install dependencies:

```powershell
cd C:\Users\rober\Documents\envi-ledger
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
code .
python bot.py
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy `
    -Scope Process `
    -ExecutionPolicy Bypass

.\.venv\Scripts\Activate.ps1
```

Compile before testing:

```powershell
python -m py_compile bot.py
python -m py_compile cogs\admin.py
python -m py_compile cogs\economy.py
python -m py_compile cogs\organization.py
python -m py_compile cogs\help.py
python -m compileall -q .
```

---

# Deployment

ENVI Ledger V2.0 is live on Railway from the `main` branch.

```text
Release: V2.0 — Institutions & Consequences
Release Tag: v2.0.0
Deployment Commit: abc9b6a318619f30d29827aea780335b5318b70b
Railway Deployment: 7deb6e07-c617-4b08-ad65-99d4893bc4db
Service: envi-ledger-v1
Status: Online
Region: sfo
Persistent Volume: /app/data
Production Database: /app/data/envi_ledger.db
```

Production migrations applied:

```text
150 — verify_v1_5_item_schema
200 — create_v2_organization_schema
210 — add_v2_shop_seller_organization
220 — create_v2_citation_schema
```

Release verification completed successfully:

```text
V1.5 production data preserved
All four migrations applied exactly once
Organization framework verified
Commercial shop settlement verified
Black Badge citation payment verified
Economy reporting verified
Staff logging verified
Private citation notes remained private
Database integrity_check returned ok
Foreign-key integrity remained clean
Railway deployment remained online
```

Retained Railway snapshots:

```text
before_v2_live_deployment_2026-07-18_034821_UTC.db
before_v2_live_write_tests_2026-07-18_052349_UTC.db
v2_live_verified_2026-07-18_063202_UTC.db
```

Never remove or recreate the Railway persistent volume during a normal application deployment.

---

# V2 Scope

V2 adds:

```text
Item autocomplete
Paginated shop display
Expanded item inspection and restocking
Improved item-use guidance
Expanded Shift Assignments
Expanded organization-linked catalog
Organization accounts and roles
Organization deposits and payments
Organization ledgers
Commercial shop revenue
Controlled institutional revenue
Black Badge citations
Expanded economy reporting
V2 help, documentation, logs, and error handling
```

Explicitly outside V2:

```text
Loans
Interest
Taxes
Property and rent
Gambling
Theft and smuggling
Warrants and bounties
Partial fine payments
Automatic fine escalation
Automatic passive organization income
Item trading and gifting
Auctions
Faction gameplay
Web dashboards
```

---

# Project Identity

ENVI Ledger is part of the Exordium Nexus civic infrastructure.

```text
ENVI tracks the credits.
The Endless Reserve watches the flow.
Sin City remembers the receipt.
```