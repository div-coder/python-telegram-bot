import html
import json
import logging
import random
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Chapter, Exam, Question, Subject, SubType

logger = logging.getLogger(__name__)


class QuizEngine:
    @staticmethod
    async def get_questions_for_quiz(
        session: AsyncSession,
        subject_id: int,
        scope: str = "chap",
        chapter_id: Optional[int] = None,
        comp: str = "mix",
        sub_type_id: Optional[int] = None,
        limit: int = 20,
    ) -> List[Question]:
        """Fetch and shuffle questions according to user selection criteria."""
        stmt = (
            select(Question)
            .join(Chapter, Question.chapter_id == Chapter.id)
            .where(Chapter.subject_id == subject_id)
            .options(
                selectinload(Question.chapter),
                selectinload(Question.sub_type),
            )
        )

        if scope == "chap" and chapter_id:
            stmt = stmt.where(Question.chapter_id == chapter_id)
            if comp == "typ" and sub_type_id and sub_type_id > 0:
                stmt = stmt.where(Question.sub_type_id == sub_type_id)

        # Order randomly
        stmt = stmt.order_by(func.random()).limit(limit)

        result = await session.execute(stmt)
        questions = list(result.scalars().all())

        # If question pool is smaller, return all available
        return questions

    @staticmethod
    async def get_questions_for_broadcast(
        session: AsyncSession,
        subject_id: int,
        chapter_id: Optional[int] = None,
        count: int = 5,
    ) -> List[Question]:
        """Fetch questions for channel broadcasting."""
        stmt = (
            select(Question)
            .join(Chapter, Question.chapter_id == Chapter.id)
            .where(Chapter.subject_id == subject_id)
            .options(
                selectinload(Question.chapter),
                selectinload(Question.sub_type),
            )
        )
        if chapter_id and chapter_id > 0:
            stmt = stmt.where(Question.chapter_id == chapter_id)

        stmt = stmt.order_by(func.random()).limit(count)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def format_question_card(
        question: Question,
        current_index: int,
        total_questions: int,
        selected_option: Optional[int] = None,
    ) -> str:
        """Format an interactive DM quiz question card with markdown."""
        opt_letters = ["A", "B", "C", "D"]
        options = question.options

        chapter_name = question.chapter.name if question.chapter else "General"
        sub_type_name = (
            f" ➔ {question.sub_type.name}"
            if question.sub_type and question.sub_type.name
            else ""
        )
        diff_emoji = {
            "Easy": "🟢 Easy",
            "Medium": "🟡 Medium",
            "Hard": "🔴 Hard",
        }.get(question.difficulty, "🟡 Medium")

        header = (
            f"📖 <b>Question {current_index + 1} of {total_questions}</b>\n"
            f"📂 <i>{chapter_name}{sub_type_name}</i> | {diff_emoji}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>{html.escape(question.question_text)}</b>\n\n"
        )

        options_text = ""
        for i, opt in enumerate(options):
            letter = opt_letters[i] if i < 4 else f"{i+1}"
            if selected_option is not None:
                if i == question.correct_option_id:
                    icon = "✅"
                elif i == selected_option:
                    icon = "❌"
                else:
                    icon = "◽"
                options_text += f"{icon} <b>{letter}.</b> {html.escape(opt)}\n"
            else:
                options_text += f"<b>{letter}.</b> {html.escape(opt)}\n"

        if selected_option is None:
            footer = "\n👉 <i>Tap an option below to submit your answer:</i>"
            return f"{header}{options_text}{footer}"

        # Answer revealed
        is_correct = selected_option == question.correct_option_id
        verdict = "🎉 <b>CORRECT!</b>" if is_correct else "❌ <b>INCORRECT!</b>"
        correct_letter = (
            opt_letters[question.correct_option_id]
            if question.correct_option_id < 4
            else f"{question.correct_option_id+1}"
        )

        solution_section = (
            f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{verdict} (Correct: <b>Option {correct_letter}</b>)\n\n"
            f"💡 <b>Step-by-Step Solution:</b>\n"
            f"{html.escape(question.explanation)}\n"
        )

        if question.shortcut_trick:
            solution_section += (
                f"\n⚡ <b>Shortcut / Formula Trick:</b>\n"
                f"<i>{html.escape(question.shortcut_trick)}</i>\n"
            )

        return f"{header}{options_text}{solution_section}"

    @staticmethod
    def format_scorecard(
        user_name: str,
        exam_name: str,
        subject_name: str,
        score: int,
        total: int,
        total_time_seconds: float,
        answers: List[Dict[str, Any]],
    ) -> str:
        """Format a rich end-of-test performance scorecard."""
        accuracy = (score / total * 100.0) if total > 0 else 0.0
        avg_speed = (total_time_seconds / total) if total > 0 else 0.0

        if accuracy >= 80:
            badge = "🏆 <b>OUTSTANDING PERFORMANCE!</b>"
            remark = "Excellent grasp of concepts! You are exam ready."
        elif accuracy >= 60:
            badge = "🔥 <b>GOOD ATTEMPT!</b>"
            remark = "Good foundation. Focus on speed and accuracy in weak areas."
        else:
            badge = "📚 <b>NEEDS REVISION</b>"
            remark = "Review shortcut tricks and solutions to master this topic."

        minutes = int(total_time_seconds // 60)
        seconds = int(total_time_seconds % 60)
        time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

        correct_count = score
        wrong_count = total - score

        msg = (
            f"🏁 <b>EXAM TEST SCORECARD</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Candidate:</b> {html.escape(user_name)}\n"
            f"🎯 <b>Exam:</b> {html.escape(exam_name)}\n"
            f"📚 <b>Subject:</b> {html.escape(subject_name)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Score:</b> <code>{correct_count} / {total}</code>\n"
            f"🎯 <b>Accuracy:</b> <code>{accuracy:.1f}%</code>\n"
            f"⏱️ <b>Total Time:</b> <code>{time_str}</code>\n"
            f"⚡ <b>Avg Speed:</b> <code>{avg_speed:.1f}s / Question</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{badge}\n"
            f"<i>{remark}</i>\n\n"
            f"✅ Correct: {correct_count} | ❌ Wrong: {wrong_count}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👉 <i>Use /menu to start another test or check /stats for overall analytics!</i>"
        )
        return msg

    @staticmethod
    def truncate_poll_explanation(text: str, max_chars: int = 195) -> str:
        """Truncate explanation text safely to fit Telegram Poll explanation limit (200 chars)."""
        if not text:
            return ""
        clean = text.replace("\n", " ").strip()
        if len(clean) <= max_chars:
            return clean
        return clean[: max_chars - 3] + "..."
