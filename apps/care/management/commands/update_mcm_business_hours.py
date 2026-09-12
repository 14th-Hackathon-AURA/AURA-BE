import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.care.business_hours import parse_business_hours
from apps.care.models import Store


DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "mcm_business_hours.json"


def normalize(value):
    return re.sub(r"\s+", "", value or "").casefold()


class Command(BaseCommand):
    help = "제공된 엑셀의 영업시간만 기존 매장에 반영합니다. 매장을 생성하지 않습니다."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        rows = json.loads(DATA_PATH.read_text(encoding="utf-8"))["rows"]
        stores = list(Store.objects.select_for_update().all())
        changes = {}
        for row in rows:
            hours = row["opening_hours"]
            if hours:
                parse_business_hours(hours)
            official_id = row["official_store_id"]
            names = {normalize(row["name"]), normalize(row["official_name"])} - {""}
            addresses = {normalize(row["address"]), normalize(row["official_address"])} - {""}
            # ID is authoritative. For legacy records without IDs, require both
            # exact normalized name and address; never match by building alone.
            matches = [store for store in stores if (
                (official_id and store.official_store_id == official_id)
                or (not store.official_store_id and normalize(store.name) in names
                    and normalize(store.address) in addresses)
            )]
            if not matches:
                self.stdout.write(f"[미매칭] {row['source_row']}: {row['name']}")
            for store in matches:
                if store.pk in changes and changes[store.pk][1] != hours:
                    raise CommandError(f"영업시간이 충돌합니다: {store.name}")
                changes[store.pk] = (store, hours)

        updated = 0
        for store, hours in changes.values():
            if store.opening_hours == hours:
                continue
            self.stdout.write(f"[{ 'DRY RUN' if options['dry_run'] else '수정' }] "
                              f"{store.pk} {store.name}: {store.opening_hours!r} -> {hours!r}")
            if not options["dry_run"]:
                store.opening_hours = hours
                store.save(update_fields=["opening_hours"])
            updated += 1
        self.stdout.write(f"매칭 {len(changes)}개, 변경 {updated}개. "
                          "빈 영업시간은 예약 불가이며 미매칭 매장은 직접 확인해야 합니다.")
