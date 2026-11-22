import unittest
from datetime import date, datetime, timezone

from app.sale_dates import (
    format_sale_date,
    sale_date_to_unix_milliseconds,
)


class SaleDateConversionTests(unittest.TestCase):
    def test_current_date_converts_to_unix_milliseconds(self):
        today = date.today()
        expected = int(
            datetime(
                today.year,
                today.month,
                today.day,
                tzinfo=timezone.utc,
            ).timestamp()
            * 1000
        )

        self.assertEqual(
            sale_date_to_unix_milliseconds(today.isoformat()),
            expected,
        )

    def test_historical_iso_datetime_preserves_instant_as_milliseconds(self):
        self.assertEqual(
            sale_date_to_unix_milliseconds("2020-05-01T10:30:45.123-03:00"),
            1588339845123,
        )

    def test_existing_millisecond_timestamp_is_preserved(self):
        timestamp_ms = 1773577800000
        self.assertEqual(
            sale_date_to_unix_milliseconds(str(timestamp_ms)),
            timestamp_ms,
        )

    def test_second_timestamps_are_rejected(self):
        for value in (1773577800, "1773577800"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "milissegundos"):
                    sale_date_to_unix_milliseconds(value)

    def test_backend_milliseconds_format_as_utc_without_epoch_fallback(self):
        self.assertEqual(
            format_sale_date(1773577800000),
            "2026-03-15T12:30:00.000Z",
        )
        with self.assertRaisesRegex(ValueError, "milissegundos"):
            format_sale_date(0)
