from redis import Redis
from rq import Queue
from app.core.config import settings
from app.core.logging import logger
from app.workers.whatsapp_worker import process_whatsapp_message

redis_conn = Redis.from_url(settings.REDIS_URL, decode_responses=False)

whatsapp_queue = Queue('whatsapp', connection=redis_conn)
insights_queue = Queue('insights', connection=redis_conn)
notifications_queue = Queue('notifications', connection=redis_conn)
charge_reminders_queue = Queue('charge_reminders', connection=redis_conn)


def enqueue_whatsapp_message(user_id: int, phone_number: str, message: str, message_sid: str):
    try:
        job = whatsapp_queue.enqueue(
            process_whatsapp_message,
            user_id=user_id,
            phone_number=phone_number,
            message=message,
            message_sid=message_sid,
            job_timeout='5m'
        )
        logger.info(f"Enqueued WhatsApp message job {job.id} for user {user_id}")
        return job.id
    except Exception as e:
        logger.error(f"Error enqueuing WhatsApp message: {str(e)}")
        return None


def enqueue_weekly_insights(user_id: int):
    try:
        job = insights_queue.enqueue(
            'app.workers.insights_worker.send_weekly_insights',
            user_id=user_id,
            job_timeout='10m'
        )
        logger.info(f"Enqueued weekly insights job {job.id} for user {user_id}")
        return job.id
    except Exception as e:
        logger.error(f"Error enqueuing insights: {str(e)}")
        return None


def enqueue_notification(user_id: int, message: str, notification_type: str):
    try:
        job = notifications_queue.enqueue(
            'app.workers.notification_worker.send_notification',
            user_id=user_id,
            message=message,
            notification_type=notification_type,
            job_timeout='2m'
        )
        logger.info(f"Enqueued notification job {job.id} for user {user_id}")
        return job.id
    except Exception as e:
        logger.error(f"Error enqueuing notification: {str(e)}")
        return None


def enqueue_charge_reminders():
    """Enqueue the charge reminders job to the charge_reminders queue."""
    try:
        job = charge_reminders_queue.enqueue(
            'app.jobs.charge_reminder_jobs.run_charge_reminders_job',
            job_timeout='10m'
        )
        logger.info(f"Enqueued charge reminders job {job.id}")
        return job.id
    except Exception as e:
        logger.error(f"Error enqueuing charge reminders: {str(e)}")
        return None
