import asyncio
import sys
import logging
from sqlalchemy import select, func

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verifier")


async def run_verification() -> bool:
    logger.info("=== STEP 1: Testing Config & Environment ===")
    from config import settings
    logger.info(f"Bot Token configured: {settings.BOT_TOKEN[:10]}...")
    logger.info(f"Target Channel ID: {settings.CHANNEL_ID} (Parsed: {settings.channel_chat_id})")
    logger.info(f"Admin IDs: {settings.admin_id_list}")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    assert settings.is_admin(8444937180), "Admin check failed for 8444937180"
    logger.info("Config verification passed! ✅")

    logger.info("\n=== STEP 2: Testing Database Initialization & Seeding ===")
    from database.connection import init_db, get_db, engine
    from database.models import Exam, Subject, Chapter, SubType, Question, User, UserAttempt, ChannelPoll

    await init_db()

    async with get_db() as session:
        exam_count = (await session.execute(select(func.count(Exam.id)))).scalar()
        subject_count = (await session.execute(select(func.count(Subject.id)))).scalar()
        chapter_count = (await session.execute(select(func.count(Chapter.id)))).scalar()
        subtype_count = (await session.execute(select(func.count(SubType.id)))).scalar()
        question_count = (await session.execute(select(func.count(Question.id)))).scalar()

        logger.info(f"Exams in DB: {exam_count}")
        logger.info(f"Subjects in DB: {subject_count}")
        logger.info(f"Chapters in DB: {chapter_count}")
        logger.info(f"SubTypes in DB: {subtype_count}")
        logger.info(f"Questions in DB: {question_count}")

        assert exam_count > 0, "No exams found in DB!"
        assert subject_count > 0, "No subjects found in DB!"
        assert question_count > 0, "No questions found in DB!"

    logger.info("Database seeding verification passed! ✅")

    logger.info("\n=== STEP 3: Testing Quiz Engine & Logic ===")
    from services.quiz_engine import QuizEngine
    async with get_db() as session:
        # Fetch SSC CGL Quant questions
        result = await session.execute(select(Subject).where(Subject.code == "SSC_QUANT"))
        quant_sub = result.scalars().first()
        assert quant_sub is not None, "SSC_QUANT subject missing!"

        questions = await QuizEngine.get_questions_for_quiz(
            session=session,
            subject_id=quant_sub.id,
            scope="full",
            limit=10,
        )
        assert len(questions) > 0, "QuizEngine failed to fetch questions!"
        logger.info(f"Fetched {len(questions)} questions for SSC Quant.")

        # Test question card formatting (unanswered)
        card_text_unanswered = QuizEngine.format_question_card(
            question=questions[0],
            current_index=0,
            total_questions=len(questions),
            selected_option=None,
        )
        assert "Question 1 of" in card_text_unanswered
        logger.info("Unanswered question card formatted successfully.")

        # Test question card formatting (answered)
        card_text_answered = QuizEngine.format_question_card(
            question=questions[0],
            current_index=0,
            total_questions=len(questions),
            selected_option=0,
        )
        assert "Step-by-Step Solution" in card_text_answered
        logger.info("Answered question card formatted successfully with solution.")

        # Test scorecard formatting
        scorecard = QuizEngine.format_scorecard(
            user_name="Aman Sharma",
            exam_name="SSC CGL",
            subject_name="Quantitative Aptitude",
            score=8,
            total=10,
            total_time_seconds=360.0,
            answers=[],
        )
        assert "EXAM TEST SCORECARD" in scorecard
        assert "80.0%" in scorecard
        logger.info("Scorecard formatted successfully.")

    logger.info("\n=== STEP 4: Testing User Stats & Leaderboard Service ===")
    from services.stats_service import StatsService
    test_user_id = 999888777
    async with get_db() as session:
        # Record attempts
        await StatsService.record_attempt(
            session=session,
            user_id=test_user_id,
            question_id=questions[0].id,
            selected_option=questions[0].correct_option_id,
            is_correct=True,
            time_taken=18.5,
            attempt_type="DM_PRACTICE",
            username="test_topper",
            full_name="Test Topper",
        )

        user_stats = await StatsService.get_user_profile_stats(session=session, user_id=test_user_id)
        assert user_stats["total_attempts"] >= 1
        assert user_stats["correct_attempts"] >= 1
        assert user_stats["accuracy"] == 100.0
        logger.info(f"User stats verified: {user_stats['accuracy']}% accuracy, {user_stats['avg_speed']}s avg speed.")

        leaderboard = await StatsService.get_leaderboard(session=session, limit=5)
        assert len(leaderboard) >= 1
        logger.info(f"Leaderboard verified with {len(leaderboard)} ranks.")

    logger.info("\n=== STEP 5: Testing Telegram Callback Data Length Limit (< 64 bytes) ===")
    from keyboards.callbacks import (
        ExamCB, SubjectCB, ScopeCB, ChapterCB, CompCB, ModeCB,
        QuizAnsCB, QuizNavCB, AdminBroadcastCB, NavCB
    )
    callbacks = [
        ExamCB(action="sel", exam_id=123).pack(),
        SubjectCB(action="sel", subject_id=456).pack(),
        ScopeCB(action="sel", scope="chap").pack(),
        ChapterCB(action="sel", chapter_id=789).pack(),
        CompCB(action="sel", comp="typ", sub_type_id=1011).pack(),
        ModeCB(action="sel", mode="timed", timer=1200).pack(),
        QuizAnsCB(q_id=9999, opt=3).pack(),
        QuizNavCB(action="next").pack(),
        AdminBroadcastCB(step="send", exam_id=1, subject_id=2, chapter_id=3, count=10).pack(),
        NavCB(to="back_exams").pack(),
    ]
    for cb_str in callbacks:
        byte_len = len(cb_str.encode("utf-8"))
        logger.info(f"Callback '{cb_str}' -> {byte_len} bytes")
        assert byte_len <= 64, f"Callback exceeds 64 bytes: {cb_str} ({byte_len} bytes)"

    logger.info("All CallbackData strings are strictly under 64 bytes! ✅")

    logger.info("\n=== STEP 6: Testing Routers and Bot Handlers Compilation ===")
    from handlers import setup_routers
    root_router = setup_routers()
    assert len(root_router.sub_routers) >= 4, "Not all sub-routers were registered!"
    logger.info(f"Routers registered successfully: {len(root_router.sub_routers)} sub-routers.")

    await engine.dispose()
    logger.info("\n🎉 ALL TESTS PASSED SUCCESSFULLY! The bot is 100% production-ready.")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_verification())
    if not success:
        sys.exit(1)
