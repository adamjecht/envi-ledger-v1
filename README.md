\# ENVI Ledger



ENVI Ledger is a Discord economy bot built for the Exordium Nexus server.



It handles the server's v1 economy system using \*\*Nexus Credits\*\* (`₦C`), player balances, daily claims, work payouts, user transfers, shop items, inventories, admin tools, transaction records, staff log output, and basic maintenance tools.



This is the economy-only version of the larger ENVI system.



\---



\## Core Identity



\*\*Bot Name:\*\* ENVI Ledger  

\*\*Currency:\*\* Nexus Credits  

\*\*Currency Symbol:\*\* `₦C`  

\*\*Primary Purpose:\*\* Discord server economy management  

\*\*Database:\*\* SQLite  

\*\*Language:\*\* Python  

\*\*Discord Library:\*\* discord.py  



ENVI Ledger is designed as a civic financial system for the Exordium Nexus, not a general-purpose money bot.



\---



\## Current Version



```text

ENVI Ledger v1

````



v1 focuses only on the core economy.



It does not include businesses, taxes, property, banking, loans, crime systems, gambling, warrants, Black Badge fines, faction banks, crafting, auctions, or moderation tools.



\---



\## Completed Features



\### Public Economy Commands



```text

/ping

/balance

/daily

/work

/pay

/shop

/buy

/inventory

/leaderboard

/help

```



\### Admin Commands



```text

/admin status

/admin addcredits

/admin removecredits

/admin setbalance

/admin additem

/admin edititem

/admin removeitem

/admin transactions

/admin clearcooldowns

/admin resetuser

```



\### Systems



```text

SQLite database

Automatic user account creation

Nexus Credit balances

Daily reward cooldowns

Work payout cooldowns

User-to-user transfers

Shop item system

Inventory system

Transaction logging

Admin role gate

Staff log channel output

Global command error handling

Targeted cleanup / maintenance tools

```



\---



\## Project Structure



```text

envi-ledger/

├── bot.py

├── requirements.txt

├── README.md

├── .env

├── .env.example

├── .gitignore

│

├── data/

│   └── envi\_ledger.db

│

├── db/

│   ├── \_\_init\_\_.py

│   ├── schema.sql

│   └── database.py

│

├── cogs/

│   ├── \_\_init\_\_.py

│   ├── economy.py

│   ├── admin.py

│   └── help.py

│

├── services/

│   ├── \_\_init\_\_.py

│   ├── economy\_service.py

│   ├── transaction\_service.py

│   ├── cooldown\_service.py

│   ├── shop\_service.py

│   ├── inventory\_service.py

│   ├── log\_channel\_service.py

│   └── maintenance\_service.py

│

├── utils/

│   ├── \_\_init\_\_.py

│   ├── constants.py

│   ├── formatting.py

│   ├── embeds.py

│   ├── checks.py

│   └── responses.py

│

└── logs/

```



\---



\## Requirements



\* Python 3.11 or newer recommended

\* A Discord bot application

\* A Discord test server / guild

\* Bot token

\* Guild ID

\* Admin role ID

\* Staff log channel ID



Python packages:



```text

discord.py

python-dotenv

```



\---



\## Installation



Create and activate a virtual environment:



```powershell

python -m venv .venv

.\\.venv\\Scripts\\Activate.ps1

```



Install requirements:



```powershell

python -m pip install -r requirements.txt

```



\---



\## Environment Variables



Create a `.env` file in the project root.



Use this format:



```env

DISCORD\_TOKEN=your\_bot\_token\_here

GUILD\_ID=your\_discord\_server\_id\_here

ADMIN\_ROLE\_ID=your\_admin\_role\_id\_here

LOG\_CHANNEL\_ID=your\_staff\_log\_channel\_id\_here

```



Do not use quotes.



Do not add extra spaces.



Correct:



```env

GUILD\_ID=123456789012345678

```



Incorrect:



```env

GUILD\_ID="123456789012345678"

GUILD\_ID = 123456789012345678

```



\---



\## Important Security Notes



Never share your `.env` file.



Never post your bot token in Discord, GitHub, screenshots, or support chats.



If the token is exposed, reset it immediately in the Discord Developer Portal.



The `.gitignore` file should protect:



```text

.env

.venv/

\_\_pycache\_\_/

\*.pyc

data/\*.db

```



\---



\## Running the Bot



From the project root:



```powershell

python bot.py

```



Expected startup output:



```text

Synced 11 slash command(s) to guild ...

ENVI Ledger online as ...

```



Discord counts `/admin` as one top-level command group, even though it contains multiple subcommands.



\---



\## Database



ENVI Ledger uses SQLite.



Database file:



```text

data/envi\_ledger.db

```



Schema file:



```text

db/schema.sql

```



Tables:



```text

users

cooldowns

shop\_items

inventory

transactions

```



The database is automatically initialized when the bot starts.



Default shop items are automatically seeded when the bot starts.



\---



\## Public Commands



\### `/ping`



Checks whether ENVI Ledger is online.



\---



\### `/balance`



Shows your current Nexus Credit balance.



\---



\### `/daily`



Claims the Civic Dividend.



Default amount:



```text

₦C 500

```



Default cooldown:



```text

24 hours

```



\---



\### `/work`



Completes a Shift Assignment and pays a random amount.



Default payout range:



```text

₦C 150 - ₦C 500

```



Default cooldown:



```text

1 hour

```



\---



\### `/pay`



Transfers Nexus Credits to another user.



Rules:



```text

You cannot pay yourself.

Amount must be greater than 0.

Sender must have enough credits.

```



\---



\### `/shop`



Displays active shop items.



\---



\### `/buy`



Purchases an active shop item.



Rules:



```text

Item must exist.

Quantity must be greater than 0.

