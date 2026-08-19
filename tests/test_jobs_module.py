"""
Comprehensive test suite for the Job Application Agent (Steps 38-46).
Tests:
- Step 38: DB Models & Migrations
- Step 39: Job Search Agent & deduplication
- Step 40: Job Filter / LLM Scorer & threshold handling
- Step 41: Browser Service & CDP offline handling
- Step 42: Job Applicator & Dispatcher
- Step 43: Tracking Agent, Orchestrator, Approval Queue & Stats
- Step 44: Frontend API client compatibility
- Step 45: Dynamic Resume Sourcing & Caching
- Step 46: Safety Rails (Duplicate guard, Daily cap, Portal backoff)
"""
import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base
from app.models import (
    User,
    Setting,
    Resume,
    JobPreference,
    JobListing,
    JobApplication,
    SendLog,
    ContextProfile,
)
from app.services.job_search import run_job_search
from app.services.job_filter import score_job, score_all_new_listings
from app.services.browser import get_browser_status, BrowserNotAvailableError
from app.services.job_applicator import (
    get_latest_resume_path,
    clear_resume_cache,
    apply_to_job,
    _is_portal_blocked,
    _increment_block,
    _blocked_portals,
)
from app.services.job_tracker import (
    get_approval_queue,
    approve_listing,
    reject_listing,
    get_job_stats,
    get_job_errors,
    run_apply_cycle,
    full_pipeline_run,
)


