import enum
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    worker = "worker"
    employer = "employer"
    both = "both"
    admin = "admin"


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"
    prefer_not_say = "prefer_not_say"


class RequiredGender(str, enum.Enum):
    any = "any"
    male = "male"
    female = "female"


class JobRequestStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    filled = "filled"
    cancelled = "cancelled"
    expired = "expired"


class ApplicationStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    cancelled_by_worker = "cancelled_by_worker"
    cancelled_by_employer = "cancelled_by_employer"


class NotificationType(str, enum.Enum):
    new_vacancy = "new_vacancy"
    application_status = "application_status"
    shift_reminder = "shift_reminder"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.worker)
    language_code: Mapped[str | None] = mapped_column(String(5))
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    worker: Mapped["Worker | None"] = relationship(back_populates="user", uselist=False)
    employer: Mapped["Employer | None"] = relationship(back_populates="user", uselist=False)
    preferences: Mapped["WorkerPreferences | None"] = relationship(back_populates="user", uselist=False)
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    gender: Mapped[Gender | None] = mapped_column(Enum(Gender, name="gender"))
    metro_station_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("metro_stations.id"))
    metro_radius_km: Mapped[int] = mapped_column(SmallInteger, default=0)
    min_hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    resume_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="worker")
    metro_station: Mapped["MetroStation | None"] = relationship(back_populates="workers")
    experiences: Mapped[list["WorkerExperience"]] = relationship(back_populates="worker")
    applications: Mapped[list["Application"]] = relationship(back_populates="worker")


class WorkerExperience(Base):
    __tablename__ = "worker_experiences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workers.id"))
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("job_categories.id"))
    role_title: Mapped[str] = mapped_column(String(200), nullable=False)
    duration_months: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    worker: Mapped["Worker"] = relationship(back_populates="experiences")
    category: Mapped["JobCategory"] = relationship(back_populates="experiences")


class Employer(Base):
    __tablename__ = "employers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    contact_person: Mapped[str | None] = mapped_column(String(200))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="employer")
    job_requests: Mapped[list["JobRequest"]] = relationship(back_populates="employer")


class JobCategory(Base):
    __tablename__ = "job_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name_ru: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("job_categories.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    parent: Mapped["JobCategory | None"] = relationship(remote_side=[id])
    job_requests: Mapped[list["JobRequest"]] = relationship(back_populates="category")
    experiences: Mapped[list["WorkerExperience"]] = relationship(back_populates="category")


class MetroStation(Base):
    __tablename__ = "metro_stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    line_name: Mapped[str] = mapped_column(String(100), nullable=False)
    lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    lon: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    workers: Mapped[list["Worker"]] = relationship(back_populates="metro_station")
    job_requests: Mapped[list["JobRequest"]] = relationship(back_populates="metro_station")


class JobRequest(Base):
    __tablename__ = "job_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employers.id"))
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("job_categories.id"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metro_station_id: Mapped[int] = mapped_column(Integer, ForeignKey("metro_stations.id"))
    address: Mapped[str | None] = mapped_column(String(300))
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    workers_needed: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    min_experience_months: Mapped[int | None] = mapped_column(SmallInteger)
    required_gender: Mapped[RequiredGender | None] = mapped_column(
        Enum(RequiredGender, name="required_gender")
    )
    min_age: Mapped[int | None] = mapped_column(SmallInteger)
    max_age: Mapped[int | None] = mapped_column(SmallInteger)
    dress_code: Mapped[str | None] = mapped_column(String(200))
    contact_info: Mapped[str | None] = mapped_column(Text)
    status: Mapped[JobRequestStatus] = mapped_column(
        Enum(JobRequestStatus, name="job_request_status"), default=JobRequestStatus.draft
    )
    post_to_groups: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_matching_workers: Mapped[bool] = mapped_column(Boolean, default=True)
    includes_lunch: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    employer: Mapped["Employer"] = relationship(back_populates="job_requests")
    category: Mapped["JobCategory"] = relationship(back_populates="job_requests")
    metro_station: Mapped["MetroStation"] = relationship(back_populates="job_requests")
    shift_slots: Mapped[list["ShiftSlot"]] = relationship(back_populates="job_request")
    applications: Mapped[list["Application"]] = relationship(back_populates="job_request")
    group_posts: Mapped[list["GroupPost"]] = relationship(back_populates="job_request")


class ShiftSlot(Base):
    __tablename__ = "shift_slots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_requests.id"))
    shift_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    slots_total: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    slots_filled: Mapped[int] = mapped_column(SmallInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job_request: Mapped["JobRequest"] = relationship(back_populates="shift_slots")
    applications: Mapped[list["Application"]] = relationship(back_populates="shift_slot")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("worker_id", "shift_slot_id", name="uq_worker_shift_slot"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workers.id"))
    job_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_requests.id"))
    shift_slot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shift_slots.id"))
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"), default=ApplicationStatus.pending
    )
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    worker: Mapped["Worker"] = relationship(back_populates="applications")
    job_request: Mapped["JobRequest"] = relationship(back_populates="applications")
    shift_slot: Mapped["ShiftSlot"] = relationship(back_populates="applications")


class WorkerPreferences(Base):
    __tablename__ = "worker_preferences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    category_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    metro_station_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    min_hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    max_distance_km: Mapped[int | None] = mapped_column(SmallInteger)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    quiet_hours_start: Mapped[time | None] = mapped_column(Time)
    quiet_hours_end: Mapped[time | None] = mapped_column(Time)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="preferences")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType, name="notification_type"))
    payload: Mapped[dict | None] = mapped_column(JSONB)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="notifications")


class TelegramGroup(Base):
    __tablename__ = "telegram_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    category_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    group_posts: Mapped[list["GroupPost"]] = relationship(back_populates="group")


class GroupPost(Base):
    __tablename__ = "group_posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_requests.id"))
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("telegram_groups.id"))
    message_id: Mapped[int | None] = mapped_column(BigInteger)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job_request: Mapped["JobRequest"] = relationship(back_populates="group_posts")
    group: Mapped["TelegramGroup"] = relationship(back_populates="group_posts")
