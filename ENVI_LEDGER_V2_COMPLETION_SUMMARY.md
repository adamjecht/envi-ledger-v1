# ENVI Ledger V2 — Completion Summary

ENVI Ledger V2.0 is the completed second major release of the economy-only Discord bot for the **Exordium Nexus**.

# Institutions & Consequences

> Citizens earn. Businesses trade. Institutions pay. ENVI records. The Black Badge collects.

V2 expands ENVI Ledger from a citizen economy and shop into a civic economy containing organization accounts, institutional commerce, permanent financial ledgers, structured authority, and Black Badge consequences.

---

# Final Release Status

```text
Version: V2.0
Release Name: Institutions & Consequences
Release Tag: v2.0.0
Release Date: July 18, 2026
Status: Complete and live
Repository: adamjecht/envi-ledger-v1
Production Branch: main
Deployment Commit: abc9b6a318619f30d29827aea780335b5318b70b
Railway Service: envi-ledger-v1
Railway Deployment: 7deb6e07-c617-4b08-ad65-99d4893bc4db
Railway Region: sfo
Persistent Volume: /app/data
Production Database: /app/data/envi_ledger.db
```

The release was completed through six phases and 33 controlled implementation steps.

---

# V2 Foundation and Usability

V2 completed the usability work that had originally been planned for a cancelled V1.5.1 maintenance release.

Completed improvements:

```text
Item autocomplete
Compact paginated shop
Shop category filtering
/admin iteminfo
/admin restock
Improved /use guidance
Expanded Shift Assignment library
Expanded default shop catalog
```

Item autocomplete supports the appropriate public and administrative commands while respecting Discord's 25-result limit.

`/shop` is compact, filterable, paginated, user-locked, timeout-safe, and clearly identifies price, stock, category, rarity, seller, and settlement behavior.

`/use` now gives useful responses for unknown, unusable, unowned, consumable, and permanent items.

The Shift Assignment system now contains 120 Nexus-flavored work results.

---

# Organizations

V2 added a generalized organization framework supporting:

```text
BUSINESS
INSTITUTION
GOVERNMENT
```

`FACTION` remains reserved in the data model for possible future development but receives no dedicated faction gameplay in V2.

Organization roles:

```text
OWNER
MANAGER
MEMBER
```

Permission boundaries protect:

```text
Membership management
Organization role changes
Private organization balances
Deposits
Payments to citizens
Payments to organizations
Private organization ledgers
Administrative balance changes
Administrative revenue generation
```

Public organization commands include:

```text
/org info
/org balance
/org members
/org deposit
/org payuser
/org payorg
/org ledger
```

Administrative organization commands include:

```text
/admin org create
/admin org edit
/admin org deactivate
/admin org addmember
/admin org removemember
/admin org setrole
/admin org setbalance
/admin org revenue
```

Thirteen official Exordium Nexus organizations were seeded idempotently in production.

Deactivated organizations retain their identity, memberships, and transaction history.

---

# Organization Commerce

Shop items may reference an optional seller organization through `seller_org_id`.

V2 supports two purchase models:

```text
Commercial purchase — credits move from a citizen to a seller organization
System purchase — credits are removed from circulation
```

A commercial purchase atomically performs all required operations:

```text
Charge the citizen
Add the item to inventory
Reduce limited stock when applicable
Credit the seller organization
Record the citizen transaction
Record the organization sale
Link both records through one reference
Send a staff audit log
```

A failed commercial purchase rolls back the entire operation.

The production catalog contains 24 active shop items.

---

# Black Badge Citations

V2 added a permanent Black Badge citation ledger.

Citation statuses:

```text
OPEN
PAID
VOID
```

Citizen commands:

```text
/fines
/payfine
```

Administrative commands:

```text
/admin fine issue
/admin fine view
/admin fine void
/admin fine collect
```

Citation protections include:

```text
Unique Black Badge identifiers
No duplicate payment
No payment of void citations
No collection of paid citations
No partial payments
No negative balances
Required public reasons
Private administrative notes
Staff audit logging
Payment transaction linkage
```

Paid fines remove Nexus Credits from circulation. They do not become organization revenue.

---

# Reporting, Documentation, and Reliability

`/admin economy` and `/admin economyreport` now distinguish:

```text
Citizen balances
Organization balances
Total circulation
Generated organization revenue
Commercial shop circulation
System-shop sinks
Fine-payment sinks
Organization performance
Citation counts and values
Institutional payouts
```

V2 also completed:

```text
Updated /help documentation
Updated README documentation
Migration documentation
Transaction-type documentation
V2 staff-log formatting
Discord embed-limit enforcement
Mention suppression
Global command error handling
Logging-failure isolation
```

