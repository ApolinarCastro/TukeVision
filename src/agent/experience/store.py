import sqlite3
import json
import logging
import os
from typing import List, Dict, Any, Optional
from src.agent.experience.contract import (
    ExperienceRecord, ExperienceRelation, ReauditCandidate, FailureExperience
)

logger = logging.getLogger("agent_experience_store")

class ExperienceStore:
    def __init__(self, db_path: str = "data/experience.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        c = self.conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS experiences (
            experience_id TEXT PRIMARY KEY,
            experience_type TEXT,
            problem TEXT,
            source TEXT,
            source_reference TEXT,
            pattern TEXT,
            evidence_refs TEXT,
            context TEXT,
            decision TEXT,
            outcome TEXT,
            lesson_learned TEXT,
            benefit TEXT,
            limitation TEXT,
            cost TEXT,
            dependencies TEXT,
            license TEXT,
            maturity TEXT,
            tukevision_component TEXT,
            confidence TEXT,
            created_at TEXT,
            updated_at TEXT,
            status TEXT,
            revisit_when TEXT
        )
        """)
        
        c.execute("""
        CREATE TABLE IF NOT EXISTS relations (
            relation_id TEXT PRIMARY KEY,
            source_experience_id TEXT,
            relation_type TEXT,
            target_experience_id TEXT,
            evidence_refs TEXT,
            created_at TEXT
        )
        """)
        
        c.execute("""
        CREATE TABLE IF NOT EXISTS reaudit_candidates (
            reaudit_id TEXT PRIMARY KEY,
            trigger_type TEXT,
            trigger_experience_id TEXT,
            affected_experience_ids TEXT,
            affected_components TEXT,
            affected_patterns TEXT,
            affected_decisions TEXT,
            reason TEXT,
            severity TEXT,
            created_at TEXT,
            status TEXT
        )
        """)
        
        c.execute("""
        CREATE TABLE IF NOT EXISTS failures (
            failure_id TEXT PRIMARY KEY,
            component TEXT,
            symptom TEXT,
            detected_at TEXT,
            root_cause TEXT,
            fix_reference TEXT,
            regression_test_reference TEXT,
            result TEXT,
            recurrence_signature TEXT,
            experience_id TEXT
        )
        """)
        self.conn.commit()

    def insert_experience(self, record: ExperienceRecord):
        # Sanitize secrets rule (Rule 77)
        def sanitize(text: str) -> str:
            if not text: return text
            # Trivial mock sanitizer
            return text.replace("password", "***").replace("token", "***")

        c = self.conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO experiences VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            record.experience_id, record.experience_type, sanitize(record.problem),
            record.source, record.source_reference, record.pattern,
            json.dumps(record.evidence_refs), sanitize(record.context),
            sanitize(record.decision), sanitize(record.outcome),
            sanitize(record.lesson_learned), record.benefit, record.limitation,
            record.cost, record.dependencies, record.license, record.maturity,
            record.tukevision_component, record.confidence, record.created_at,
            record.updated_at, record.status, record.revisit_when
        ))
        self.conn.commit()

    def get_experience(self, experience_id: str) -> Optional[ExperienceRecord]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM experiences WHERE experience_id = ?", (experience_id,))
        row = c.fetchone()
        if not row: return None
        
        d = dict(row)
        d["evidence_refs"] = json.loads(d["evidence_refs"])
        return ExperienceRecord(**d)
        
    def find_related_experiences(self, situation_type: str = None, component: str = None) -> List[ExperienceRecord]:
        c = self.conn.cursor()
        query = "SELECT * FROM experiences WHERE 1=1"
        params = []
        if situation_type:
            query += " AND pattern LIKE ?"
            params.append(f"%{situation_type}%")
        if component:
            query += " AND tukevision_component = ?"
            params.append(component)
            
        c.execute(query, params)
        res = []
        for row in c.fetchall():
            d = dict(row)
            d["evidence_refs"] = json.loads(d["evidence_refs"])
            res.append(ExperienceRecord(**d))
        return res

    def insert_relation(self, relation: ExperienceRelation):
        c = self.conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO relations VALUES (?, ?, ?, ?, ?, ?)
        """, (
            relation.relation_id, relation.source_experience_id, relation.relation_type,
            relation.target_experience_id, json.dumps(relation.evidence_refs), relation.created_at
        ))
        self.conn.commit()

    def insert_reaudit_candidate(self, candidate: ReauditCandidate):
        c = self.conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO reaudit_candidates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            candidate.reaudit_id, candidate.trigger_type, candidate.trigger_experience_id,
            json.dumps(candidate.affected_experience_ids), json.dumps(candidate.affected_components),
            json.dumps(candidate.affected_patterns), json.dumps(candidate.affected_decisions),
            candidate.reason, candidate.severity, candidate.created_at, candidate.status
        ))
        self.conn.commit()

    def insert_failure(self, failure: FailureExperience):
        c = self.conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO failures VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            failure.failure_id, failure.component, failure.symptom, failure.detected_at,
            failure.root_cause, failure.fix_reference, failure.regression_test_reference,
            failure.result, failure.recurrence_signature, failure.experience_id
        ))
        self.conn.commit()

    def find_known_failure(self, signature: str) -> Optional[FailureExperience]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM failures WHERE recurrence_signature = ?", (signature,))
        row = c.fetchone()
        if not row: return None
        return FailureExperience(**dict(row))
        
    def close(self):
        self.conn.close()
