"""Semantic Evidence Index (Slice 8).

Provides lightweight relational persistence and semantic tagging/search
for EvidenceBundles using local SQLite.
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

from src.evidence.bundle import EvidenceBundle

class SemanticEvidenceIndex:
    def __init__(self, db_path: str = "data/evidence_index.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS bundles (
                    bundle_id TEXT PRIMARY KEY,
                    observed_at TEXT NOT NULL,
                    camera_id TEXT NOT NULL,
                    path_to_json TEXT NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS tags (
                    bundle_id TEXT,
                    tag_key TEXT,
                    tag_value TEXT,
                    FOREIGN KEY(bundle_id) REFERENCES bundles(bundle_id),
                    UNIQUE(bundle_id, tag_key)
                );
                
                CREATE TABLE IF NOT EXISTS entities (
                    bundle_id TEXT,
                    entity_id TEXT,
                    FOREIGN KEY(bundle_id) REFERENCES bundles(bundle_id),
                    UNIQUE(bundle_id, entity_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_bundles_time ON bundles(observed_at);
                CREATE INDEX IF NOT EXISTS idx_tags_key_val ON tags(tag_key, tag_value);
                CREATE INDEX IF NOT EXISTS idx_entities ON entities(entity_id);
            """)
            conn.commit()

    def index_bundle(self, bundle: EvidenceBundle, json_path: str):
        """Indices an EvidenceBundle for semantic search."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert Bundle
            cursor.execute("""
                INSERT OR REPLACE INTO bundles (bundle_id, observed_at, camera_id, path_to_json)
                VALUES (?, ?, ?, ?)
            """, (bundle.bundle_id, bundle.observed_at, bundle.source_camera, json_path))
            
            # Insert Tags
            if bundle.metadata:
                for k, v in bundle.metadata.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO tags (bundle_id, tag_key, tag_value)
                        VALUES (?, ?, ?)
                    """, (bundle.bundle_id, str(k), str(v)))
            
            # Additional semantic tags (e.g., situation, etc.)
            if bundle.situation_id:
                cursor.execute("""
                    INSERT OR REPLACE INTO tags (bundle_id, tag_key, tag_value)
                    VALUES (?, ?, ?)
                """, (bundle.bundle_id, "situation", str(bundle.situation_id)))
            
            # Insert Entities
            if bundle.entity_id:
                cursor.execute("""
                    INSERT OR REPLACE INTO entities (bundle_id, entity_id)
                    VALUES (?, ?)
                """, (bundle.bundle_id, bundle.entity_id))
                
            conn.commit()

    def search_bundles(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        camera_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        entity_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Searches for bundles matching semantic criteria.
        Returns a list of dictionaries with bundle info (path_to_json allows full load later).
        """
        query = "SELECT DISTINCT b.bundle_id, b.observed_at, b.camera_id, b.path_to_json FROM bundles b "
        joins = []
        where_clauses = []
        params = []
        
        if entity_id:
            joins.append("JOIN entities e ON b.bundle_id = e.bundle_id")
            where_clauses.append("e.entity_id = ?")
            params.append(entity_id)
            
        if tags:
            tag_idx = 0
            for k, v in tags.items():
                alias = f"t{tag_idx}"
                joins.append(f"JOIN tags {alias} ON b.bundle_id = {alias}.bundle_id")
                where_clauses.append(f"{alias}.tag_key = ? AND {alias}.tag_value = ?")
                params.extend([str(k), str(v)])
                tag_idx += 1
                
        if start_time:
            where_clauses.append("b.observed_at >= ?")
            params.append(start_time)
            
        if end_time:
            where_clauses.append("b.observed_at <= ?")
            params.append(end_time)
            
        if camera_id:
            where_clauses.append("b.camera_id = ?")
            params.append(camera_id)
            
        full_query = query + " ".join(joins)
        if where_clauses:
            full_query += " WHERE " + " AND ".join(where_clauses)
            
        full_query += " ORDER BY b.observed_at DESC"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(full_query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
