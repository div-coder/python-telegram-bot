import asyncio
import html
import logging
from typing import Optional
from aiogram import Bot, F, Router, types
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config import settings
from database.connection import get_db
from database.models import ChannelPoll, Chapter, Exam, Question, Subject, UserAttempt
from keyboards.callbacks import AdminBroadcastCB
from keyboards.inline_builders import build_admin_broadcast_kb
from services.quiz_engine import QuizEngine
from services.stats_service import StatsService

logger = logging.getLogger(__name__)
router = Router(name="admin_broadcast_router")


# --- ADMIN AUTHORIZATION GUARD ---

def is_authorized_admin(user_id: int) -> bool:
    return settings.is_admin(user_id)


# --- ADMIN COMMANDS & WIZARD ---

@router.message(Command("admin"))
@router.message(Command("broadcast_quiz"))
@router.message(Command("schedule_quiz"))
async def cmd_admin_broadcast(message: types.Message) -> None:
    """Admin entry point for channel quiz broadcast wizard."""
    user = message.from_user
    if not user or not is_authorized_admin(user.id):
        await message.answer("⛔ <i>Access Denied: This command is restricted to administrators.</i>", parse_mode="HTML")
        return

    async with get_db() as session:
        result = await session.execute(select(Exam).order_by(Exam.id))
        exams = list(result.scalars().all())

    if not exams:
        await message.answer("⚠️ No exams configured. Please seed the database first.")
        return

    text = (
        f"📢 <b>Telegram Channel Quiz Broadcast Engine</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>Target Channel:</b> <code>{settings.CHANNEL_ID}</code>\n\n"
        f"<b>Step 1 of 4:</b> Select the Exam category to broadcast:"
    )
    await message.answer(
        text=text,
        reply_markup=build_admin_broadcast_kb(step="exam", items=exams),
        parse_mode="HTML",
    )


