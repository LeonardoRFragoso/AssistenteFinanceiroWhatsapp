import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class OrganizationRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    FINANCE = "finance"
    VIEWER = "viewer"


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", foreign_keys=[owner_user_id], backref="owned_organizations")
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    role = Column(
        Enum(OrganizationRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=OrganizationRole.VIEWER,
    )
    active = Column(Boolean, default=True, nullable=False)
    invited_email = Column(String(255), nullable=True)
    invited_at = Column(DateTime(timezone=True), nullable=True)
    joined_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    organization = relationship("Organization", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], backref="organization_memberships")
