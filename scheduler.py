from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import atexit

scheduler = BackgroundScheduler()

def init_scheduler(app, db, execute_func):
    """Inisialisasi scheduler dengan konteks aplikasi."""
    with app.app_context():
        from models import Schedule
        schedules = Schedule.query.filter_by(is_active=True).all()
        for sched in schedules:
            if sched.cron_expression:
                trigger = CronTrigger.from_crontab(sched.cron_expression)
                scheduler.add_job(
                    func=lambda sid=sched.id: execute_func(sid),
                    trigger=trigger,
                    id=f'sched_{sched.id}',
                    replace_existing=True
                )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())