@router.callback_query(AdminBroadcastCB.filter(F.step == "start"))
async def cb_broadcast_start(callback: types.CallbackQuery) -> None:
    """Start broadcast wizard via callback."""
    if not is_authorized_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    async with get_db() as session:
        result = await session.execute(select(Exam).order_by(Exam.id))
        exams = list(result.scalars().all())

    text = (
        f"📢 <b>Telegram Channel Quiz Broadcast Engine</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>Target Channel:</b> <code>{settings.CHANNEL_ID}</code>\n\n"
        f"<b>Step 1 of 4:</b> Select the Exam category to broadcast:"
    )
    await callback.message.edit_text(
        text=text,
        reply_markup=build_admin_broadcast_kb(step="exam", items=exams),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(AdminBroadcastCB.filter(F.step == "sub"))
async def cb_broadcast_select_exam(
    callback: types.CallbackQuery, callback_data: AdminBroadcastCB
) -> None:
    """Step 2: Select Subject for the chosen Exam."""
    if not is_authorized_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    exam_id = callback_data.exam_id
    async with get_db() as session:
        exam = await session.get(Exam, exam_id)
        result = await session.execute(
            select(Subject).where(Subject.exam_id == exam_id).order_by(Subject.id)
        )
        subjects = list(result.scalars().all())

    if not subjects:
        await callback.answer("No subjects found for this exam.", show_alert=True)
        return

    text = (
        f"📢 <b>Channel Broadcast Wizard</b>\n"
        f"🏛️ <b>Exam:</b> {html.escape(exam.name if exam else 'Exam')}\n\n"
        f"<b>Step 2 of 4:</b> Select Subject / Section to broadcast:"
    )
    await callback.message.edit_text(
        text=text,
        reply_markup=build_admin_broadcast_kb(
            step="sub", items=subjects, exam_id=exam_id
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(AdminBroadcastCB.filter(F.step == "ch"))
async def cb_broadcast_select_subject(
    callback: types.CallbackQuery, callback_data: AdminBroadcastCB
) -> None:
    """Step 3: Select Chapter or Mixed for the chosen Subject."""
    if not is_authorized_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    exam_id = callback_data.exam_id
    subject_id = callback_data.subject_id

    async with get_db() as session:
        subject = await session.get(Subject, subject_id)
        result = await session.execute(
            select(Chapter).where(Chapter.subject_id == subject_id).order_by(Chapter.id)
        )
        chapters = list(result.scalars().all())

    text = (
        f"📢 <b>Channel Broadcast Wizard</b>\n"
        f"📚 <b>Subject:</b> {html.escape(subject.name if subject else 'Subject')}\n\n"
        f"<b>Step 3 of 4:</b> Select Chapter/Topic to broadcast from:"
    )
    await callback.message.edit_text(
        text=text,
        reply_markup=build_admin_broadcast_kb(
            step="ch", items=chapters, exam_id=exam_id, subject_id=subject_id
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(AdminBroadcastCB.filter(F.step == "count"))
async def cb_broadcast_select_chapter(
    callback: types.CallbackQuery, callback_data: AdminBroadcastCB
) -> None:
    """Step 4: Select Question Count to broadcast."""
    if not is_authorized_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    exam_id = callback_data.exam_id
    subject_id = callback_data.subject_id
    chapter_id = callback_data.chapter_id

    async with get_db() as session:
        subject = await session.get(Subject, subject_id)
        chapter = (
            await session.get(Chapter, chapter_id) if chapter_id > 0 else None
        )

    topic_name = chapter.name if chapter else "All Chapters (Mixed)"
    text = (
        f"📢 <b>Channel Broadcast Wizard</b>\n"
        f"📚 <b>Subject:</b> {html.escape(subject.name if subject else 'Subject')}\n"
        f"📖 <b>Topic:</b> {html.escape(topic_name)}\n"
        f"🎯 <b>Target:</b> <code>{settings.CHANNEL_ID}</code>\n\n"
        f"<b>Step 4 of 4:</b> Select number of quiz polls to broadcast:"
    )
    await callback.message.edit_text(
        text=text,
        reply_markup=build_admin_broadcast_kb(
            step="count",
            exam_id=exam_id,
            subject_id=subject_id,
            chapter_id=chapter_id,
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(AdminBroadcastCB.filter(F.step == "send"))
async def cb_broadcast_execute(
    callback: types.CallbackQuery, callback_data: AdminBroadcastCB, bot: Bot
) -> None:
    """Execute broadcast to Telegram Channel."""
    if not is_authorized_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    exam_id = callback_data.exam_id
    subject_id = callback_data.subject_id
    chapter_id = callback_data.chapter_id
    count = callback_data.count

    await callback.message.edit_text("⏳ <i>Broadcasting quiz polls to channel...</i>", parse_mode="HTML")

    async with get_db() as session:
        questions = await QuizEngine.get_questions_for_broadcast(
            session=session,
            subject_id=subject_id,
            chapter_id=chapter_id,
            count=count,
        )

        if not questions:
            await callback.message.edit_text(
                "❌ <i>No matching questions found to broadcast.</i>", parse_mode="HTML"
            )
            return

        sent_count = 0
        for q in questions:
            try:
                # Format explanation safely within Telegram's limit (200 chars)
                exp_text = QuizEngine.truncate_poll_explanation(q.explanation)

                # Send native Telegram Quiz Poll to Channel
                poll_msg = await bot.send_poll(
                    chat_id=settings.channel_chat_id,
                    question=f"🎯 [{q.chapter.name if q.chapter else 'Quiz'}] {q.question_text[:280]}",
                    options=q.options[:10],
                    type="quiz",
                    correct_option_id=q.correct_option_id,
                    is_anonymous=False,  # Essential to capture poll_answer events and leaderboard stats
                    explanation=exp_text,
                    open_period=None,  # Or set timer e.g. 60
                )

                # Save mapping in database
                channel_poll = ChannelPoll(
                    poll_id=poll_msg.poll.id,
                    question_id=q.id,
                    channel_id=str(settings.CHANNEL_ID),
                    message_id=poll_msg.message_id,
                )
                session.add(channel_poll)
                sent_count += 1
                await asyncio.sleep(0.5)  # Telegram rate limit safety
            except Exception as e:
                logger.error(f"Failed to broadcast poll: {e}", exc_info=True)

        await session.commit()

    success_text = (
        f"✅ <b>Broadcast Successful!</b>\n\n"
        f"🚀 <b>{sent_count}</b> Quiz Poll{'s' if sent_count > 1 else ''} pushed to channel "
        f"<code>{settings.CHANNEL_ID}</code>.\n"
        f"📊 Member responses are automatically tracked for the Channel Leaderboard."
    )
    await callback.message.edit_text(text=success_text, parse_mode="HTML")
    await callback.answer("Broadcast Complete!")


@router.callback_query(AdminBroadcastCB.filter(F.step == "cancel"))
async def cb_broadcast_cancel(callback: types.CallbackQuery) -> None:
    """Cancel broadcast wizard."""
    await callback.message.edit_text("❌ <i>Broadcast wizard cancelled.</i>", parse_mode="HTML")
    await callback.answer("Cancelled")


# --- POLL ANSWER EVENT LISTENER ---

@router.poll_answer()
async def handle_channel_poll_answer(poll_answer: types.PollAnswer) -> None:
    """Handle poll_answer updates from Channel or Group quizzes to track accuracy & leaderboards."""
    poll_id = poll_answer.poll_id
    user = poll_answer.user
    selected_option_ids = poll_answer.option_ids

    if not selected_option_ids:
        # User retracted vote
        return

    selected_opt = selected_option_ids[0]

    async with get_db() as session:
        # Check if poll is registered
        result = await session.execute(
            select(ChannelPoll)
            .where(ChannelPoll.poll_id == poll_id)
            .options(selectinload(ChannelPoll.question))
        )
        channel_poll = result.scalars().first()

        if not channel_poll or not channel_poll.question:
            # Poll not tracked in DB
            return

        question = channel_poll.question
        is_correct = selected_opt == question.correct_option_id

        # Record attempt for channel leaderboard
        await StatsService.record_attempt(
            session=session,
            user_id=user.id,
            question_id=question.id,
            selected_option=selected_opt,
            is_correct=is_correct,
            time_taken=0.0,
            attempt_type="CHANNEL_POLL",
            username=user.username,
            full_name=user.full_name,
        )

        logger.info(
            f"Recorded channel poll attempt: User={user.id} ({user.username}), Q={question.id}, Correct={is_correct}"
        )
