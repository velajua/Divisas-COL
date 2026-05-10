import tempfile
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import verify_instagram_token as subject


class VerifyInstagramTokenTests(unittest.TestCase):
    def test_non_monday_exits_without_reading_env(self):
        calls = []

        exit_code = subject.run(
            env_path=Path("missing.env"),
            today=date(2026, 5, 12),
            now=datetime(2026, 5, 12, tzinfo=timezone.utc),
            refresh_user_access_token=lambda user_token, app_id, app_secret: calls.append(user_token),
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [])

    def test_monday_keeps_token_when_expiration_is_not_close(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            expires_at = datetime(2026, 5, 25, tzinfo=timezone.utc)
            env_path.write_text(
                "\n".join(
                    [
                        "OTHER=value",
                        "INSTAGRAM_APP_ID=app-id",
                        "INSTAGRAM_APP_SECRET=app-secret",
                        "META_USER_ACCESS_TOKEN=old-token",
                        "META_APP_ACCESS_TOKEN=app-token",
                        f"META_USER_ACCESS_TOKEN_EXPIRES_AT={expires_at.isoformat()}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            exit_code = subject.run(
                env_path=env_path,
                today=date(2026, 5, 11),
                now=datetime(2026, 5, 11, tzinfo=timezone.utc),
                refresh_user_access_token=lambda user_token, app_id, app_secret: self.fail("refresh should not be called"),
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("META_USER_ACCESS_TOKEN=old-token", env_path.read_text(encoding="utf-8"))

    def test_monday_refreshes_user_token_when_expiration_is_less_than_ten_days_away(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "OTHER=value",
                        "INSTAGRAM_APP_ID=app-id",
                        "INSTAGRAM_APP_SECRET=app-secret",
                        "META_USER_ACCESS_TOKEN=old-token",
                        "META_APP_ACCESS_TOKEN=app-token",
                        "META_PAGE_ACCESS_TOKEN=existing-page-token",
                        "INSTAGRAM_USER_ID=ig-123",
                        "META_USER_ACCESS_TOKEN_EXPIRES_AT=2026-05-20T00:00:00+00:00",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            def refresh_user_access_token(user_token, app_id, app_secret):
                self.assertEqual(user_token, "old-token")
                self.assertEqual(app_id, "app-id")
                self.assertEqual(app_secret, "app-secret")
                return {
                    "access_token": "new-user-token",
                    "expires_in": 60 * 60 * 24 * 60,
                }

            exit_code = subject.run(
                env_path=env_path,
                today=date(2026, 5, 11),
                now=datetime(2026, 5, 11, 12, tzinfo=timezone.utc),
                refresh_user_access_token=refresh_user_access_token,
            )

            updated = env_path.read_text(encoding="utf-8")
            expected_expiry = datetime(2026, 7, 10, 12, tzinfo=timezone.utc).isoformat()
            self.assertEqual(exit_code, 0)
            self.assertIn("OTHER=value", updated)
            self.assertIn("META_USER_ACCESS_TOKEN=new-user-token", updated)
            self.assertIn("META_PAGE_ACCESS_TOKEN=existing-page-token", updated)
            self.assertIn(f"META_USER_ACCESS_TOKEN_EXPIRES_AT={expected_expiry}", updated)

    def test_uses_debug_token_expiration_when_env_expiration_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "META_USER_ACCESS_TOKEN=old-token",
                        "INSTAGRAM_APP_ID=app-id",
                        "INSTAGRAM_APP_SECRET=app-secret",
                        "META_APP_ACCESS_TOKEN=app-token",
                        "META_PAGE_ACCESS_TOKEN=existing-page-token",
                        "INSTAGRAM_USER_ID=ig-123",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            exit_code = subject.run(
                env_path=env_path,
                today=date(2026, 5, 11),
                now=datetime(2026, 5, 11, tzinfo=timezone.utc),
                get_token_expiration=lambda token, app_token: datetime(2026, 5, 15, tzinfo=timezone.utc),
                refresh_user_access_token=lambda user_token, app_id, app_secret: {
                    "access_token": "new-user-token",
                    "expires_in": 60 * 60 * 24,
                },
            )

            updated = env_path.read_text(encoding="utf-8")
            self.assertEqual(exit_code, 0)
            self.assertIn("META_USER_ACCESS_TOKEN=new-user-token", updated)
            self.assertIn("META_PAGE_ACCESS_TOKEN=existing-page-token", updated)
            self.assertIn("META_USER_ACCESS_TOKEN_EXPIRES_AT=", updated)


class ExpirationParsingTests(unittest.TestCase):
    def test_parses_unix_timestamp_expiration(self):
        parsed = subject.parse_expiration("1770000000")

        self.assertEqual(parsed, datetime.fromtimestamp(1770000000, tz=timezone.utc))

    def test_rejects_invalid_expiration(self):
        with self.assertRaises(ValueError):
            subject.parse_expiration("not-a-date")


if __name__ == "__main__":
    unittest.main()
