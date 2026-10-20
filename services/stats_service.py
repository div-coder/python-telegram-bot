import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import case, cast, desc, func, select, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Chapter, Question, Subject, User, UserAttempt

logger = logging.getLogger(__name__)


class StatsService:
    @staticmethod
    async def get_or_create_user(
        session: AsyncSession,
        user_id: int,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        target_exam: Optional[str] = None,
    ) -> User:
        """Fetch user or create if new, updating username/full_name."""
        user = await session.get(User, user_id)
        if not user:
            user = User(
                user_id=user_id,
                username=username,
                full_name=full_name,
                target_exam=target_exam,
            )
            session.add(user)
            await session.flush()
        else:
            updated = False
            if username and user.username != username:
                user.username = username
                updated = True
            if full_name and user.full_name != full_name:
                user.full_name = full_name
                updated = True
            if target_exam and user.target_exam != target_exam:
                user.target_exam = target_exam
                updated = True
            if updated:
                await session.flush()
        return user

    @staticmethod
    async def record_attempt(
        session: AsyncSession,
        user_id: int,
        question_id: int,
        selected_option: int,
        is_correct: bool,
        time_taken: float = 0.0,
        attempt_type: str = "DM_PRACTICE",
        username: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> UserAttempt:
        """Record an individual question attempt and ensure user exists."""
        await StatsService.get_or_create_user(
            session=session, user_id=user_id, username=username, full_name=full_name
        )

        attempt = UserAttempt(
            user_id=user_id,
            question_id=question_id,
            selected_option=selected_option,
            is_correct=is_correct,
            time_taken=time_taken,
            attempt_type=attempt_type,
            timestamp=datetime.utcnow(),
        )
        session.add(attempt)
        await session.flush()
        return attempt

    @staticmethod
    async def get_user_profile_stats(
        session: AsyncSession, user_id: int
    ) -> Dict[str, Any]:
        """Aggregate comprehensive performance analytics for a user."""
        user = await session.get(User, user_id)
        if not user:
            return {
                "user_id": user_id,
                "total_attempts": 0,
                "correct_attempts": 0,
                "accuracy": 0.0,
                "avg_speed": 0.0,
                "target_exam": "Not Set",
                "breakdown": [],
            }

        # Query attempt stats
        correct_case = case((UserAttempt.is_correct == True, 1), else_=0)
        stmt = select(
            func.count(UserAttempt.id).label("total"),
            func.sum(correct_case).label("correct"),
            func.avg(UserAttempt.time_taken).label("avg_time"),
        ).where(UserAttempt.user_id == user_id)

        res = (await session.execute(stmt)).first()
        total = res.total or 0
        correct = res.correct or 0
        avg_time = float(res.avg_time or 0.0)
        accuracy = (correct / total * 100.0) if total > 0 else 0.0

        # Breakdown by Subject
        sub_stmt = (
            select(
                Subject.name.label("subject_name"),
                func.count(UserAttempt.id).label("total"),
                func.sum(correct_case).label("correct"),
            )
            .join(Question, UserAttempt.question_id == Question.id)
            .join(Chapter, Question.chapter_id == Chapter.id)
            .join(Subject, Chapter.subject_id == Subject.id)
            .where(UserAttempt.user_id == user_id)
            .group_by(Subject.name)
            .order_by(desc("total"))
        )
        sub_results = (await session.execute(sub_stmt)).all()

        breakdown = []
        for row in sub_results:
            s_tot = row.total or 0
            s_cor = row.correct or 0
            s_acc = (s_cor / s_tot * 100.0) if s_tot > 0 else 0.0
            breakdown.append(
                {
                    "subject": row.subject_name,
                    "total": s_tot,
                    "correct": s_cor,
                    "accuracy": s_acc,
                }
            )

        return {
            "user_id": user_id,
            "username": user.username,
            "full_name": user.full_name,
            "target_exam": user.target_exam or "Not Configured",
            "total_attempts": total,
            "correct_attempts": correct,
            "accuracy": round(accuracy, 1),
            "avg_speed": round(avg_time, 1),
            "breakdown": breakdown,
        }

    @staticmethod
    async def get_leaderboard(
        session: AsyncSession, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Compute top performers across quizzes and channel polls."""
        correct_case = case((UserAttempt.is_correct == True, 1), else_=0)
        stmt = (
            select(
                User.user_id,
                User.username,
                User.full_name,
                func.count(UserAttempt.id).label("total_attempts"),
                func.sum(correct_case).label("correct_count"),
            )
            .join(UserAttempt, User.user_id == UserAttempt.user_id)
            .group_by(User.user_id, User.username, User.full_name)
            .having(func.count(UserAttempt.id) >= 1)
            .order_by(desc("correct_count"), desc("total_attempts"))
            .limit(limit)
        )

        rows = (await session.execute(stmt)).all()
        leaderboard = []
        for idx, r in enumerate(rows, 1):
            tot = r.total_attempts or 0
            cor = r.correct_count or 0
            acc = (cor / tot * 100.0) if tot > 0 else 0.0
            name = r.full_name or (f"@{r.username}" if r.username else f"User_{str(r.user_id)[-4:]}")
            leaderboard.append(
                {
                    "rank": idx,
                    "user_id": r.user_id,
                    "name": name,
                    "score": cor,
                    "total": tot,
                    "accuracy": round(acc, 1),
                }
            )
        return leaderboard
