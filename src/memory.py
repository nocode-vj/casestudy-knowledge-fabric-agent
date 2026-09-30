"""Context & Memory Management: Constitution, History Compaction, Persistent & Async State."""

import asyncio
import json
import sqlite3
import time
from typing import Any, Dict, List
from src.observability import PIIRedactor, logger

SIEMENS_AGENT_CONSTITUTION = """
# CONSTITUTION: SIEMENS KNOWLEDGE FABRIC MODERNIZATION SYSTEM
1. PERSONA & MISSION:
   You are an Industrial Software Modernization Specialist operating within the Siemens
   Knowledge Fabric architecture on Google Cloud. Your mission is to modernize legacy
   industrial codebases ("slicing the elephant") with 100% traceability.
2. DOMAIN CONSTRAINTS & COMPLIANCE:
   - Industrial systems operate over 15 to 20+ year lifecycles under strict safety compliance.
   - Hallucinated or unverified code changes are operationally unacceptable.
   - Every proposed code change MUST trace back to a retrieved Spanner Graph node and
     a historical requirement ID (Jira, Confluence, or PDF manual).
3. OPERATIONAL PROTOCOL:
   - Never modify code monolithically. Always execute in sequence:
     (1) Graph Search -> (2) User Story -> (3) Architecture Impact -> (4) Task Breakdown -> (5) HITL Gate & Coding.
"""


class PersistentKnowledgeMemory:
    """
    Manages persistent conversational session state, sliding-window history compaction,
    and non-blocking asynchronous memory consolidation.
    """

    def __init__(self, db_path: str = ":memory:", max_token_budget: int = 2000):
        self.db_path = db_path
        self.max_token_budget = max_token_budget
        self.redactor = PIIRedactor()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_schema()
        self._background_tasks: set[asyncio.Task] = set()

    def _init_schema(self) -> None:
        cursor = self._conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS session_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                token_estimate INTEGER NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS compacted_memory_bank (
                session_id TEXT PRIMARY KEY,
                compacted_summary TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        self._conn.commit()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Approximates token count (4 chars ~= 1 token)."""
        return max(1, len(text) // 4)

    def append_turn_sync(self, session_id: str, role: str, content: str) -> None:
        """Persists a PII-scrubbed turn to the session database."""
        safe_content = self.redactor.redact_text(content)
        tokens = self.estimate_tokens(safe_content)
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO session_turns (session_id, role, content, token_estimate, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, role, safe_content, tokens, time.time()),
        )
        self._conn.commit()

    def get_compacted_context(self, session_id: str, sliding_window: int = 4) -> Dict[str, Any]:
        """
        Implements History Compaction: returns the consolidated memory bank summary plus
        only the most recent `sliding_window` turns to prevent context window bloat.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT compacted_summary FROM compacted_memory_bank WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        summary = row[0] if row else "No prior compacted summary."

        cursor.execute(
            """
            SELECT role, content, token_estimate
            FROM session_turns
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, sliding_window),
        )
        recent_rows = list(reversed(cursor.fetchall()))
        recent_turns: List[Dict[str, str]] = []
        running_tokens = self.estimate_tokens(summary)

        for role, content, token_est in recent_rows:
            if running_tokens + token_est <= self.max_token_budget:
                recent_turns.append({"role": role, "content": content})
                running_tokens += token_est

        return {
            "constitution": SIEMENS_AGENT_CONSTITUTION.strip(),
            "compacted_memory_summary": summary,
            "recent_sliding_window_turns": recent_turns,
            "active_token_count": running_tokens,
        }

    async def _consolidate_memory_async(self, session_id: str) -> None:
        """Expensive memory consolidation executed asynchronously to avoid blocking the UI."""
        await asyncio.sleep(0.05)  # Non-blocking async I/O yield
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT role, content FROM session_turns WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        )
        all_turns = cursor.fetchall()
        key_facts = [f"[{r}]: {c[:120]}" for r, c in all_turns]
        compacted_blob = self.redactor.redact_text(" | ".join(key_facts))

        cursor.execute(
            """
            INSERT INTO compacted_memory_bank (session_id, compacted_summary, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                compacted_summary = excluded.compacted_summary,
                updated_at = excluded.updated_at
            """,
            (session_id, compacted_blob, time.time()),
        )
        self._conn.commit()
        logger.info(
            "ASYNC_MEMORY_CONSOLIDATED",
            extra={"session_id": session_id, "turns_compacted": len(all_turns)},
        )

    def trigger_background_consolidation(self, session_id: str) -> asyncio.Task:
        """Schedules asynchronous memory compaction as a non-blocking background task."""
        task = asyncio.create_task(self._consolidate_memory_async(session_id))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task
