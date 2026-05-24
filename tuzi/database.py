"""SQLite database layer for the Tuzi AI Tutor."""

import json
import sqlite3
from datetime import datetime
from typing import Optional

from .models import Curriculum, Lesson, TestQuestion, TestResult, UserProfile


SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT 'Student',
    depth TEXT NOT NULL,
    learning_style TEXT NOT NULL,
    communication_style TEXT NOT NULL,
    tone_style TEXT NOT NULL,
    reasoning_framework TEXT NOT NULL,
    emojis_enabled INTEGER NOT NULL DEFAULT 1,
    language TEXT NOT NULL DEFAULT 'English',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS curricula (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    depth TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lessons (
    lesson_id TEXT NOT NULL,
    curriculum_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    is_prerequisite INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (curriculum_id, lesson_id),
    FOREIGN KEY (curriculum_id) REFERENCES curricula(id)
);

CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    curriculum_id INTEGER NOT NULL,
    topic TEXT NOT NULL,
    questions TEXT NOT NULL,
    score REAL,
    completed_at TEXT NOT NULL,
    FOREIGN KEY (curriculum_id) REFERENCES curricula(id)
);
"""


class Database:
    """SQLite persistence for profiles, curricula, lessons, and test results."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        with sqlite3.connect(db_path) as conn:
            conn.executescript(SCHEMA)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ---- Profiles ----

    def get_profile(self) -> Optional[UserProfile]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM profiles ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            return UserProfile(
                id=row["id"],
                name=row["name"],
                depth=row["depth"],
                learning_style=row["learning_style"],
                communication_style=row["communication_style"],
                tone_style=row["tone_style"],
                reasoning_framework=row["reasoning_framework"],
                emojis_enabled=bool(row["emojis_enabled"]),
                language=row["language"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    def save_profile(self, profile: UserProfile) -> UserProfile:
        now = datetime.now().isoformat()
        profile.updated_at = datetime.now()
        with self._get_conn() as conn:
            if profile.id:
                conn.execute(
                    """UPDATE profiles SET name=?, depth=?, learning_style=?,
                       communication_style=?, tone_style=?, reasoning_framework=?,
                       emojis_enabled=?, language=?, updated_at=?
                       WHERE id=?""",
                    (
                        profile.name,
                        profile.depth.value,
                        profile.learning_style.value,
                        profile.communication_style.value,
                        profile.tone_style.value,
                        profile.reasoning_framework.value,
                        int(profile.emojis_enabled),
                        profile.language,
                        now,
                        profile.id,
                    ),
                )
            else:
                profile.created_at = datetime.now()
                now = profile.created_at.isoformat()
                cursor = conn.execute(
                    """INSERT INTO profiles (name, depth, learning_style,
                       communication_style, tone_style, reasoning_framework,
                       emojis_enabled, language, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        profile.name,
                        profile.depth.value,
                        profile.learning_style.value,
                        profile.communication_style.value,
                        profile.tone_style.value,
                        profile.reasoning_framework.value,
                        int(profile.emojis_enabled),
                        profile.language,
                        now,
                        now,
                    ),
                )
                profile.id = cursor.lastrowid or 0
            conn.commit()
        return profile

    # ---- Curricula ----

    def save_curriculum(self, curriculum: Curriculum) -> Curriculum:
        now = datetime.now().isoformat()
        curriculum.created_at = datetime.fromisoformat(now)
        with self._get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO curricula (topic, depth, created_at) VALUES (?, ?, ?)",
                (curriculum.topic, curriculum.depth, now),
            )
            curriculum.id = cursor.lastrowid or 0

            for lesson in curriculum.prerequisites:
                conn.execute(
                    """INSERT OR REPLACE INTO lessons
                       (lesson_id, curriculum_id, title, description, status, is_prerequisite)
                       VALUES (?, ?, ?, ?, ?, 1)""",
                    (lesson.id, curriculum.id, lesson.title, lesson.description, lesson.status),
                )

            for lesson in curriculum.main_curriculum:
                conn.execute(
                    """INSERT OR REPLACE INTO lessons
                       (lesson_id, curriculum_id, title, description, status, is_prerequisite)
                       VALUES (?, ?, ?, ?, ?, 0)""",
                    (lesson.id, curriculum.id, lesson.title, lesson.description, lesson.status),
                )

            conn.commit()
        return curriculum

    def get_curricula(self) -> list[Curriculum]:
        curricula: list[Curriculum] = []
        with self._get_conn() as conn:
            cur_rows = conn.execute(
                "SELECT * FROM curricula ORDER BY created_at DESC"
            ).fetchall()
            for crow in cur_rows:
                lessons = conn.execute(
                    "SELECT * FROM lessons WHERE curriculum_id=? ORDER BY lesson_id",
                    (crow["id"],),
                ).fetchall()
                prerequisites = []
                main_curriculum = []
                for lrow in lessons:
                    lesson = Lesson(
                        id=lrow["lesson_id"],
                        title=lrow["title"],
                        description=lrow["description"],
                        status=lrow["status"],
                    )
                    if lrow["is_prerequisite"]:
                        prerequisites.append(lesson)
                    else:
                        main_curriculum.append(lesson)
                curricula.append(
                    Curriculum(
                        id=crow["id"],
                        topic=crow["topic"],
                        depth=crow["depth"],
                        prerequisites=prerequisites,
                        main_curriculum=main_curriculum,
                        created_at=datetime.fromisoformat(crow["created_at"]),
                    )
                )
        return curricula

    def get_curriculum(self, curriculum_id: int) -> Optional[Curriculum]:
        with self._get_conn() as conn:
            crow = conn.execute(
                "SELECT * FROM curricula WHERE id=?", (curriculum_id,)
            ).fetchone()
            if crow is None:
                return None
            lessons = conn.execute(
                "SELECT * FROM lessons WHERE curriculum_id=? ORDER BY lesson_id",
                (curriculum_id,),
            ).fetchall()
            prerequisites = []
            main_curriculum = []
            for lrow in lessons:
                lesson = Lesson(
                    id=lrow["lesson_id"],
                    title=lrow["title"],
                    description=lrow["description"],
                    status=lrow["status"],
                )
                if lrow["is_prerequisite"]:
                    prerequisites.append(lesson)
                else:
                    main_curriculum.append(lesson)
            return Curriculum(
                id=crow["id"],
                topic=crow["topic"],
                depth=crow["depth"],
                prerequisites=prerequisites,
                main_curriculum=main_curriculum,
                created_at=datetime.fromisoformat(crow["created_at"]),
            )

    def update_lesson_status(
        self, curriculum_id: int, lesson_id: str, status: str
    ) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE lessons SET status=? WHERE curriculum_id=? AND lesson_id=?",
                (status, curriculum_id, lesson_id),
            )
            conn.commit()

    # ---- Test Results ----

    def save_test_result(self, result: TestResult) -> TestResult:
        now = datetime.now().isoformat()
        result.completed_at = datetime.fromisoformat(now)
        questions_json = json.dumps(
            [q.model_dump() for q in result.questions]
        )
        with self._get_conn() as conn:
            cursor = conn.execute(
                """INSERT INTO test_results
                   (curriculum_id, topic, questions, score, completed_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (result.curriculum_id, result.topic, questions_json, result.score, now),
            )
            result.id = cursor.lastrowid or 0
            conn.commit()
        return result

    def get_test_results(self, curriculum_id: int) -> list[TestResult]:
        results: list[TestResult] = []
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM test_results WHERE curriculum_id=? ORDER BY completed_at DESC",
                (curriculum_id,),
            ).fetchall()
            for row in rows:
                questions_data = json.loads(row["questions"])
                questions = [TestQuestion(**q) for q in questions_data]
                results.append(
                    TestResult(
                        id=row["id"],
                        curriculum_id=row["curriculum_id"],
                        topic=row["topic"],
                        questions=questions,
                        score=row["score"],
                        completed_at=datetime.fromisoformat(row["completed_at"]),
                    )
                )
        return results