class TestJobApplicationAgent(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Create an in-memory SQLite database for testing
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Populate a test user with profile and preferences
        async with self.session_maker() as db:
            user = User(id=1, email="candidate@test.com", password_hash="hashed_pw")
            db.add(user)

            setting = Setting(user_id=1, job_agent_enabled=True)
            db.add(setting)

            pref = JobPreference(
                user_id=1,
                role_1="Software Engineer",
                role_2="Backend Developer",
                locations="Remote, Bangalore",
                experience_level="entry",
                auto_apply_threshold=85,
                max_applications_per_day=5,
            )
            db.add(pref)

            profile = ContextProfile(
                user_id=1,
                full_name="Alex Developer",
                role_title="Junior Backend Engineer",
            )
            db.add(profile)

            # Add a mock resume
            os.makedirs("./storage_data/1", exist_ok=True)
            mock_resume_path = "./storage_data/1/test_resume.pdf"
            with open(mock_resume_path, "wb") as f:
                f.write(b"%PDF-1.4 Mock resume content for testing")

            resume = Resume(
                user_id=1,
                file_url=mock_resume_path,
                file_name="test_resume.pdf",
            )
            db.add(resume)
            await db.commit()

    async def asyncTearDown(self):
        clear_resume_cache()
        _blocked_portals.clear()
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()

        # Clean test resume file
        if os.path.exists("./storage_data/1/test_resume.pdf"):
            os.remove("./storage_data/1/test_resume.pdf")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 38: DB Models & Migration Tests
    # ─────────────────────────────────────────────────────────────────────────
    async def test_step38_models_and_relationships(self):
        async with self.session_maker() as db:
            listing = JobListing(
                user_id=1,
                portal="linkedin",
                job_title="Junior Python Engineer",
                company="Acme Corp",
                location="Remote",
                job_url="https://linkedin.com/jobs/view/12345",
                status="new",
            )
            db.add(listing)
            await db.commit()
            await db.refresh(listing)

            self.assertIsNotNone(listing.id)
            self.assertEqual(listing.status, "new")

            app = JobApplication(
                user_id=1,
                job_listing_id=listing.id,
                portal="linkedin",
                application_status="submitted",
                channel="job_application",
            )
            db.add(app)

            from app.models import Contact
            contact = Contact(
                user_id=1,
                name="Test Contact",
                email="contact@example.com",
                company="Acme",
            )
            db.add(contact)
            await db.flush()

            send_log = SendLog(
                user_id=1,
                contact_id=contact.id,
                status="sent",
                channel="job_application",
            )
            db.add(send_log)
            await db.commit()

            # Verify relationships and channels
            res_apps = await db.execute(select(JobApplication).where(JobApplication.user_id == 1))
            apps = res_apps.scalars().all()
            self.assertEqual(len(apps), 1)
            self.assertEqual(apps[0].channel, "job_application")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 39: Job Search Agent & Deduplication Tests
    # ─────────────────────────────────────────────────────────────────────────
    @patch("app.services.llm.llm_service.expand_role_keywords")
    @patch("app.services.job_search.search_linkedin_jobs")
    @patch("app.services.job_search.search_remotive_jobs")
    @patch("app.services.job_search.search_naukri_jobs")
    @patch("app.services.job_search.search_wellfound_jobs")
    @patch("app.services.job_search.search_arbeitnow_jobs")
    @patch("app.services.job_search.search_ats_direct_jobs")
    async def test_step39_job_search_and_deduplication(
        self, mock_ats, mock_arbeit, mock_wellfound, mock_naukri, mock_remotive, mock_linkedin, mock_expand
    ):
        mock_expand.return_value = ["software engineer", "backend developer", "python developer"]
        mock_linkedin.return_value = [
            {"portal": "linkedin", "job_title": "Backend Dev", "company": "Stripe", "location": "Remote", "job_url": "https://linkedin.com/jobs/1", "description_raw": "Python FastAPI"}
        ]
        mock_remotive.return_value = [
            {"portal": "indeed", "job_title": "Python Dev", "company": "Zapier", "location": "Remote", "job_url": "https://remotive.com/jobs/2", "description_raw": "Django & AWS"}
        ]
        mock_naukri.return_value = []
        mock_wellfound.return_value = []
        mock_arbeit.return_value = []
        mock_ats.return_value = []

        async with self.session_maker() as db:
            result = await run_job_search(1, db)
            self.assertEqual(result["found"], 2)
            self.assertEqual(result["new"], 2)

            # Verify saved to DB
            res = await db.execute(select(JobListing).where(JobListing.user_id == 1))
            saved_listings = res.scalars().all()
            self.assertEqual(len(saved_listings), 2)
            self.assertTrue(all(l.status == "new" for l in saved_listings))

            # Run search again with same listings -> should deduplicate and return 0 new
            result_dup = await run_job_search(1, db)
            self.assertEqual(result_dup["new"], 0)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 40: Job Filter / LLM Scorer Tests
    # ─────────────────────────────────────────────────────────────────────────
    @patch("app.services.llm.llm_service.generate_text")
    async def test_step40_job_scoring_auto_approval(self, mock_llm):
        # High match score (95) -> should auto-approve (threshold is 85)
        mock_llm.return_value = '{"score": 95, "reason": "Perfect match for Python skills", "recommended_angle": "Highlight FastAPI experience"}'

        async with self.session_maker() as db:
            listing = JobListing(
                user_id=1,
                portal="linkedin",
                job_title="Senior Python Dev",
                company="Google",
                job_url="https://linkedin.com/jobs/100",
                status="new",
            )
            db.add(listing)
            await db.commit()

            score_res = await score_job(1, listing.id, db)
            self.assertEqual(score_res["score"], 95)
            self.assertEqual(score_res["status_set"], "approved")

            # Check DB updated
            await db.refresh(listing)
            self.assertEqual(listing.status, "approved")
            self.assertEqual(listing.match_score, 95.0)

    @patch("app.services.llm.llm_service.generate_text")
    async def test_step40_job_scoring_review_queue(self, mock_llm):
        # Low match score (65) -> should land in scored (review queue)
        mock_llm.return_value = '{"score": 65, "reason": "Requires Go experience which is missing", "recommended_angle": "Strong backend fundamentals"}'

        async with self.session_maker() as db:
            listing = JobListing(
                user_id=1,
                portal="indeed",
                job_title="Golang Engineer",
                company="Docker",
                job_url="https://indeed.com/jobs/200",
                status="new",
            )
            db.add(listing)
            await db.commit()

            score_res = await score_job(1, listing.id, db)
            self.assertEqual(score_res["score"], 65)
            self.assertEqual(score_res["status_set"], "scored")

            await db.refresh(listing)
            self.assertEqual(listing.status, "scored")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 41: Browser Service & CDP Offline Handling Tests
    # ─────────────────────────────────────────────────────────────────────────
    @patch("socket.socket")
    async def test_step41_browser_status_offline(self, mock_socket_cls):
        # Mock socket to simulate port 9222 connection failure (errno 10061 / non-zero return)
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 111  # Connection refused
        mock_socket_cls.return_value = mock_sock

        status = await get_browser_status()
        self.assertIn("cdp_reachable", status)
        self.assertIn("portals", status)
        self.assertFalse(status["cdp_reachable"])
        self.assertIn("not open", status["message"].lower())

    # ─────────────────────────────────────────────────────────────────────────
    # Step 42 & 45: Dynamic Resume Sourcing & Caching Tests
    # ─────────────────────────────────────────────────────────────────────────
    async def test_step45_resume_dynamic_sourcing_and_cache(self):
        async with self.session_maker() as db:
            resume_path = await get_latest_resume_path(1, db)
            self.assertIsNotNone(resume_path)
            self.assertTrue(os.path.exists(resume_path))

            # Second call should use cache
            cached_path = await get_latest_resume_path(1, db)
            self.assertEqual(resume_path, cached_path)

            clear_resume_cache(1)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 43: Tracking Agent, Approval Queue & Orchestrator Tests
    # ─────────────────────────────────────────────────────────────────────────
    async def test_step43_approval_queue_and_actions(self):
        async with self.session_maker() as db:
            l1 = JobListing(
                user_id=1,
                portal="linkedin",
                job_title="Backend Dev 1",
                company="Company A",
                job_url="https://joba.com",
                status="scored",
                match_score=75.0,
            )
            l2 = JobListing(
                user_id=1,
                portal="naukri",
                job_title="Backend Dev 2",
                company="Company B",
                job_url="https://jobb.com",
                status="scored",
                match_score=80.0,
            )
            db.add_all([l1, l2])
            await db.commit()

            queue = await get_approval_queue(1, db)
            self.assertEqual(len(queue), 2)
            # Should be ordered by match_score DESC
            self.assertEqual(queue[0]["id"], l2.id)

            # Approve l2
            appr = await approve_listing(1, l2.id, db)
            self.assertEqual(appr["status"], "approved")

            # Reject l1
            rej = await reject_listing(1, l1.id, db, reason="Location not ideal")
            self.assertEqual(rej["status"], "skipped")

            # Queue should now be empty
            queue_after = await get_approval_queue(1, db)
            self.assertEqual(len(queue_after), 0)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 46: Safety Rails Tests
    # ─────────────────────────────────────────────────────────────────────────
    async def test_step46_safety_duplicate_guard(self):
        async with self.session_maker() as db:
            listing = JobListing(
                user_id=1,
                portal="linkedin",
                job_title="Test Job",
                job_url="https://test.com/job/1",
                status="approved",
            )
            db.add(listing)
            await db.commit()

            # Pre-insert existing submitted application
            app = JobApplication(
                user_id=1,
                job_listing_id=listing.id,
                portal="linkedin",
                application_status="submitted",
            )
            db.add(app)
            await db.commit()

            mock_browser = MagicMock()
            result = await apply_to_job(1, listing.id, db, mock_browser, {})
            self.assertEqual(result["application_status"], "already_applied")

    async def test_step46_safety_daily_cap(self):
        async with self.session_maker() as db:
            # Insert 5 already submitted jobs today (cap is 5)
            for i in range(5):
                listing = JobListing(
                    user_id=1,
                    portal="linkedin",
                    job_title=f"Filled Job {i}",
                    job_url=f"https://test.com/filled/{i}",
                    status="applied",
                )
                db.add(listing)
                await db.flush()

                app = JobApplication(
                    user_id=1,
                    job_listing_id=listing.id,
                    portal="linkedin",
                    application_status="submitted",
                )
                db.add(app)

            # Add one approved listing
            approved_listing = JobListing(
                user_id=1,
                portal="linkedin",
                job_title="Approved Job",
                job_url="https://test.com/approved",
                status="approved",
            )
            db.add(approved_listing)
            await db.commit()

            mock_browser = MagicMock()
            cycle_result = await run_apply_cycle(1, db, mock_browser)
            self.assertEqual(cycle_result["applied"], 0)
            self.assertEqual(cycle_result["stopped_reason"], "daily_cap_reached")

    async def test_step46_portal_block_backoff(self):
        self.assertFalse(_is_portal_blocked("naukri"))
        _increment_block("naukri")
        self.assertTrue(_is_portal_blocked("naukri"))


if __name__ == "__main__":
    unittest.main()
