import random

import discord
from discord import app_commands
from discord.ext import commands

from services.cooldown_service import get_remaining_cooldown, set_cooldown
from services.citation_service import (
    get_citation_report,
    get_user_citations,
    pay_citation,
)
from services.economy_service import (
    add_credits,
    ensure_user,
    get_balance,
    get_top_balances,
    remove_credits,
)
from services.shop_service import (
    get_shop_item_by_id,
    format_item_purchase_status,
    format_item_seller,
    format_item_seller_mode,
    format_item_settlement,
    format_stock,
    get_active_shop_items,
)
from services.inventory_service import (
    decrease_item_quantity,
    get_user_inventory,
    get_user_inventory_item_by_name,
)
from services.item_use_guidance_service import (
    build_non_usable_item_reason,
    build_unknown_item_use_reason,
)
from services.purchase_service import (
    purchase_shop_item,
)
from services.log_channel_service import send_ledger_log
from services.transaction_service import log_transaction
from utils.constants import (
    CITATION_STATUS_OPEN,
    DAILY_AMOUNT,
    DAILY_COOLDOWN_SECONDS,
    LEADERBOARD_LIMIT,
    SHOP_CATEGORIES,
    TRANSACTION_DAILY,
    TRANSACTION_TRANSFER_RECEIVED,
    TRANSACTION_TRANSFER_SENT,
    TRANSACTION_WORK,
    WORK_COOLDOWN_SECONDS,
    WORK_MAX_AMOUNT,
    WORK_MIN_AMOUNT,
)
from utils.embeds import envi_embed, envi_error
from utils.autocomplete import (
    buy_item_autocomplete,
    use_item_autocomplete,
)
from utils.formatting import format_credits, format_seconds
from utils.citation_pagination import (
    CitationPaginationView,
    RECENT_CITATION_HISTORY_LIMIT,
)
from utils.shop_pagination import ShopPaginationView
from utils.shop_components import ShopComponentsView
from utils.work_assignments import ADDITIONAL_WORK_ASSIGNMENTS


