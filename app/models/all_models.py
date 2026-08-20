import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, JSON, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    settings: Mapped[Optional["Setting"]] = relationship("Setting", back_populates="user", cascade="all, delete-orphan", uselist=False)
    resumes: Mapped[List["Resume"]] = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    context_profile: Mapped[Optional["ContextProfile"]] = relationship("ContextProfile", back_populates="user", cascade="all, delete-orphan", uselist=False)
    context_experiences: Mapped[List["ContextExperience"]] = relationship("ContextExperience", back_populates="user", cascade="all, delete-orphan")
    context_projects: Mapped[List["ContextProject"]] = relationship("ContextProject", back_populates="user", cascade="all, delete-orphan")
    context_achievements: Mapped[List["ContextAchievement"]] = relationship("ContextAchievement", back_populates="user", cascade="all, delete-orphan")
    job_preferences: Mapped[Optional["JobPreference"]] = relationship("JobPreference", back_populates="user", cascade="all, delete-orphan", uselist=False)
    templates: Mapped[List["Template"]] = relationship("Template", back_populates="user", cascade="all, delete-orphan")
    contacts: Mapped[List["Contact"]] = relationship("Contact", back_populates="user", cascade="all, delete-orphan")
    scrape_queues: Mapped[List["ScrapeQueue"]] = relationship("ScrapeQueue", back_populates="user", cascade="all, delete-orphan")
    send_logs: Mapped[List["SendLog"]] = relationship("SendLog", back_populates="user", cascade="all, delete-orphan")
    job_listings: Mapped[List["JobListing"]] = relationship("JobListing", back_populates="user", cascade="all, delete-orphan")
    job_applications: Mapped[List["JobApplication"]] = relationship("JobApplication", back_populates="user", cascade="all, delete-orphan")

class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    smtp_host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[Optional[int]] = mapped_column(Integer, default=587, nullable=True)
    smtp_user: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    smtp_password_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    imap_host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    imap_port: Mapped[Optional[int]] = mapped_column(Integer, default=993, nullable=True)
    imap_user: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    imap_password_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Google OAuth2 tokens for XOAUTH2 SMTP sending
    google_refresh_token_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    google_access_token_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    google_token_expiry: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)

    linkedin_cookie_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    send_mode: Mapped[str] = mapped_column(String(50), default="review") # auto, review, auto_pause_on_signal
    schedule_window: Mapped[str] = mapped_column(String(50), default="08:00-23:00")
    daily_target: Mapped[int] = mapped_column(Integer, default=50)

    # Job Application Agent settings
    job_agent_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    browser_type: Mapped[str] = mapped_column(String(50), default="brave") # brave, chrome, edge, custom
    browser_custom_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    browser_cdp_port: Mapped[int] = mapped_column(Integer, default=9222)

    user: Mapped["User"] = relationship("User", back_populates="settings")

class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    parsed_status: Mapped[str] = mapped_column(String(50), default="pending") # pending, done, failed

    user: Mapped["User"] = relationship("User", back_populates="resumes")

class ContextProfile(Base):
    __tablename__ = "context_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    role_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    grad_year: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="context_profile")

class ContextExperience(Base):
    __tablename__ = "context_experience"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    dates: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    one_liner: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stack: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    user: Mapped["User"] = relationship("User", back_populates="context_experiences")

class ContextProject(Base):
    __tablename__ = "context_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    dates: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    one_liner: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stack: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    link: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    live_link: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="context_projects")

class ContextAchievement(Base):
    __tablename__ = "context_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="context_achievements")

class JobPreference(Base):
    __tablename__ = "job_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    role_1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role_2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role_3: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    min_lpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_lpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    locations: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    experience_level: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Job Application Agent thresholds
    auto_apply_threshold: Mapped[int] = mapped_column(Integer, default=90)
    max_applications_per_day: Mapped[int] = mapped_column(Integer, default=20)

    user: Mapped["User"] = relationship("User", back_populates="job_preferences")

class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    subject_template: Mapped[str] = mapped_column(Text, nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="templates")

class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    job_posting_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    discovered_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    status: Mapped[str] = mapped_column(String(50), default="new")

    subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personalized_data: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    user: Mapped["User"] = relationship("User", back_populates="contacts")

class ScrapeQueue(Base):
    __tablename__ = "scrape_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    discovered_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    status: Mapped[str] = mapped_column(String(50), default="pending")

    user: Mapped["User"] = relationship("User", back_populates="scrape_queues")

class SendLog(Base):
    __tablename__ = "send_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    template_id: Mapped[Optional[int]] = mapped_column(ForeignKey("templates.id", ondelete="SET NULL"), nullable=True)
    sent_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    status: Mapped[str] = mapped_column(Text, default="sent")
    message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    channel: Mapped[str] = mapped_column(String(50), default="cold_mail")  # cold_mail | job_application

    user: Mapped["User"] = relationship("User", back_populates="send_logs")


class JobListing(Base):
    __tablename__ = "job_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    portal: Mapped[str] = mapped_column(String(50), nullable=False)  # linkedin/indeed/naukri/wellfound/arbeitnow/general
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    job_url: Mapped[str] = mapped_column(String(512), nullable=False)

    match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    match_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_angle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # new → scored → approved → applied → skipped
    status: Mapped[str] = mapped_column(String(50), default="new")

    discovered_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    applied_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="job_listings")
    applications: Mapped[List["JobApplication"]] = relationship("JobApplication", back_populates="job_listing", cascade="all, delete-orphan")


class JobApplication(Base):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_listing_id: Mapped[int] = mapped_column(ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False)

    portal: Mapped[str] = mapped_column(String(50), nullable=False)
    resume_version_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # submitted | failed | manual_needed | already_applied
    application_status: Mapped[str] = mapped_column(String(50), default="submitted")
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    channel: Mapped[str] = mapped_column(String(50), default="job_application")
    applied_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="job_applications")
    job_listing: Mapped["JobListing"] = relationship("JobListing", back_populates="applications")
