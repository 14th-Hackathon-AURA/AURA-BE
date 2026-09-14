import json
from datetime import datetime, timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from .business_hours import STORE_TIMEZONE, UnknownBusinessHours, reservation_slots
from .management.commands.update_mcm_business_hours import DATA_PATH
from .models import Store


class BusinessHoursTests(SimpleTestCase):
    def test_every_source_schedule_is_valid(self):
        rows = json.loads(DATA_PATH.read_text(encoding="utf-8"))["rows"]
        self.assertEqual(len(rows), 21)
        self.assertEqual(sum(not row["opening_hours"] for row in rows), 3)
        for row in rows:
            if row["opening_hours"]:
                for day in range(7):
                    self.assertIsInstance(reservation_slots(
                        row["opening_hours"], datetime(2030, 1, 7 + day).date()), list)

    def test_weekday_weekend_and_closing_boundary(self):
        hours = "월-목 10:30-20:00 / 금-일 10:30-20:30"
        monday = reservation_slots(hours, datetime(2030, 1, 7).date())
        friday = reservation_slots(hours, datetime(2030, 1, 11).date())
        self.assertEqual(monday[0].strftime("%H:%M"), "10:30")
        self.assertEqual(monday[-1].strftime("%H:%M"), "19:30")
        self.assertEqual(friday[-1].strftime("%H:%M"), "20:00")
        self.assertEqual(len(friday), len(monday) + 1)

    def test_closed_and_early_airport_hours(self):
        self.assertEqual(reservation_slots("월-토 10:30-19:30 / 일 휴무",
                                          datetime(2030, 1, 13).date()), [])
        slots = reservation_slots("매일 06:30-21:30", datetime(2030, 1, 7).date())
        self.assertEqual(len(slots), 30)
        self.assertEqual(slots[0].hour, 6)
        self.assertEqual(slots[-1].strftime("%H:%M"), "21:00")

    def test_unknown_and_malformed_hours_do_not_fall_back(self):
        for hours in ["", "문의", "매일 25:00-26:00", "매일 20:00-10:00",
                      "매일 10:00-18:00 / 일 휴무"]:
            with self.subTest(hours=hours), self.assertRaises(UnknownBusinessHours):
                reservation_slots(hours, datetime(2030, 1, 7).date())

    def test_partial_intervals_do_not_exceed_closing(self):
        slots = reservation_slots("매일 10:10-11:10", datetime(2030, 1, 7).date())
        self.assertEqual([slot.strftime("%H:%M") for slot in slots], ["10:30"])


class ReservationBusinessHoursApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("hours-user")
        self.product = Product.objects.create(user=self.user, name="Bag", category="bag")
        self.store = Store.objects.create(name="MCM", address="서울",
                                          opening_hours="매일 11:00-20:00")
        self.client.force_authenticate(self.user)
        self.day = timezone.localdate() + timedelta(days=7)

    def book(self, hour, minute=0):
        visit = datetime.combine(self.day, datetime.min.time(), tzinfo=STORE_TIMEZONE)
        visit = visit.replace(hour=hour, minute=minute)
        return self.client.post("/api/visit-reservations/", {
            "store": self.store.pk, "product": self.product.pk,
            "visit_at": visit.isoformat(), "purpose": "상담"}, format="json")

    def availability(self):
        return self.client.get("/api/visit-reservations/availability/", {
            "store": self.store.pk, "date": self.day.isoformat()})

    def test_list_create_conflict_and_cancel_share_actual_hours(self):
        response = self.availability()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slots"][0]["time"], "11:00")
        self.assertEqual(response.data["slots"][-1]["time"], "19:30")
        self.assertEqual(self.book(10).status_code, 400)
        self.assertEqual(self.book(20).status_code, 400)
        self.assertEqual(self.book(19, 15).status_code, 400)
        booking = self.book(19, 30)
        self.assertEqual(booking.status_code, 201, booking.data)
        self.assertEqual(self.book(19, 30).status_code, 400)
        self.assertFalse(self.availability().data["slots"][-1]["available"])
        self.assertEqual(self.client.post(
            f"/api/visit-reservations/{booking.data['id']}/cancel/").status_code, 200)
        self.assertTrue(self.availability().data["slots"][-1]["available"])

    def test_store_only_update_revalidates_time(self):
        booking = self.book(19, 30)
        other = Store.objects.create(name="early", address="서울", opening_hours="매일 10:00-18:00")
        response = self.client.patch(f"/api/visit-reservations/{booking.data['id']}/",
                                     {"store": other.pk}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_closed_and_unknown_hours(self):
        self.day += timedelta(days=(6 - self.day.weekday()) % 7)
        self.store.opening_hours = "월-토 10:30-19:30 / 일 휴무"
        self.store.save()
        self.assertEqual(self.availability().data["slots"], [])
        self.assertEqual(self.book(11).status_code, 400)
        self.store.opening_hours = ""
        self.store.save()
        self.assertEqual(self.availability().status_code, 400)
        self.assertEqual(self.book(11).status_code, 400)

    def test_utc_input_uses_korean_weekday(self):
        self.day += timedelta(days=(6 - self.day.weekday()) % 7)
        self.store.opening_hours = "월-토 06:30-21:30 / 일 휴무"
        self.store.save()
        visit = datetime.combine(self.day, datetime.min.time(), tzinfo=STORE_TIMEZONE).replace(hour=6, minute=30)
        from datetime import timezone as dt_timezone
        response = self.client.post("/api/visit-reservations/", {
            "store": self.store.pk, "product": self.product.pk,
            "visit_at": visit.astimezone(dt_timezone.utc).isoformat(), "purpose": "상담"}, format="json")
        self.assertEqual(response.status_code, 400)


class UpdateBusinessHoursCommandTests(TestCase):
    def test_id_matching_dry_run_idempotency_and_preservation(self):
        store = Store.objects.create(name="기존 이름", address="기존 주소",
            official_store_id="1000001596", opening_hours="매일 10:00-18:00",
            latitude="37.5000000", supports_as=False)
        call_command("update_mcm_business_hours", dry_run=True, stdout=StringIO())
        store.refresh_from_db()
        self.assertEqual(store.opening_hours, "매일 10:00-18:00")
        for _ in range(2):
            call_command("update_mcm_business_hours", stdout=StringIO())
        store.refresh_from_db()
        self.assertEqual(store.opening_hours, "매일 11:00-20:00")
        self.assertEqual(store.name, "기존 이름")
        self.assertFalse(store.supports_as)
        self.assertEqual(str(store.latitude), "37.5000000")
        self.assertEqual(Store.objects.count(), 1)

    def test_blank_clears_placeholder_and_different_id_is_untouched(self):
        store = Store.objects.create(name="T2", address="인천", official_store_id="1000001628",
                                      opening_hours="매일 10:00-18:00")
        wrong = Store.objects.create(name="MCM HAUS", address="서울특별시 강남구 압구정로 412 MCM HAUS",
                                      official_store_id="different", opening_hours="매일 09:00-17:00")
        call_command("update_mcm_business_hours", stdout=StringIO())
        store.refresh_from_db()
        wrong.refresh_from_db()
        self.assertEqual(store.opening_hours, "")
        self.assertEqual(wrong.opening_hours, "매일 09:00-17:00")

    def test_legacy_name_and_address_match(self):
        store = Store.objects.create(name="MCMHAUS", address="서울특별시 강남구 압구정로 412 MCM HAUS")
        unrelated = Store.objects.create(name="다른 매장", address=store.address)
        call_command("update_mcm_business_hours", stdout=StringIO())
        store.refresh_from_db()
        unrelated.refresh_from_db()
        self.assertEqual(store.opening_hours, "매일 11:00-20:00")
        self.assertEqual(unrelated.opening_hours, "")