class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="balance",
        description="View your ENVI Ledger balance.",
    )
    async def balance(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ):
        target_user = user or interaction.user

        ensure_user(
            user_id=target_user.id,
            display_name=target_user.display_name,
        )

        balance_amount = get_balance(target_user.id)

        embed = envi_embed(
            title="ENVI FINANCIAL SUMMARY",
            description=(
                f"Citizen: {target_user.mention}\n"
                f"Available Balance: **{format_credits(balance_amount)}**\n"
                f"Account Status: **Active**"
            ),
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="fines",
        description=(
            "View your Black Badge citations."
        ),
    )
    async def fines(
        self,
        interaction: discord.Interaction,
    ):
        user = interaction.user

        ensure_user(
            user_id=user.id,
            display_name=user.display_name,
        )

        open_citations = get_user_citations(
            user_id=user.id,
            status=CITATION_STATUS_OPEN,
        )

        all_citations = get_user_citations(
            user_id=user.id,
        )

        recent_history = [
            citation
            for citation in all_citations
            if (
                str(
                    citation["status"]
                )
                != CITATION_STATUS_OPEN
            )
        ][
            :RECENT_CITATION_HISTORY_LIMIT
        ]

        report = get_citation_report(
            user_id=user.id
        )

        if (
            not open_citations
            and not recent_history
        ):
            embed = envi_embed(
                title=(
                    "BLACK BADGE CITATION RECORD"
                ),
                description=(
                    f"Citizen: {user.mention}\n\n"
                    "No Black Badge citations are "
                    "registered to this account."
                ),
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        view = CitationPaginationView(
            open_citations=open_citations,
            recent_history=recent_history,
            report=report,
            user_id=user.id,
        )

        await interaction.response.send_message(
            embed=view.build_embed(),
            view=view,
            ephemeral=True,
        )

        view.message = (
            await interaction.original_response()
        )

    @app_commands.command(
        name="payfine",
        description=(
            "Pay one OPEN Black Badge citation."
        ),
    )
    @app_commands.describe(
        citation_identifier=(
            "Your citation ID, such as BB-000001."
        ),
    )
    async def payfine(
        self,
        interaction: discord.Interaction,
        citation_identifier: str,
    ):
        user = interaction.user

        ensure_user(
            user_id=user.id,
            display_name=user.display_name,
        )

        await interaction.response.defer(
            ephemeral=True
        )

        try:
            result = pay_citation(
                user_id=user.id,
                citation_identifier=(
                    citation_identifier
                ),
            )

        except (
            ValueError,
            RuntimeError,
        ) as error:
            embed = envi_error(
                title=(
                    "BLACK BADGE PAYMENT DENIED"
                ),
                reason=str(error),
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True,
            )
            return

        citation = result["citation"]
        transaction = result["transaction"]

        await send_ledger_log(
            bot=interaction.client,
            title=(
                "BLACK BADGE FINE PAYMENT LOG"
            ),
            description=(
                "Type: "
                f"`{transaction['type']}`\n"
                "Citation: "
                f"`{citation['citation_identifier']}`\n"
                f"Citizen: {user.mention}\n"
                f"Citizen ID: `{user.id}`\n"
                "Issuer: "
                f"**{citation['issuer_display_name']}**\n"
                "Citation Amount: "
                f"**{format_credits(result['amount'])}**\n"
                "Previous Balance: "
                f"**{format_credits(result['balance_before'])}**\n"
                "Updated Balance: "
                f"**{format_credits(result['user']['balance'])}**\n"
                "Payment Transaction ID: "
                f"`{transaction['transaction_id']}`\n"
                "Previous Status: **OPEN**\n"
                "Updated Status: **PAID**\n"
                "Economic Treatment: "
                "`Credits Removed from Circulation`\n"
                "Citation Reason: "
                f"{citation['reason']}"
            ),
        )

        embed = envi_embed(
            title=(
                "BLACK BADGE CITATION PAID"
            ),
            description=(
                "Citation: "
                f"`{citation['citation_identifier']}`\n"
                "Status: **PAID**\n"
                "Amount Paid: "
                f"**{format_credits(result['amount'])}**\n"
                "Previous Balance: "
                f"**{format_credits(result['balance_before'])}**\n"
                "Updated Balance: "
                f"**{format_credits(result['user']['balance'])}**\n"
                "Payment Transaction: "
                f"`{transaction['transaction_id']}`\n\n"
                "**Citation Reason**\n"
                f"{citation['reason']}\n\n"
                "_Payment was processed in full. "
                "The removed credits did not transfer "
                "to another citizen or organization._"
            ),
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )

    @app_commands.command(
        name="daily",
        description="Claim your daily Civic Dividend.",
    )
    async def daily(self, interaction: discord.Interaction):
        user = interaction.user

        ensure_user(
            user_id=user.id,
            display_name=user.display_name,
        )

        remaining_seconds = get_remaining_cooldown(
            user_id=user.id,
            command_name="daily",
            cooldown_seconds=DAILY_COOLDOWN_SECONDS,
        )

        if remaining_seconds > 0:
            embed = envi_error(
                title="ENVI CIVIC DIVIDEND DENIED",
                reason=(
                    "Civic Dividend has already been processed. "
                    f"Next claim available in **{format_seconds(remaining_seconds)}**."
                ),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        new_balance = add_credits(user.id, DAILY_AMOUNT)

        log_transaction(
            user_id=user.id,
            transaction_type=TRANSACTION_DAILY,
            amount=DAILY_AMOUNT,
            reason="Daily Civic Dividend processed.",
        )

        set_cooldown(
            user_id=user.id,
            command_name="daily",
        )

        embed = envi_embed(
            title="ENVI CIVIC DIVIDEND PROCESSED",
            description=(
                f"Citizen: {user.mention}\n"
                f"Deposit: **{format_credits(DAILY_AMOUNT)}**\n"
                f"Updated Balance: **{format_credits(new_balance)}**\n"
                "Next claim available in **24h**."
            ),
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="work",
        description="Complete a Nexus Shift Assignment for credits.",
    )
    async def work(self, interaction: discord.Interaction):
        user = interaction.user

        ensure_user(
            user_id=user.id,
            display_name=user.display_name,
        )

        remaining_seconds = get_remaining_cooldown(
            user_id=user.id,
            command_name="work",
            cooldown_seconds=WORK_COOLDOWN_SECONDS,
        )

        if remaining_seconds > 0:
            embed = envi_error(
                title="ENVI SHIFT ASSIGNMENT DENIED",
                reason=(
                    "Shift Assignment access is currently cooling down. "
                    f"Next assignment available in **{format_seconds(remaining_seconds)}**."
                ),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        assignments = [
            "You completed a service shift at Eclipse. ENVI logged elevated bass levels and questionable decision-making.",
            "You processed inventory for Obsession. ENVI detected several items being purchased for reasons customers refused to admit.",
            "You delivered sealed documents through the Luxuria District. ENVI confirmed the seals were intact and your curiosity was poorly hidden.",
            "You assisted with guest intake at Elysium Noir. ENVI noted that three guests lied elegantly and one lied poorly.",
            "You catalogued rare arrivals at The Cozy Tome. ENVI flagged two books for movement without permission.",
            "You filed civic receipts through an ENVI terminal. ENVI accepted your paperwork with minimal disappointment.",
            "You cleaned up a suspicious spill near Sinlink. ENVI classified the substance as non-lethal, probably.",
            "You escorted a nervous courier through Gutterlight. ENVI noted the courier became less nervous after you became more nervous.",
            "You sorted late-night order slips at Afterglow Diner. ENVI detected grease, exhaustion, and civic resilience.",
            "You verified guest manifests for Hotel Seraphine. ENVI found one alias, two scandals, and no desire to elaborate.",
            "You sorted Black Badge citations into 'paid,' 'ignored,' and 'politically inconvenient.'",
            "You cleaned glitter, blood, and someone’s ego off the Eclipse floor. ENVI refuses to rank them by toxicity.",
            "You delivered a cursed package across Sinlink. It hummed twice. You pretended that was normal.",
            "You helped SIN News edit a report until the truth became legally attractive.",
            "You restocked Inferno Lounge napkins after Belial allegedly terrified someone into spilling a drink. Allegedly.",
            "You assisted with a private Obsession fitting. The mirror asked better questions than the client did.",
            "You delivered velvet-sealed invitations to Eclipse’s upper floor. Several guests suddenly remembered how to behave.",
            "You helped prepare an Obsession fragrance display. ENVI detected elevated heart rates and approved the layout.",
            "You escorted VIPs through Paradise’s Edge, where the lighting was soft and the consequences were not.",
            "You handled silk, perfume, and confidential measurements at the Obsession Showroom. Professionalism barely survived.",
            "You reconciled luxury invoices at the Endless Reserve. Every number looked hungry.",
            "You updated ENVI civic records inside the Velvet Obelisk. ENVI noted your unusual compliance.",
            "You carried sealed paperwork from Scarlet Atelier to Ambrosia Hall without asking why it was warm.",
            "You helped reset access permissions for a restricted Luxuria Complex elevator.",
            "You logged suspicious transit delays on Sinlink. Three were mechanical. One was probably a demon.",
            "You assisted with guest registration at Hotel Seraphine and learned that diplomacy smells expensive.",
            "You filed medical debt forms at Saint Emiko Medical Complex. Mercy remains billable.",
            "You delivered a discreet envelope to Elysium Noir and were smart enough not to read it.",
            "You helped archive SIN News footage that officially never existed.",
            "You performed inventory checks for Obsession packaging: black boxes, gold foil, crimson tissue, zero innocence.",
            "You ran a courier route through Gutterlight and came back with all your limbs and most of your dignity.",
            "You helped verify vault receipts at Endless Reserve. The vault blinked. You did not.",
            "You assisted with crowd flow near Eclipse before the bass swallowed the block.",
            "You checked ENVI access pings around Edenveil Gardens and found one camera politely refusing to work.",
            "You delivered a maintenance report to the Velvet Vista observation deck and tried not to stare at the city judging you.",
            "Patriarch Maximillion assigned you to audit Obsession’s private client ledgers. Several purchases were emotional confessions with invoices attached.",
            "Patriarch Maximillion requested your assistance at the Velvet Obelisk. You carried sealed documents and learned that silence is part of the uniform.",
            "Patriarch Maximillion sent you to inspect Eclipse’s upper floor before opening. The lights behaved. The guests probably will not.",
            "Patriarch Maximillion ordered a refinement sweep through the Luxuria Complex. Every mirror was polished until it looked judgmental.",
            "Patriarch Maximillion had you prepare VIP access records for Paradise’s Edge. ENVI flagged three guests as desperate and one as entertaining.",
            "Lucifer assigned you to review old Eden Afterlife records. Some names were crossed out. Others crossed themselves out.",
            "Lucifer requested a legacy archive delivery to the Velvet Obelisk. The package felt older than the city and twice as patient.",
            "Lucifer sent you to Edenveil Gardens to inspect a memorial seal. For once, the city was quiet enough to hear itself breathe.",
            "Lucifer asked you to recover a misplaced family document. It was not lost. It was waiting to be respected.",
            "Lucifer assigned you to clean up an old sanctuary chamber beneath the Nexus. Some dust is history. Some dust watches back.",
            "Lucifer assigned you to bring Nyxeria ice cream. She hugged you instead. Lucifer is still waiting for his hug.",
            "Lucifer requested you give Nyxeria an allowance. She immediately spent it on snacks.",
            "Lucifer assigned you to make sure Nyxeria had dinner. She thanked you. Lucifer received no acknowledgment.",
            "Lucifer instructed you to check on Nyxeria. She adopted you for the afternoon.",
            "Lucifer assigned you to remind Maximillion to eat lunch. He replied, “After this one thing.” He has said that six times today.",
            "Lucifer requested you confiscate Maximillion’s paperwork. He somehow produced more.",
            "Lucifer assigned you to ask Amanei how her day was. She stared at you until the shift ended.",
            "Lucifer requested you tell Amanei a joke. She asked you to explain why it was supposed to be funny.",
            "Lucifer assigned you to follow Xenimus and repair everything he accidentally broke. Overtime has been approved.",
            "Lucifer assigned you to supervise Kori. You quickly realized the assignment was impossible.",
            "Lucifer assigned you to keep Kori out of trouble. You submitted your resignation halfway through the shift.",
            "Lucifer assigned you to help Kori interrogate a suspect. You now require therapy.",
            "Lucifer assigned you to remind Kori that not every inconvenience requires a body count. He disagreed.",
            "Ximena wanted to hire a few new joytoys. Asks for your help conducting the interviews. You spend several hours fucking the new joytoys and indulged in a pleasurable evening.",
            "Ximena needed assistance with testing some new equipment for the VIP rooms. You unlocked a new kink. You are officially into feet.",
        ]

        assignments.extend(ADDITIONAL_WORK_ASSIGNMENTS)

        assignment = random.choice(assignments)
        payout = random.randint(WORK_MIN_AMOUNT, WORK_MAX_AMOUNT)

        new_balance = add_credits(user.id, payout)

        log_transaction(
            user_id=user.id,
            transaction_type=TRANSACTION_WORK,
            amount=payout,
            reason=assignment,
        )

        set_cooldown(
            user_id=user.id,
            command_name="work",
        )

        embed = envi_embed(
            title="ENVI SHIFT ASSIGNMENT COMPLETE",
            description=(
                f"Citizen: {user.mention}\n"
                f"Assignment: **{assignment}**\n"
                f"Compensation: **{format_credits(payout)}**\n"
                f"Updated Balance: **{format_credits(new_balance)}**\n"
                "Next assignment available in **4h**."
            ),
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="pay",
        description="Transfer Nexus Credits to another citizen.",
    )
    async def pay(
        self,
        interaction: discord.Interaction,
        recipient: discord.Member,
        amount: int,
    ):
        sender = interaction.user

        ensure_user(
            user_id=sender.id,
            display_name=sender.display_name,
        )

        ensure_user(
            user_id=recipient.id,
            display_name=recipient.display_name,
        )

        if recipient.id == sender.id:
            embed = envi_error(
                title="ENVI CREDIT TRANSFER DENIED",
                reason="Sender and recipient cannot be the same citizen.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if amount <= 0:
            embed = envi_error(
                title="ENVI CREDIT TRANSFER DENIED",
                reason="Transfer amount must be greater than zero.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            sender_new_balance = remove_credits(sender.id, amount)
        except ValueError as error:
            embed = envi_error(
                title="ENVI CREDIT TRANSFER DENIED",
                reason=str(error),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        recipient_new_balance = add_credits(recipient.id, amount)

        log_transaction(
            user_id=sender.id,
            target_user_id=recipient.id,
            transaction_type=TRANSACTION_TRANSFER_SENT,
            amount=-amount,
            reason=f"Credit transfer sent to {recipient.display_name}.",
        )

        log_transaction(
            user_id=recipient.id,
            target_user_id=sender.id,
            transaction_type=TRANSACTION_TRANSFER_RECEIVED,
            amount=amount,
            reason=f"Credit transfer received from {sender.display_name}.",
        )

        await send_ledger_log(
            bot=interaction.client,
            title="ENVI LEDGER TRANSFER LOG",
            description=(
                f"Type: `{TRANSACTION_TRANSFER_SENT}` / `{TRANSACTION_TRANSFER_RECEIVED}`\n"
                f"Sender: {sender.mention}\n"
                f"Recipient: {recipient.mention}\n"
                f"Amount: **{format_credits(amount)}**\n"
                f"Sender Updated Balance: **{format_credits(sender_new_balance)}**"
            ),
        )

        embed = envi_embed(
            title="ENVI CREDIT TRANSFER COMPLETE",
            description=(
                f"Sender: {sender.mention}\n"
                f"Recipient: {recipient.mention}\n"
                f"Amount: **{format_credits(amount)}**\n"
                f"Sender Updated Balance: **{format_credits(sender_new_balance)}**"
            ),
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="shop",
        description=(
            "Browse and purchase goods from the "
            "ENVI Commercial Exchange."
        ),
    )
    async def shop(
        self,
        interaction: discord.Interaction,
    ):
        user = interaction.user

        ensure_user(
            user_id=user.id,
            display_name=user.display_name,
        )

        items = get_active_shop_items()

        if not items:
            embed = envi_error(
                title="ENVI COMMERCIAL EXCHANGE UNAVAILABLE",
                reason=(
                    "No active shop items are currently "
                    "registered."
                ),
            )
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        bot_user = interaction.client.user

        if bot_user is None:
            embed = envi_error(
                title="ENVI COMMERCIAL EXCHANGE UNAVAILABLE",
                reason=(
                    "The ENVI bot identity could not be "
                    "resolved."
                ),
            )
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        view = ShopComponentsView(
            items=items,
            user_id=user.id,
            balance=get_balance(user.id),
            thumbnail_url=str(
                bot_user.display_avatar.url
            ),
            purchase_callback=(
                self._purchase_shop_view_item
            ),
        )

        await interaction.response.send_message(
            view=view,
            ephemeral=True,
            allowed_mentions=(
                discord.AllowedMentions.none()
            ),
        )

        view.message = (
            await interaction.original_response()
        )


    @app_commands.command(
        name="buy",
        description=(
            "Purchase an item from the "
            "ENVI Commercial Exchange."
        ),
    )
    @app_commands.describe(
        item_name=(
            "Start typing the name of an "
            "available shop item."
        ),
        quantity=(
            "How many copies of the item "
            "you want to purchase."
        ),
    )
    @app_commands.autocomplete(
        item_name=buy_item_autocomplete,
    )
    async def buy(
        self,
        interaction: discord.Interaction,
        item_name: str,
        quantity: int = 1,
    ):
        await interaction.response.defer()

        user = interaction.user

        try:
            result = await self._execute_shop_purchase(
                interaction=interaction,
                item_name=item_name,
                quantity=quantity,
            )
        except (ValueError, RuntimeError) as error:
            embed = envi_error(
                title="ENVI PURCHASE DENIED",
                reason=str(error),
            )
            await interaction.followup.send(
                embed=embed,
                ephemeral=True,
            )
            return

        item = result["item"]

        seller_text = format_item_seller(item)
        seller_mode = format_item_seller_mode(item)
        settlement_type = format_item_settlement(
            item
        )
        remaining_stock_text = format_stock(
            result["remaining_stock"]
        )

        embed = envi_embed(
            title="ENVI PURCHASE CONFIRMED",
            description=(
                f"Citizen: {user.mention}\n"
                f"Item: **{item['name']}**\n"
                f"Seller: **{seller_text}**\n"
                f"Purchase Type: **{seller_mode}**\n"
                f"Settlement: **{settlement_type}**\n"
                f"Category: `{item['category']}`"
                f" | Rarity: `{item['rarity']}`\n"
                f"Quantity: **{result['quantity']}**\n"
                f"Total: **{format_credits(result['total_price'])}**\n"
                f"Stock Remaining: **{remaining_stock_text}**\n"
                "Inventory Quantity: "
                f"**{result['inventory_quantity']}**\n"
                "Updated Balance: "
                f"**{format_credits(result['user']['balance'])}**\n"
                f"Reference: `{result['reference_id']}`"
            ),
        )

        await interaction.followup.send(
            embed=embed
        )

    async def _log_shop_purchase(
        self,
        *,
        interaction: discord.Interaction,
        result: dict,
    ) -> None:
        """Send the complete staff audit log for one shop purchase."""

        user = interaction.user
        item = result["item"]

        personal_transaction = result[
            "personal_transaction"
        ]
        organization_transaction = result[
            "organization_transaction"
        ]
        seller_organization = result[
            "seller_organization"
        ]

        seller_text = format_item_seller(item)
        seller_mode = format_item_seller_mode(item)
        purchase_status = format_item_purchase_status(
            item
        )
        settlement_type = format_item_settlement(
            item
        )
        remaining_stock_text = format_stock(
            result["remaining_stock"]
        )

        if seller_organization is None:
            seller_finance_log = (
                "Seller Organization ID: "
                "`Not Applicable`\n"
                "Seller Balance: "
                "`Not Applicable`\n"
                "Organization Transaction: "
                "`None`\n"
                "Economic Treatment: "
                "`Credits Removed from Circulation`"
            )
        else:
            seller_finance_log = (
                "Seller Organization ID: "
                f"`{seller_organization['organization_id']}`\n"
                "Seller Previous Balance: "
                f"**{format_credits(result['seller_balance_before'])}**\n"
                "Seller Updated Balance: "
                f"**{format_credits(seller_organization['balance'])}**\n"
                "Organization Transaction ID: "
                f"`{organization_transaction['organization_transaction_id']}`\n"
                "Organization Transaction Type: "
                f"`{organization_transaction['transaction_type']}`\n"
                "Economic Treatment: "
                "`Buyer-to-Organization Transfer`"
            )

        await send_ledger_log(
            bot=interaction.client,
            title="ENVI LEDGER PURCHASE LOG",
            description=(
                "Personal Transaction Type: "
                f"`{personal_transaction['type']}`\n"
                f"Reference: `{result['reference_id']}`\n"
                f"Ownership: **{seller_mode}**\n"
                f"Settlement: **{settlement_type}**\n"
                f"Purchase Status: **{purchase_status}**\n"
                f"Citizen: {user.mention}\n"
                f"Citizen ID: `{user.id}`\n"
                f"Item ID: `{item['item_id']}`\n"
                f"Item: **{item['name']}**\n"
                f"Seller: **{seller_text}**\n"
                f"Category: `{item['category']}`\n"
                f"Rarity: `{item['rarity']}`\n"
                f"Quantity: **{result['quantity']}**\n"
                f"Unit Price: **{format_credits(item['price'])}**\n"
                f"Total: **{format_credits(result['total_price'])}**\n"
                "Buyer Previous Balance: "
                f"**{format_credits(result['user_balance_before'])}**\n"
                "Buyer Updated Balance: "
                f"**{format_credits(result['user']['balance'])}**\n"
                f"Stock Remaining: **{remaining_stock_text}**\n"
                "Inventory Quantity: "
                f"**{result['inventory_quantity']}**\n"
                "Personal Transaction ID: "
                f"`{personal_transaction['transaction_id']}`\n"
                f"{seller_finance_log}"
            ),
        )

    async def _execute_shop_purchase(
        self,
        *,
        interaction: discord.Interaction,
        item_name: str,
        quantity: int,
    ) -> dict:
        """
        Execute one shop purchase through the atomic purchase service.

        Both /buy and the Components V2 storefront use this method so
        financial behavior and staff auditing cannot drift apart.
        """

        user = interaction.user

        ensure_user(
            user_id=user.id,
            display_name=user.display_name,
        )

        result = purchase_shop_item(
            user_id=user.id,
            item_name=item_name,
            quantity=quantity,
        )

        await self._log_shop_purchase(
            interaction=interaction,
            result=result,
        )

        return result

    async def _purchase_shop_view_item(
        self,
        interaction: discord.Interaction,
        item_snapshot: dict,
    ) -> dict:
        """
        Purchase one storefront item after validating its live record.

        The displayed snapshot is compared with the current listing so
        a citizen cannot unknowingly buy an item after its price, name,
        seller, or availability changes.
        """

        item_id = int(item_snapshot["item_id"])
        item = get_shop_item_by_id(item_id)

        refreshed_items = get_active_shop_items()
        refreshed_balance = get_balance(
            interaction.user.id
        )

        if item is None:
            return {
                "success": False,
                "message": (
                    "That shop item is no longer registered. "
                    "ENVI refreshed the catalog."
                ),
                "items": refreshed_items,
                "balance": refreshed_balance,
            }

        if int(item.get("active", 0)) != 1:
            return {
                "success": False,
                "message": (
                    "That shop item is no longer available. "
                    "ENVI refreshed the catalog."
                ),
                "items": refreshed_items,
                "balance": refreshed_balance,
            }

        snapshot_seller_id = item_snapshot.get(
            "seller_org_id"
        )
        current_seller_id = item.get(
            "seller_org_id"
        )

        if snapshot_seller_id is not None:
            snapshot_seller_id = int(
                snapshot_seller_id
            )

        if current_seller_id is not None:
            current_seller_id = int(
                current_seller_id
            )

        listing_changed = any(
            (
                str(item["name"])
                != str(item_snapshot["name"]),
                int(item["price"])
                != int(item_snapshot["price"]),
                current_seller_id
                != snapshot_seller_id,
            )
        )

        if listing_changed:
            return {
                "success": False,
                "message": (
                    "This listing changed while your shop "
                    "session was open. ENVI refreshed the "
                    "catalog. Review the updated item and "
                    "select it again."
                ),
                "items": refreshed_items,
                "balance": refreshed_balance,
            }

        try:
            result = await self._execute_shop_purchase(
                interaction=interaction,
                item_name=str(item["name"]),
                quantity=1,
            )
        except (ValueError, RuntimeError) as error:
            return {
                "success": False,
                "message": str(error),
                "items": get_active_shop_items(),
                "balance": get_balance(
                    interaction.user.id
                ),
            }

        return {
            "success": True,
            "result": result,
            "items": get_active_shop_items(),
            "balance": get_balance(
                interaction.user.id
            ),
        }

    @app_commands.command(
        name="inventory",
        description="View a citizen's ENVI Asset Registry.",
    )
    async def inventory(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ):
        target_user = user or interaction.user

        ensure_user(
            user_id=target_user.id,
            display_name=target_user.display_name,
        )

        inventory_items = get_user_inventory(target_user.id)

        if not inventory_items:
            embed = envi_embed(
                title="ENVI ASSET REGISTRY",
                description=(
                    f"Citizen: {target_user.mention}\n\n"
                    "No registered assets found."
                ),
            )

            await interaction.response.send_message(embed=embed)
            return

        item_lines = []

        for item in inventory_items:
            use_status = "Usable" if int(item["usable"]) == 1 else "Not Usable"
            item_type = "Consumable" if int(item["consumable"]) == 1 else "Permanent"

            item_lines.append(
                f"**{item['quantity']}x {item['name']}**\n"
                f"Category: `{item['category']}` | Rarity: `{item['rarity']}`\n"
                f"Use Status: `{use_status}` | Type: `{item_type}`\n"
                f"{item['description']}"
            )

        embed = envi_embed(
            title="ENVI ASSET REGISTRY",
            description=(
                f"Citizen: {target_user.mention}\n\n"
                + "\n\n".join(item_lines)
            ),
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="use",
        description="Use an item from your ENVI inventory.",
    )
    @app_commands.describe(
        item_name="Start typing the name of a usable item you own.",
    )
    @app_commands.autocomplete(
        item_name=use_item_autocomplete,
    )
    async def use_item(
        self,
        interaction: discord.Interaction,
        item_name: str,
    ):
        ensure_user(
            interaction.user.id,
            interaction.user.display_name,
        )

        item = get_user_inventory_item_by_name(
            user_id=interaction.user.id,
            item_name=item_name,
        )

        if item is None:
            guidance_reason = build_unknown_item_use_reason(
                user_id=interaction.user.id,
                requested_name=item_name,
            )

            embed = envi_error(
                title="ENVI ITEM USE DENIED",
                reason=guidance_reason,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        if int(item["usable"]) != 1:
            guidance_reason = build_non_usable_item_reason(
                user_id=interaction.user.id,
                item=item,
            )

            embed = envi_error(
                title="ENVI ITEM USE DENIED",
                reason=guidance_reason,
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        is_consumable = int(item["consumable"]) == 1
        remaining_quantity = int(item["quantity"])

        if is_consumable:
            try:
                remaining_quantity = decrease_item_quantity(
                    user_id=interaction.user.id,
                    item_id=item["item_id"],
                    quantity=1,
                )
            except ValueError as error:
                embed = envi_error(
                    title="ENVI ITEM USE DENIED",
                    reason=str(error),
                )

                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True,
                )
                return

        use_message = item["use_message"]

        if use_message is None:
            use_message = (
                f"**{item['name']}** used. "
                "ENVI has recorded the action."
            )

        if is_consumable:
            inventory_update = (
                f"One **{item['name']}** was consumed.\n"
                f"Remaining Quantity: **{remaining_quantity}**"
            )
        else:
            inventory_update = (
                f"**{item['name']}** is a permanent item and "
                "remains in your inventory.\n"
                f"Current Quantity: **{remaining_quantity}**"
            )

        await send_ledger_log(
            bot=interaction.client,
            title="ENVI ITEM USE LOG",
            description=(
                f"User: {interaction.user.mention}\n"
                f"Item: **{item['name']}**\n"
                f"Category: `{item['category']}`\n"
                f"Rarity: `{item['rarity']}`\n"
                f"Consumable: "
                f"**{'Yes' if is_consumable else 'No'}**\n"
                f"Remaining Quantity: **{remaining_quantity}**"
            ),
        )

        embed = envi_embed(
            title="ENVI ITEM USED",
            description=(
                f"User: {interaction.user.mention}\n"
                f"Item: **{item['name']}**\n"
                f"Category: `{item['category']}` | "
                f"Rarity: `{item['rarity']}`\n\n"
                f"{use_message}\n\n"
                "**Inventory Update**\n"
                f"{inventory_update}"
            ),
        )

        await interaction.response.send_message(
            embed=embed,
        )

    @app_commands.command(
        name="leaderboard",
        description="View the top Nexus Credit balances.",
    )
    async def leaderboard(self, interaction: discord.Interaction):
        top_users = get_top_balances(LEADERBOARD_LIMIT)

        if not top_users:
            embed = envi_embed(
                title="ENVI ECONOMIC RANKINGS",
                description="No active financial records found.",
            )

            await interaction.response.send_message(embed=embed)
            return

        ranking_lines = []

        for index, user_record in enumerate(top_users, start=1):
            ranking_lines.append(
                f"**{index}. {user_record['display_name']}** — "
                f"{format_credits(user_record['balance'])}"
            )

        embed = envi_embed(
            title="ENVI ECONOMIC RANKINGS",
            description="\n".join(ranking_lines),
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))
