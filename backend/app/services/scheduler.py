import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.campaign_runner import CampaignRunner

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def start_scheduler() -> None:
    runner = CampaignRunner()
    scheduler.add_job(
        runner.run_active_campaigns,
        "interval",
        minutes=30,
        id="run_active_campaigns",
        replace_existing=True,
    )
    scheduler.add_job(
        runner.run_followups,
        "interval",
        hours=6,
        id="run_followups",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler initialized and started")


async def stop_scheduler() -> None:
    scheduler.shutdown()
    logger.info("APScheduler shutdown complete")
