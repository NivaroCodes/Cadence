import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.campaign import Campaign, CampaignStatus
from app.models.lead import Lead
from app.models.message import Message, MessageChannel, MessageStatus
from app.services.ai_agent import GeminiAgent
from app.services.email_service import GmailService
from app.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)

MAX_REPLY_CHECK_ATTEMPTS = 5


async def _schedule_reply_check(message_id_str: str) -> None:
    runner = CampaignRunner()
    await runner.check_replies_for_message(uuid.UUID(message_id_str))


class CampaignRunner:
    def __init__(self) -> None:
        self._ai_agent = GeminiAgent()
        self._gmail_service = GmailService()
        self._telegram_service = TelegramService()

    async def run_campaign(self, campaign_id: uuid.UUID, db: AsyncSession | None = None) -> None:
        if db is None:
            async with AsyncSessionLocal() as session:
                await self._run_campaign_impl(campaign_id, session)
        else:
            await self._run_campaign_impl(campaign_id, db)

    async def run_followups(self, db: AsyncSession | None = None) -> None:
        if db is None:
            async with AsyncSessionLocal() as session:
                await self._run_followups_impl(session)
        else:
            await self._run_followups_impl(db)

    async def run_active_campaigns(self, db: AsyncSession | None = None) -> None:
        if db is None:
            async with AsyncSessionLocal() as session:
                await self._run_active_campaigns_impl(session)
        else:
            await self._run_active_campaigns_impl(db)

    async def _run_campaign_impl(self, campaign_id: uuid.UUID, db: AsyncSession) -> None:
        stmt = (
            select(Campaign)
            .options(selectinload(Campaign.leads))
            .where(Campaign.id == campaign_id)
        )
        result = await db.execute(stmt)
        campaign = result.scalars().first()
        if not campaign:
            logger.error("Campaign %s not found for running", campaign_id)
            return

        stmt_contacted = (
            select(Message.lead_id)
            .where(Message.campaign_id == campaign_id)
            .where(Message.sequence_number == 1)
        )
        res_contacted = await db.execute(stmt_contacted)
        contacted_lead_ids = set(res_contacted.scalars().all())

        pending_leads = [lead for lead in campaign.leads if lead.id not in contacted_lead_ids]
        logger.info("Running campaign %s | %d pending leads", campaign.name, len(pending_leads))

        for lead in pending_leads:
            try:
                lead_data = {
                    "name": lead.name,
                    "company": lead.company,
                    "email": lead.email,
                    "phone": lead.phone,
                    "website": lead.website,
                    "industry": lead.industry,
                    "context": lead.context,
                }
                
                analysis = await self._ai_agent.analyze_lead(lead_data)
                await asyncio.sleep(8)

                content = await self._ai_agent.generate_email(
                    analysis,
                    campaign.tone.value if hasattr(campaign.tone, "value") else str(campaign.tone),
                    campaign.language.value if hasattr(campaign.language, "value") else str(campaign.language),
                    lead_name=lead.name,
                    company_name=lead.company
                )
                await asyncio.sleep(8)

                # Telegram outreach requires chat_id to be collected separately.
                # Fallback to email if no valid telegram_chat_id attribute exists on Lead.
                telegram_chat_id = getattr(lead, "telegram_chat_id", None)
                channel = MessageChannel.telegram if telegram_chat_id else MessageChannel.email

                sent = False
                recipient = ""

                if channel == MessageChannel.email:
                    lang = campaign.language.value if hasattr(campaign.language, "value") else str(campaign.language)
                    if lang == "ru":
                        subject = f"Сотрудничество с {lead.company}"
                    elif lang == "kz":
                        subject = f"{lead.company} үшін ұсыныс"
                    else:
                        subject = f"Partnership proposal for {lead.company}"

                    gmail_service = GmailService(user_id=campaign.user_id)
                    sent = await gmail_service.send_email(
                        to=lead.email,
                        subject=subject,
                        body=content
                    )
                    recipient = lead.email
                    await asyncio.sleep(30)
                else:
                    sent = await self._telegram_service.send_message(
                        chat_id=str(telegram_chat_id),
                        text=content
                    )
                    recipient = str(telegram_chat_id)

                if sent:
                    msg = Message(
                        campaign_id=campaign_id,
                        lead_id=lead.id,
                        channel=channel,
                        content=content,
                        status=MessageStatus.sent,
                        recipient_address=recipient,
                        sequence_number=1,
                        sent_at=datetime.now(timezone.utc)
                    )
                    db.add(msg)
                    await db.commit()
                    await db.refresh(msg)
                    logger.info("Saved sequence 1 message for lead %s in campaign %s", lead.id, campaign_id)

                    from app.services.scheduler import scheduler
                    run_time = datetime.now(timezone.utc) + timedelta(minutes=30)
                    scheduler.add_job(
                        _schedule_reply_check,
                        trigger='date',
                        run_date=run_time,
                        args=[str(msg.id)],
                        id=f"reply_check_{msg.id}",
                        replace_existing=True,
                    )
                    logger.info("Scheduled reply check for message %s at %s", msg.id, run_time)

            except Exception:
                logger.exception("Failed to process campaign %s for lead %s", campaign_id, lead.id)

    async def check_replies_for_message(self, message_id: uuid.UUID) -> None:
        async with AsyncSessionLocal() as db:
            stmt = (
                select(Message)
                .options(selectinload(Message.lead))
                .where(Message.id == message_id)
            )
            result = await db.execute(stmt)
            message = result.scalars().first()

            if not message or message.status != MessageStatus.sent:
                return

            gmail_service = GmailService(user_id=message.user_id)
            reply_ids = await gmail_service.search_replies(
                message.lead.email, message.sent_at
            )

            if reply_ids:
                message.status = MessageStatus.replied
                await db.commit()
                logger.info("Reply detected for lead %s, message %s", message.lead.email, message_id)
                return

            message.reply_check_attempts += 1
            await db.commit()

            if message.reply_check_attempts < MAX_REPLY_CHECK_ATTEMPTS:
                from app.services.scheduler import scheduler
                run_time = datetime.now(timezone.utc) + timedelta(hours=1)
                scheduler.add_job(
                    _schedule_reply_check,
                    trigger='date',
                    run_date=run_time,
                    args=[str(message_id)],
                    id=f"reply_check_{message_id}_{message.reply_check_attempts}",
                    replace_existing=True,
                )
                logger.info(
                    "No reply for %s — attempt %d/%d, next check at %s",
                    message.lead.email, message.reply_check_attempts,
                    MAX_REPLY_CHECK_ATTEMPTS, run_time,
                )
            else:
                logger.info("Max reply checks reached for message %s", message_id)

    async def _run_followups_impl(self, db: AsyncSession) -> None:
        from uuid import UUID
        ADMIN_UUID = UUID("00000000-0000-0000-0000-000000000000")

        # Step 1: Follow-up sequence 1 -> 2 (sent >= 3 days ago)
        stmt_has_seq_2 = select(Message.campaign_id, Message.lead_id).where(Message.sequence_number == 2)
        res_has_seq_2 = await db.execute(stmt_has_seq_2)
        exclude_pairs_2 = {(r[0], r[1]) for r in res_has_seq_2.all()}

        three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
        stmt_seq_1 = (
            select(Message)
            .options(selectinload(Message.campaign), selectinload(Message.lead))
            .join(Campaign, Message.campaign_id == Campaign.id)
            .where(Message.sequence_number == 1)
            .where(Message.status == MessageStatus.sent)
            .where(Message.sent_at <= three_days_ago)
            .where(Campaign.user_id == ADMIN_UUID)
        )
        res_seq_1 = await db.execute(stmt_seq_1)
        messages_seq_1 = res_seq_1.scalars().all()

        eligible_seq_1 = [m for m in messages_seq_1 if (m.campaign_id, m.lead_id) not in exclude_pairs_2]
        logger.info("Processing sequence 1->2 followups | %d eligible", len(eligible_seq_1))

        for m in eligible_seq_1:
            try:
                lang = m.campaign.language.value if hasattr(m.campaign.language, "value") else str(m.campaign.language)
                followup_content = await self._ai_agent.generate_followup(
                    original_email=m.content,
                    sequence=1,
                    language=lang,
                    lead_name=m.lead.name,
                    company_name=m.lead.company
                )
                await asyncio.sleep(8)

                sent = False
                if m.channel == MessageChannel.email:
                    if lang == "ru":
                        subject = f"Re: Сотрудничество с {m.lead.company}"
                    elif lang == "kz":
                        subject = f"Re: {m.lead.company} үшін ұсыныс"
                    else:
                        subject = f"Re: Partnership proposal for {m.lead.company}"

                    gmail_service = GmailService(user_id=m.campaign.user_id)
                    sent = await gmail_service.send_email(
                        to=m.lead.email,
                        subject=subject,
                        body=followup_content
                    )
                    await asyncio.sleep(30)
                else:
                    sent = await self._telegram_service.send_message(
                        chat_id=m.recipient_address,
                        text=followup_content
                    )

                if sent:
                    new_msg = Message(
                        campaign_id=m.campaign_id,
                        lead_id=m.lead_id,
                        channel=m.channel,
                        content=followup_content,
                        status=MessageStatus.sent,
                        recipient_address=m.recipient_address,
                        sequence_number=2,
                        sent_at=datetime.now(timezone.utc)
                    )
                    db.add(new_msg)
                    await db.commit()
                    logger.info("Saved sequence 2 follow-up for lead %s in campaign %s", m.lead_id, m.campaign_id)

            except Exception:
                logger.exception("Failed to process follow-up sequence 2 for lead %s", m.lead_id)

        # Step 2: Follow-up sequence 2 -> 3 (sent >= 7 days ago)
        stmt_has_seq_3 = select(Message.campaign_id, Message.lead_id).where(Message.sequence_number == 3)
        res_has_seq_3 = await db.execute(stmt_has_seq_3)
        exclude_pairs_3 = {(r[0], r[1]) for r in res_has_seq_3.all()}

        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        stmt_seq_2 = (
            select(Message)
            .options(selectinload(Message.campaign), selectinload(Message.lead))
            .join(Campaign, Message.campaign_id == Campaign.id)
            .where(Message.sequence_number == 2)
            .where(Message.status == MessageStatus.sent)
            .where(Message.sent_at <= seven_days_ago)
            .where(Campaign.user_id == ADMIN_UUID)
        )
        res_seq_2 = await db.execute(stmt_seq_2)
        messages_seq_2 = res_seq_2.scalars().all()

        eligible_seq_2 = [m for m in messages_seq_2 if (m.campaign_id, m.lead_id) not in exclude_pairs_3]
        logger.info("Processing sequence 2->3 followups | %d eligible", len(eligible_seq_2))

        for m in eligible_seq_2:
            try:
                lang = m.campaign.language.value if hasattr(m.campaign.language, "value") else str(m.campaign.language)
                followup_content = await self._ai_agent.generate_followup(
                    original_email=m.content,
                    sequence=2,
                    language=lang,
                    lead_name=m.lead.name,
                    company_name=m.lead.company
                )
                await asyncio.sleep(8)

                sent = False
                if m.channel == MessageChannel.email:
                    if lang == "ru":
                        subject = f"Re: Сотрудничество с {m.lead.company}"
                    elif lang == "kz":
                        subject = f"Re: {m.lead.company} үшін ұсыныс"
                    else:
                        subject = f"Re: Partnership proposal for {m.lead.company}"

                    gmail_service = GmailService(user_id=m.campaign.user_id)
                    sent = await gmail_service.send_email(
                        to=m.lead.email,
                        subject=subject,
                        body=followup_content
                    )
                    await asyncio.sleep(30)
                else:
                    sent = await self._telegram_service.send_message(
                        chat_id=m.recipient_address,
                        text=followup_content
                    )

                if sent:
                    new_msg = Message(
                        campaign_id=m.campaign_id,
                        lead_id=m.lead_id,
                        channel=m.channel,
                        content=followup_content,
                        status=MessageStatus.sent,
                        recipient_address=m.recipient_address,
                        sequence_number=3,
                        sent_at=datetime.now(timezone.utc)
                    )
                    db.add(new_msg)
                    await db.commit()
                    logger.info("Saved sequence 3 follow-up for lead %s in campaign %s", m.lead_id, m.campaign_id)

            except Exception:
                logger.exception("Failed to process follow-up sequence 3 for lead %s", m.lead_id)

    async def _run_active_campaigns_impl(self, db: AsyncSession) -> None:
        from uuid import UUID
        ADMIN_UUID = UUID("00000000-0000-0000-0000-000000000000")
        
        stmt = select(Campaign).where(
            (Campaign.status == CampaignStatus.active) &
            (Campaign.user_id == ADMIN_UUID)
        )
        result = await db.execute(stmt)
        active_campaigns = result.scalars().all()
        logger.info("Running active campaigns runner for ADMIN | %d campaigns active", len(active_campaigns))

        for c in active_campaigns:
            await self._run_campaign_impl(c.id, db)
            
        await self._run_followups_impl(db)
