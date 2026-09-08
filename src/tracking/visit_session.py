"""Anonymous visit session management.

Rules:
- visit_id format: VIS-000001 (stable, never reused after close)
- LIKELY_SCENE_FIXTURE tracks never receive a visit_id
- AMBIGUOUS_PERSON_LIKE tracks: visit_id=None until resolved
- Default role: UNKNOWN (never auto-assigned CUSTOMER)
- STAFF_CONFIRMED: excluded from customer analytics, but remains tracked
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class AnonymousVisitSession:
    visit_id: str
    started_at: float
    last_seen_at: float
    status: str = "ACTIVE"
    current_camera: str = ""
    local_track_refs: List[str] = field(default_factory=list)
    role: str = "UNKNOWN"
    role_confidence: float = 0.0
    entry_source: str = "UNKNOWN"
    exit_source: str = ""
    handoff_confidence: float = 0.0
    trajectory_refs: List[str] = field(default_factory=list)

    @property
    def customer_analytics_eligible(self) -> bool:
        """True when this visit contributes to customer analytics.

        Excluded:
            STAFF_CONFIRMED  — explicitly identified staff
            LIKELY_FIXTURE   — mannequin / static object
            AMBIGUOUS        — unresolved classification
        Eligible:
            CUSTOMER
            UNKNOWN          — unresolved but plausible visitor
            STAFF_CANDIDATE  — not yet confirmed
        """
        return self.role not in ("STAFF_CONFIRMED", "LIKELY_FIXTURE", "AMBIGUOUS")


class VisitSessionManager:
    def __init__(self):
        self._sessions: Dict[str, AnonymousVisitSession] = {}
        self._counter = 0
        self._track_to_visit: Dict[str, str] = {}
        # camera_id -> dict of ENTRY/EXIT zones (rects)
        self._zones: Dict[str, Dict[str, Tuple[int, int, int, int]]] = {}

    def _next_id(self) -> str:
        self._counter += 1
        return f"VIS-{self._counter:06d}"

    def get_visit_by_track(self, track_id: str) -> Optional[AnonymousVisitSession]:
        visit_id = self._track_to_visit.get(track_id)
        if visit_id:
            return self._sessions.get(visit_id)
        return None

    def handle_track(
        self,
        track_id: str,
        camera_id: str,
        bbox: Tuple[int, int, int, int],
        is_eligible_person: bool = False,
    ) -> Optional[AnonymousVisitSession]:
        """Create or update a visit session for an eligible person track.

        Only creates a visit for:
            PERSON_MOVING or PERSON_STATIONARY (is_eligible_person=True)

        Returns None for:
            LIKELY_SCENE_FIXTURE, AMBIGUOUS_PERSON_LIKE
        """
        if not is_eligible_person:
            return None

        now = time.time()
        session = self.get_visit_by_track(track_id)

        if not session:
            # Determine entry origin
            is_entry = self._check_entry(camera_id, bbox)
            entry_source = "ENTRY_OBSERVED" if is_entry else "UNKNOWN"
            session = self._create_visit(track_id, camera_id, entry_source)
        else:
            session.last_seen_at = now
            session.current_camera = camera_id
            # Check exit zone
            if self._check_exit(camera_id, bbox):
                self.close_visit(session.visit_id, exit_source=camera_id)

        return session

    def _create_visit(
        self,
        track_id: str,
        camera_id: str,
        entry_source: str,
    ) -> AnonymousVisitSession:
        """All visits use VIS-NNNNNN format. No provisional IDs."""
        visit_id = self._next_id()
        now = time.time()
        session = AnonymousVisitSession(
            visit_id=visit_id,
            started_at=now,
            last_seen_at=now,
            current_camera=camera_id,
            local_track_refs=[track_id],
            entry_source=entry_source,
            role="UNKNOWN",  # NEVER auto-assign CUSTOMER
        )
        self._sessions[visit_id] = session
        self._track_to_visit[track_id] = visit_id
        return session

    def handoff_track(
        self,
        old_track_id: str,
        new_track_id: str,
        new_camera_id: str,
        confidence: float,
    ):
        """Transfer a visit session to a new track (cross-camera handoff)."""
        visit_id = self._track_to_visit.get(old_track_id)
        if not visit_id or confidence < 0.8:
            # FALSE MERGE > MISSED HANDOFF -> treat as new
            self._create_visit(new_track_id, new_camera_id, entry_source="UNKNOWN")
            return

        session = self._sessions.get(visit_id)
        if session and session.status == "ACTIVE":
            session.local_track_refs.append(new_track_id)
            session.current_camera = new_camera_id
            session.handoff_confidence = confidence
            self._track_to_visit[new_track_id] = visit_id

    def close_visit(self, visit_id: str, exit_source: str = ""):
        if visit_id in self._sessions:
            self._sessions[visit_id].status = "VISIT_CLOSED"
            if exit_source:
                self._sessions[visit_id].exit_source = exit_source

    def set_role(self, visit_id: str, role: str):
        """Operator-driven role assignment."""
        if visit_id in self._sessions:
            self._sessions[visit_id].role = role

    def _check_entry(self, camera_id: str, bbox: Tuple[int, int, int, int]) -> bool:
        """Check if bbox intersects a configured entry zone for this camera.
        
        Without explicit zone configuration, defaults True (tracks entering
        frame from anywhere are treated as entry observations).
        """
        zone_config = self._zones.get(camera_id, {})
        entry_zone = zone_config.get("entry")
        if entry_zone is None:
            return True  # No entry zone configured → assume entry
        ex1, ey1, ex2, ey2 = entry_zone
        bx1, by1, bx2, by2 = bbox
        # Overlap check
        return not (bx2 < ex1 or bx1 > ex2 or by2 < ey1 or by1 > ey2)

    def _check_exit(self, camera_id: str, bbox: Tuple[int, int, int, int]) -> bool:
        """Check if bbox intersects a configured exit zone."""
        zone_config = self._zones.get(camera_id, {})
        exit_zone = zone_config.get("exit")
        if exit_zone is None:
            return False  # No exit zone configured → never auto-close
        ex1, ey1, ex2, ey2 = exit_zone
        bx1, by1, bx2, by2 = bbox
        return not (bx2 < ex1 or bx1 > ex2 or by2 < ey1 or by1 > ey2)

    def configure_zones(
        self,
        camera_id: str,
        entry: Optional[Tuple[int, int, int, int]] = None,
        exit: Optional[Tuple[int, int, int, int]] = None,
    ):
        """Configure entry/exit zones for a camera."""
        self._zones[camera_id] = {}
        if entry:
            self._zones[camera_id]["entry"] = entry
        if exit:
            self._zones[camera_id]["exit"] = exit