User must have enough credits.

Purchased items are added to inventory.

```



\---



\### `/inventory`



Displays owned shop items.



\---



\### `/leaderboard`



Displays the top Nexus Credit balances.



Default limit:



```text

Top 10

```



\---



\### `/help`



Displays the ENVI Ledger command directory.



\---



\## Admin Commands



Admin commands require the configured role from:



```env

ADMIN\_ROLE\_ID=

```



If the user does not have that role, ENVI denies access.



\---



\### `/admin status`



Checks whether the user has ENVI Ledger admin access.



\---



\### `/admin addcredits`



Adds Nexus Credits to a user.



Also logs:



```text

Database transaction

Staff log channel message

```



\---



\### `/admin removecredits`



Removes Nexus Credits from a user.



Rules:



```text

Amount must be greater than 0.

User must have enough credits.

Balance cannot go below 0.

```



Also logs:



```text

Database transaction

Staff log channel message

```



\---



\### `/admin setbalance`



Sets a user's balance to an exact amount.



Rules:



```text

Balance cannot be negative.

```



Also logs:



```text

Database transaction

Staff log channel message

```



\---



\### `/admin additem`



Creates a new active shop item.



Rules:



```text

Item name cannot be empty.

Price must be greater than 0.

Description cannot be empty.

Duplicate item names are blocked.

```



Also logs to the staff log channel.



\---



\### `/admin edititem`



Edits an existing shop item.



Can update:



```text

Name

Price

Description

Active status

```



Also logs to the staff log channel.



\---



\### `/admin removeitem`



Deactivates a shop item.



This does not permanently delete the item.



Reason:



```text

Old purchases and records should not break.

```



Also logs to the staff log channel.



\---



\### `/admin transactions`



Shows recent transaction records for one user.



Limit range:



```text

1 - 20

```



Discord blocks invalid limits before the command runs.



\---



\### `/admin clearcooldowns`



Clears a user's cooldown records.



Useful for testing:



```text

/daily

/work

```



Also logs to the staff log channel.



\---



\### `/admin resetuser`



Resets one user's test economy data.



Requires:



```text

confirm: True

```



Clears:



```text

Inventory

Cooldowns

Transaction history

```



Resets:



```text

Balance to ₦C 0

```



Then creates a fresh `ADMIN\_RESET` transaction record.



Also logs to the staff log channel.



This command does not wipe the entire server database.



\---



\## Staff Log Channel



Staff economy logs are sent to the channel configured by:



```env

LOG\_CHANNEL\_ID=

```



Logged events include:



```text

Player transfers

Shop purchases

Admin credit changes

Admin shop changes

Maintenance actions

Unexpected command errors

```



The bot needs these permissions in the log channel:



```text

View Channel

Send Messages

Embed Links

Read Message History

```



\---



\## Error Handling



ENVI Ledger has global slash command error handling.



If a command crashes unexpectedly, users should receive:



```text

ENVI COMMAND FAILURE

Reason: An unexpected system fault occurred. The incident has been logged.

```



The full traceback prints in PowerShell.



A short error summary is sent to the staff log channel.



\---



\## Testing Checklist



After setup, test these commands:



```text

/ping

/balance

/daily

/work

/pay

/shop

/buy

/inventory

/leaderboard

/help

```



Admin test:



```text

/admin status

/admin addcredits

/admin removecredits

/admin setbalance

/admin additem

/admin edititem

/admin removeitem

/admin transactions

/admin clearcooldowns

/admin resetuser

```



Also verify:



```text

Non-admin users are denied from /admin commands.

Staff logs appear in #envi-ledger-logs.

Cooldowns work.

Maintenance tools work.

Invalid transaction limits are blocked by Discord.

```



\---



\## Default Shop Items



The bot seeds default shop items on startup.



Current default examples include:



```text

Eclipse Drink Voucher

Obsession Perfume Sample

Foxy Delights Dessert Box

Black Cab Transit Pass

Velvet Obelisk Visitor Pass

Luxury Gift Box

```



Default shop items are inserted only if they do not already exist.



\---



\## V1 Limits



ENVI Ledger v1 does not include:



```text

Business ownership

Property ownership

Taxes

Loans

Interest

Bank accounts

Faction banks

Crime systems

Gambling

Warrants

Black Badge fines

Item trading

Crafting

Auctions

Moderation

Full web dashboard

Hosting automation

```



These can be considered later versions.



\---



\## Recommended Launch Prep



Before launch:



```text

1\. Confirm .env values are correct.

2\. Confirm the bot has the correct Discord permissions.

3\. Confirm the admin role works.

4\. Confirm #envi-ledger-logs receives log messages.

5\. Reset test users if needed.

6\. Remove junk test shop items.

7\. Run the final testing checklist.

8\. Back up the database if needed.

```



\---



\## Useful PowerShell Commands



Run bot:



```powershell

python bot.py

```



Compile all main files:



```powershell

python -m py\_compile bot.py cogs\\economy.py cogs\\admin.py cogs\\help.py services\\economy\_service.py services\\transaction\_service.py services\\cooldown\_service.py services\\shop\_service.py services\\inventory\_service.py services\\log\_channel\_service.py services\\maintenance\_service.py utils\\constants.py utils\\formatting.py utils\\embeds.py utils\\checks.py utils\\responses.py db\\database.py

```



Activate virtual environment:



```powershell

.\\.venv\\Scripts\\Activate.ps1

```



Install requirements:



```powershell

python -m pip install -r requirements.txt

```



\---



\## Final Note



ENVI Ledger v1 is meant to be stable, simple, and usable.



The goal is not to build every possible economy system at once.



The goal is to give the Exordium Nexus a working financial backbone first.



Database logs are the archive.



Staff channel logs are the watchtower.



ENVI remembers.



````

