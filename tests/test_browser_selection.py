"""
Test suite for Step 47: Multi-Browser Selection & Launcher Integration (Brave, Chrome, Edge, Custom).
Verifies:
- DB setting properties (browser_type, browser_custom_path, browser_cdp_port)
- Finding executable paths across platforms
- Dynamic command line generation
- Status, Config, and Launch APIs
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import os
import platform

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.database import Base
from app.models import User, Setting
from app.services.browser import (
    get_browser_executable_path,
    get_launch_commands,
    launch_browser_instance,
    get_browser_status,
)


class TestBrowserSelectionAndLauncher(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Create an in-memory SQLite database for testing setting models
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Populate a test user
        async with self.session_maker() as db:
            user = User(id=1, email="test@candidate.com", password_hash="hashed_pw")
            db.add(user)
            setting = Setting(
                user_id=1,
                browser_type="brave",
                browser_cdp_port=9222,
                browser_custom_path=None,
            )
            db.add(setting)
            await db.commit()

    async def asyncTearDown(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()

    # ─────────────────────────────────────────────────────────────────────────
    # DB Columns & Migration Tests
    # ─────────────────────────────────────────────────────────────────────────
    async def test_settings_db_properties(self):
        async with self.session_maker() as db:
            res = await db.execute(select(Setting).where(Setting.user_id == 1))
            st = res.scalar_one()

            self.assertEqual(st.browser_type, "brave")
            self.assertEqual(st.browser_cdp_port, 9222)
            self.assertIsNone(st.browser_custom_path)

            # Update settings
            st.browser_type = "chrome"
            st.browser_cdp_port = 9223
            st.browser_custom_path = "/path/to/chrome"
            await db.commit()

            # Refresh and assert
            await db.refresh(st)
            self.assertEqual(st.browser_type, "chrome")
            self.assertEqual(st.browser_cdp_port, 9223)
            self.assertEqual(st.browser_custom_path, "/path/to/chrome")

    # ─────────────────────────────────────────────────────────────────────────
    # Executable Path & Command Generation Tests
    # ─────────────────────────────────────────────────────────────────────────
    @patch("os.path.exists")
    def test_executable_path_resolution(self, mock_exists):
        # Simulate browser existing at a default path
        mock_exists.return_value = True

        # Test Brave path
        brave_path = get_browser_executable_path("brave")
        self.assertIsNotNone(brave_path)

        # Test Custom path
        custom_path = get_browser_executable_path("custom", custom_path="/custom/dir/browser")
        self.assertEqual(custom_path, os.path.abspath("/custom/dir/browser"))

    def test_launch_command_generation(self):
        cmds = get_launch_commands(browser_type="brave", port=9225, custom_path="/path/to/brave")
        self.assertEqual(cmds["browser_name"], "Brave Browser")
        self.assertEqual(cmds["port"], 9225)
        self.assertIn("9225", cmds["powershell"])
        self.assertIn("9225", cmds["cmd"])
        self.assertIn("9225", cmds["bash"])

    # ─────────────────────────────────────────────────────────────────────────
    # Browser Launcher & Status Tests
    # ─────────────────────────────────────────────────────────────────────────
    @patch("subprocess.Popen")
    @patch("app.services.browser.get_browser_executable_path")
    def test_launch_browser_instance_success(self, mock_get_path, mock_popen):
        mock_get_path.return_value = "/bin/brave"
        mock_proc = MagicMock()
        mock_proc.pid = 98765
        mock_popen.return_value = mock_proc

        result = launch_browser_instance(browser_type="brave", port=9222)
        self.assertTrue(result["success"])
        self.assertEqual(result["pid"], 98765)
        self.assertEqual(result["port"], 9222)

    @patch("app.services.browser.get_browser_executable_path")
    def test_launch_browser_instance_not_found(self, mock_get_path):
        mock_get_path.return_value = None

        result = launch_browser_instance(browser_type="brave", port=9222)
        self.assertFalse(result["success"])
        self.assertIn("Could not find", result["message"])
        self.assertIn("launch_commands", result)

    @patch("socket.socket")
    async def test_get_browser_status_offline(self, mock_socket_cls):
        # Simulate connection refused (port offline)
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 111  # Connection refused
        mock_socket_cls.return_value = mock_sock

        status = await get_browser_status(port=9222, browser_type="brave")
        self.assertFalse(status["cdp_reachable"])
        self.assertEqual(status["browser_type"], "brave")
        self.assertEqual(status["port"], 9222)


if __name__ == "__main__":
    unittest.main()
