"""
BidGenie AI - Session Manager
Tracks per-user project state, uploaded files, and bid data across conversations.
"""

import json
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict


@dataclass
class ProjectSession:
    """Holds all data for a single bid project session."""
    user_id: int
    project_name: str = ""
    client_name: str = ""
    trade_type: str = "Plumbing"
    project_type: str = "residential"  # residential | commercial | luxury
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # Uploaded files
    uploaded_files: List[Dict[str, str]] = field(default_factory=list)

    # Extracted data
    raw_text: str = ""
    scope_items: List[Dict[str, Any]] = field(default_factory=list)
    extracted_materials: List[str] = field(default_factory=list)
    extracted_measurements: List[Dict[str, str]] = field(default_factory=list)
    timeline_notes: str = ""

    # Pricing
    pricing_preset: str = "residential"
    custom_markup: float = 20.0
    custom_overhead: float = 10.0
    custom_profit: float = 15.0
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    total_cost: float = 0.0
    suggested_bid: float = 0.0

    # Proposal
    proposal_text: str = ""
    proposal_pdf_path: str = ""
    proposal_csv_path: str = ""
    terms_and_conditions: str = ""

    # State machine
    state: str = "idle"  # idle | intake | uploading | processing | pricing | reviewing | done
    awaiting_input: str = ""  # what we're waiting for from the user
    revision_count: int = 0

    # Company info (can be overridden per user)
    company_name: str = "Ace Plumbing"
    company_address: str = ""
    company_phone: str = ""
    company_email: str = ""
    company_license: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    def touch(self):
        self.updated_at = time.time()


class SessionManager:
    """Manages in-memory sessions for all active users."""

    def __init__(self):
        self._sessions: Dict[int, ProjectSession] = {}
        self._settings: Dict[int, Dict[str, Any]] = {}

    def get_session(self, user_id: int) -> Optional[ProjectSession]:
        return self._sessions.get(user_id)

    def create_session(self, user_id: int) -> ProjectSession:
        session = ProjectSession(user_id=user_id)
        self._sessions[user_id] = session
        return session

    def get_or_create(self, user_id: int) -> ProjectSession:
        if user_id not in self._sessions:
            return self.create_session(user_id)
        return self._sessions[user_id]

    def clear_session(self, user_id: int):
        if user_id in self._sessions:
            del self._sessions[user_id]

    def update_session(self, user_id: int, **kwargs) -> ProjectSession:
        session = self.get_or_create(user_id)
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
        session.touch()
        return session

    def get_settings(self, user_id: int) -> Dict[str, Any]:
        return self._settings.get(user_id, {
            "company_name": "Ace Plumbing",
            "company_address": "",
            "company_phone": "",
            "company_email": "",
            "company_license": "",
            "default_markup": 20.0,
            "default_overhead": 10.0,
            "default_profit": 15.0,
            "default_preset": "residential",
        })

    def save_settings(self, user_id: int, settings: Dict[str, Any]):
        existing = self.get_settings(user_id)
        existing.update(settings)
        self._settings[user_id] = existing

    def apply_settings_to_session(self, session: ProjectSession, user_id: int):
        settings = self.get_settings(user_id)
        session.company_name = settings.get("company_name", "Ace Plumbing")
        session.company_address = settings.get("company_address", "")
        session.company_phone = settings.get("company_phone", "")
        session.company_email = settings.get("company_email", "")
        session.company_license = settings.get("company_license", "")
        session.custom_markup = settings.get("default_markup", 20.0)
        session.custom_overhead = settings.get("default_overhead", 10.0)
        session.custom_profit = settings.get("default_profit", 15.0)
        session.pricing_preset = settings.get("default_preset", "residential")

    def all_sessions_summary(self) -> List[Dict]:
        return [
            {
                "user_id": s.user_id,
                "project": s.project_name,
                "client": s.client_name,
                "state": s.state,
                "files": len(s.uploaded_files),
            }
            for s in self._sessions.values()
        ]


# Global singleton
session_manager = SessionManager()