---

# Database Migrations

| Version | Migration | Purpose |
|---:|---|---|
| 150 | `verify_v1_5_item_schema` | Verifies V1.5 item metadata and stock fields |
| 200 | `create_v2_organization_schema` | Creates organizations, memberships, and organization ledgers |
| 210 | `add_v2_shop_seller_organization` | Links shop items to seller organizations |
| 220 | `create_v2_citation_schema` | Creates the Black Badge citation ledger |

All four migrations were applied exactly once during the live production deployment.

Existing V1.5 citizens, balances, cooldowns, inventory, shop records, and transactions were preserved.

---

# Live Production Verification

The live Railway deployment passed:

```text
Startup and migration verification
Slash-command synchronization
Public command smoke tests
Administrative command smoke tests
Organization directory tests
Shop pagination and filtering
Commercial seller display
Commercial purchase settlement
Seller organization settlement
Black Badge citation issuing
Citizen citation payment
Fine sink classification
Economy statistics
Private Financial Pulse generation
Staff audit logging
Private-note visibility protection
Database integrity checks
Foreign-key checks
```

The deployment remained online without unresolved tracebacks, interaction timeouts, missing tables, database locks, or foreign-key violations.

---

# Intentional Live Verification Records

Two controlled records were retained as valid production audit history.

## Commercial purchase

```text
Citizen: Maximillion / Miliana
Item: Civic Compliance Handbook — Revised Edition
Quantity: 1
Cost: ₦C 175
Seller: Nexus Civic Enforcement Directorate
Citizen Transaction: COMMERCIAL_SHOP_PURCHASE
Organization Transaction: SHOP_SALE
NCED Balance After Sale: ₦C 175
```

## Black Badge citation

```text
Citation: BB-000001
Amount: ₦C 25
Status: PAID
Payment Transaction: 304
Economic Treatment: Credits removed from circulation
Organization Revenue Created: None
```

The private administrative note remained restricted to staff views and never appeared in `/fines` or economy reporting.

---

# Verified Release-Time Production State

This is a fixed release checkpoint. Live counts may naturally change after release.

```text
Users: 13
Cooldowns: 26
Shop Items: 26
Active Shop Items: 24
Inventory Rows: 11
Citizen Transactions: 304
Organizations: 13
Active Organization Memberships: 0
Organization Transactions: 1
Citations: 1
Paid Citations: 1
Maximillion / Miliana Balance: ₦C 4,288
NCED Balance: ₦C 175
```

Database verification:

```text
PRAGMA integrity_check: ok
PRAGMA foreign_key_check: clean
Negative citizen balances: 0
Negative organization balances: 0
Duplicate inventory rows: 0
Duplicate citation payment links: 0
```

---

# Production Snapshots

## Pre-deployment V1.5 snapshot

```text
File: before_v2_live_deployment_2026-07-18_034821_UTC.db
Size: 81,920 bytes
SHA-256: 2caf9c0390b9cdc2d3b1667450f1a714d1ae60406b7e8b7724e207a05543bd40
```

## Migrated pre-write V2 snapshot

```text
File: before_v2_live_write_tests_2026-07-18_052349_UTC.db
Size: 188,416 bytes
SHA-256: e1a30c50c5856929eabc6f64703edd506281b51d1b53e9407d64db89f3b571ac
```

## Final verified V2 snapshot

```text
File: v2_live_verified_2026-07-18_063202_UTC.db
Size: 188,416 bytes
SHA-256: 454f6e0a2b04f0713dda7fc23646bcab51955f7935120083f827a3d6adfea67c
```

The final snapshot was downloaded byte-for-byte, validated locally, and accompanied by a checksum manifest.

---

# Deferred Follow-Up

One usability improvement was intentionally deferred:

```text
Admin-only organization balance inspection
```

Public `/org info` correctly omits private finances. `/org balance` correctly requires organization authorization. A future maintenance release may add an administrator inspection command without weakening those privacy boundaries.

---

# Scope Boundaries Preserved

V2 does not include:

```text
Loans
Interest
Taxes
Property
Rent
Gambling
Theft
Smuggling
Warrants
Bounties
Item trading
Auctions
Faction gameplay
Web dashboards
Passive organization income
Automatic fine escalation
Partial fine payments
```

These remain possible future releases rather than unfinished V2 work.

---

# Final Result

ENVI Ledger V2.0 is complete, tested, migrated, documented, backed up, and live on Railway.

The release establishes the institutional foundation required for future Exordium Nexus economy systems without sacrificing V1.5 data, financial traceability, permission boundaries, or database integrity.
