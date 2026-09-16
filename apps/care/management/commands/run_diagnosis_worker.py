import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from apps.care.diagnosis_jobs import available, run_diagnosis


class Command(BaseCommand):
    help = "Process durable diagnosis jobs (use one worker with SQLite)."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Drain currently available jobs and exit")

    def handle(self, *args, **options):
        while True:
            close_old_connections()
            job = available().order_by("created_at", "pk").first()
            if job:
                run_diagnosis(job)
            elif options["once"]:
                return
            else:
                time.sleep(1)
