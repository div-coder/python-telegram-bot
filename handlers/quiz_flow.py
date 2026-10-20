import html
import time
from typing import Any, Dict, List, Optional
from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config import settings
from database.connection import get_db
from database.models import Chapter, Exam, Question, Subject, SubType
from keyboards.callbacks import (
    ChapterCB,
    CompCB,
    ExamCB,
    ModeCB,
    NavCB,
    QuizAnsCB,
    QuizNavCB,
    ScopeCB,
    SubjectCB,
)
from keyboards.inline_builders import (
    build_chapter_kb,
    build_composition_kb,
    build_exam_kb,
    build_interactive_quiz_kb,
    build_main_menu_kb,
    build_mode_kb,
    build_scope_kb,
    build_subject_kb,
)
from services.quiz_engine import QuizEngine
from services.stats_service import StatsService

router = Router(name="quiz_flow_router")


class QuizFSM(StatesGroup):
    selecting_exam = State()
    selecting_subject = State()
    selecting_scope = State()
    selecting_chapter = State()
    selecting_composition = State()
    selecting_mode = State()
    active_quiz = State()


# --- STEP 1: EXAM SELECTION ---

@router.message(Command("quiz"))
async def cmd_quiz_start(message: types.Message, state: FSMContext) -> None:
    """Entry point for /quiz command."""
    await state.clear()
    async with get_db() as session:
        result = await session.execute(select(Exam).order_by(Exam.id))
        exams = list(result.scalars().all())

    if not exams:
        await message.answer("⚠️ No exams configured in database. Please run seed data.")
        return

    await state.set_state(QuizFSM.selecting_exam)
    await message.answer(
        text="🎯 <b>Select Your Target Exam:</b>\n<i>Choose the competitive examination you are preparing for:</i>",
        reply_markup=build_exam_kb(exams),
        parse_mode="HTML",
    )


@router.callback_query(NavCB.filter(F.to == "exams"))
async def cb_show_exams(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Callback to display exams list."""
    await state.clear()
    async with get_db() as session:
        result = await session.execute(select(Exam).order_by(Exam.id))
        exams = list(result.scalars().all())

    await state.set_state(QuizFSM.selecting_exam)
    await callback.message.edit_text(
        text="🎯 <b>Select Your Target Exam:</b>\n<i>Choose the competitive examination you are preparing for:</i>",
        reply_markup=build_exam_kb(exams),
        parse_mode="HTML",
    )
    await callback.answer()


# --- STEP 2: SUBJECT / SECTION SELECTION ---

@router.callback_query(ExamCB.filter(F.action == "sel"))
async def cb_select_exam(
    callback: types.CallbackQuery, callback_data: ExamCB, state: FSMContext
) -> None:
    """Handle Exam selection -> fetch subjects."""
    exam_id = callback_data.exam_id
    async with get_db() as session:
        exam = await session.get(Exam, exam_id)
        if not exam:
            await callback.answer("Exam not found!", show_alert=True)
            return

        result = await session.execute(
            select(Subject).where(Subject.exam_id == exam_id).order_by(Subject.id)
        )
        subjects = list(result.scalars().all())

    if not subjects:
        await callback.answer(
            f"No subjects found for {exam.name} yet.", show_alert=True
        )
        return

    # Store in FSM data
    await state.update_data(
        exam_id=exam.id,
        exam_name=exam.name,
        exam_code=exam.code,
    )
    await state.set_state(QuizFSM.selecting_subject)

    await callback.message.edit_text(
        text=(
            f"🏛️ <b>Exam:</b> {html.escape(exam.name)}\n\n"
            f"📚 <b>Select Section / Subject:</b>\n"
            f"<i>Choose the section you want to practice:</i>"
        ),
        reply_markup=build_subject_kb(subjects),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(NavCB.filter(F.to == "subjects"))
async def cb_back_to_subjects(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Back button handler to return to subjects list."""
    data = await state.get_data()
    exam_id = data.get("exam_id")
    if not exam_id:
        await cb_show_exams(callback, state)
        return

    async with get_db() as session:
        exam = await session.get(Exam, exam_id)
        result = await session.execute(
            select(Subject).where(Subject.exam_id == exam_id).order_by(Subject.id)
        )
        subjects = list(result.scalars().all())

    await state.set_state(QuizFSM.selecting_subject)
    await callback.message.edit_text(
        text=(
            f"🏛️ <b>Exam:</b> {html.escape(exam.name if exam else 'Exam')}\n\n"
            f"📚 <b>Select Section / Subject:</b>\n"
            f"<i>Choose the section you want to practice:</i>"
        ),
        reply_markup=build_subject_kb(subjects),
        parse_mode="HTML",
    )
    await callback.answer()


# --- STEP 3: SCOPE SELECTION (Chapter-wise vs Full-Subject Section Test) ---

@router.callback_query(SubjectCB.filter(F.action == "sel"))
async def cb_select_subject(
    callback: types.CallbackQuery, callback_data: SubjectCB, state: FSMContext
) -> None:
    """Handle Subject selection -> prompt Chapter-wise vs Full Section."""
    subject_id = callback_data.subject_id
    async with get_db() as session:
        subject = await session.get(Subject, subject_id)
        if not subject:
            await callback.answer("Subject not found!", show_alert=True)
            return

    await state.update_data(
        subject_id=subject.id,
        subject_name=subject.name,
        subject_code=subject.code,
    )
    await state.set_state(QuizFSM.selecting_scope)

    data = await state.get_data()
    exam_name = data.get("exam_name", "Exam")

    await callback.message.edit_text(
        text=(
            f"🏛️ <b>Exam:</b> {html.escape(exam_name)}\n"
            f"📚 <b>Subject:</b> {html.escape(subject.name)}\n\n"
            f"🎯 <b>Select Test Scope:</b>\n"
            f"• <b>Chapter-wise:</b> Target specific chapters & sub-types\n"
            f"• <b>Full-Subject Section Test:</b> Full mock test covering all chapters\n"
        ),
        reply_markup=build_scope_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(NavCB.filter(F.to == "scope"))
async def cb_back_to_scope(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Back button handler to return to scope selection."""
    data = await state.get_data()
    exam_name = data.get("exam_name", "Exam")
    subject_name = data.get("subject_name", "Subject")

    await state.set_state(QuizFSM.selecting_scope)
    await callback.message.edit_text(
        text=(
            f"🏛️ <b>Exam:</b> {html.escape(exam_name)}\n"
            f"📚 <b>Subject:</b> {html.escape(subject_name)}\n\n"
            f"🎯 <b>Select Test Scope:</b>\n"
            f"• <b>Chapter-wise:</b> Target specific chapters & sub-types\n"
            f"• <b>Full-Subject Section Test:</b> Full mock test covering all chapters\n"
        ),
        reply_markup=build_scope_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# --- STEP 4: CHAPTER SELECTION (If Chapter-wise) OR MODE SELECTION (If Full Section) ---

@router.callback_query(ScopeCB.filter(F.action == "sel"))
async def cb_select_scope(
    callback: types.CallbackQuery, callback_data: ScopeCB, state: FSMContext
) -> None:
    """Handle Scope selection."""
    scope = callback_data.scope
    await state.update_data(scope=scope)
    data = await state.get_data()
    subject_id = data.get("subject_id")
    exam_code = data.get("exam_code", "")

    if scope == "full":
        # Full subject section test -> jump directly to Mode selection
        await state.set_state(QuizFSM.selecting_mode)
        await callback.message.edit_text(
            text=(
                f"📝 <b>Full-Subject Section Mock Test</b>\n"
                f"📚 <b>Subject:</b> {html.escape(data.get('subject_name', ''))}\n\n"
                f"⏱️ <b>Select Test Mode & Timer:</b>\n"
                f"• <b>Untimed Practice:</b> Learn with instant solutions & tricks\n"
                f"• <b>Timed Section Test:</b> Exam-level timer simulations\n"
            ),
            reply_markup=build_mode_kb(is_full_section=True, exam_code=exam_code),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Scope is "chap" -> load chapters for this subject
    async with get_db() as session:
        result = await session.execute(
            select(Chapter).where(Chapter.subject_id == subject_id).order_by(Chapter.id)
        )
        chapters = list(result.scalars().all())

    if not chapters:
        await callback.answer("No chapters found for this subject yet.", show_alert=True)
        return

    await state.set_state(QuizFSM.selecting_chapter)
    await callback.message.edit_text(
        text=(
            f"📚 <b>Subject:</b> {html.escape(data.get('subject_name', ''))}\n\n"
            f"📖 <b>Select Chapter / Topic:</b>\n"
            f"<i>Choose a specific chapter to drill down:</i>"
        ),
        reply_markup=build_chapter_kb(chapters),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(NavCB.filter(F.to == "chapters"))
async def cb_back_to_chapters(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Back button handler to return to chapters list."""
    data = await state.get_data()
    subject_id = data.get("subject_id")

    async with get_db() as session:
        result = await session.execute(
            select(Chapter).where(Chapter.subject_id == subject_id).order_by(Chapter.id)
        )
        chapters = list(result.scalars().all())

    await state.set_state(QuizFSM.selecting_chapter)
    await callback.message.edit_text(
        text=(
            f"📚 <b>Subject:</b> {html.escape(data.get('subject_name', ''))}\n\n"
            f"📖 <b>Select Chapter / Topic:</b>\n"
            f"<i>Choose a specific chapter to drill down:</i>"
        ),
        reply_markup=build_chapter_kb(chapters),
        parse_mode="HTML",
    )
    await callback.answer()


# --- STEP 5: QUESTION COMPOSITION (Type-wise vs Mix Questions) ---

@router.callback_query(ChapterCB.filter(F.action == "sel"))
async def cb_select_chapter(
    callback: types.CallbackQuery, callback_data: ChapterCB, state: FSMContext
) -> None:
    """Handle Chapter selection -> fetch sub-types and offer Type-wise vs Mix."""
    chapter_id = callback_data.chapter_id

    async with get_db() as session:
        chapter = await session.get(Chapter, chapter_id)
        if not chapter:
            await callback.answer("Chapter not found!", show_alert=True)
            return

        result = await session.execute(
            select(SubType).where(SubType.chapter_id == chapter_id).order_by(SubType.id)
        )
        sub_types = list(result.scalars().all())

    await state.update_data(
        chapter_id=chapter.id,
        chapter_name=chapter.name,
    )
    await state.set_state(QuizFSM.selecting_composition)

    await callback.message.edit_text(
        text=(
            f"📖 <b>Chapter:</b> {html.escape(chapter.name)}\n\n"
            f"🎯 <b>Question Composition:</b>\n"
            f"• <b>Type-wise:</b> Drill specific sub-types (e.g., Efficiency, Wages)\n"
            f"• <b>Mix Questions:</b> Comprehensive mix of all types in this chapter\n"
        ),
        reply_markup=build_composition_kb(sub_types),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(NavCB.filter(F.to == "comp"))
async def cb_back_to_comp(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Back button handler to return to composition."""
    data = await state.get_data()
    chapter_id = data.get("chapter_id")

    async with get_db() as session:
        chapter = await session.get(Chapter, chapter_id)
        result = await session.execute(
            select(SubType).where(SubType.chapter_id == chapter_id).order_by(SubType.id)
        )
        sub_types = list(result.scalars().all())

    await state.set_state(QuizFSM.selecting_composition)
    await callback.message.edit_text(
        text=(
            f"📖 <b>Chapter:</b> {html.escape(chapter.name if chapter else 'Chapter')}\n\n"
            f"🎯 <b>Question Composition:</b>\n"
            f"• <b>Type-wise:</b> Drill specific sub-types\n"
            f"• <b>Mix Questions:</b> Comprehensive mix of all types\n"
        ),
        reply_markup=build_composition_kb(sub_types),
        parse_mode="HTML",
    )
    await callback.answer()


# --- STEP 6: TIMER & MODE ENGINE SELECTION ---

@router.callback_query(CompCB.filter(F.action == "sel"))
async def cb_select_composition(
    callback: types.CallbackQuery, callback_data: CompCB, state: FSMContext
) -> None:
    """Handle Composition selection (Type-wise vs Mix) -> prompt Mode selection."""
    comp = callback_data.comp
    sub_type_id = callback_data.sub_type_id

    await state.update_data(
        comp=comp,
        sub_type_id=sub_type_id,
    )
    await state.set_state(QuizFSM.selecting_mode)
    data = await state.get_data()

    await callback.message.edit_text(
        text=(
            f"📖 <b>Chapter:</b> {html.escape(data.get('chapter_name', ''))}\n"
            f"🎯 <b>Drill Mode:</b> {'Type-wise' if comp == 'typ' else 'Mix Questions'}\n\n"
            f"⏱️ <b>Select Practice Mode & Timer:</b>\n"
            f"• <b>Untimed:</b> Step-by-step solutions, formulas & shortcut tricks\n"
            f"• <b>Timed Drill:</b> Fast speed test (30s / 45s / 60s per question)\n"
        ),
        reply_markup=build_mode_kb(is_full_section=False),
        parse_mode="HTML",
    )
    await callback.answer()


# --- STEP 7: QUIZ EXECUTION ENGINE (Untimed & Timed) ---

@router.callback_query(ModeCB.filter(F.action == "sel"))
async def cb_start_quiz_mode(
    callback: types.CallbackQuery, callback_data: ModeCB, state: FSMContext
) -> None:
    """Fetch questions from DB and start active quiz session."""
    mode = callback_data.mode
    timer = callback_data.timer
    data = await state.get_data()

    subject_id = data.get("subject_id")
    scope = data.get("scope", "chap")
    chapter_id = data.get("chapter_id")
    comp = data.get("comp", "mix")
    sub_type_id = data.get("sub_type_id")

    # Fetch questions
    async with get_db() as session:
        questions = await QuizEngine.get_questions_for_quiz(
            session=session,
            subject_id=subject_id,
            scope=scope,
            chapter_id=chapter_id,
            comp=comp,
            sub_type_id=sub_type_id,
            limit=25 if scope == "full" else 15,
        )

    if not questions:
        await callback.answer(
            "⚠️ No questions available for the chosen criteria. Please select another topic.",
            show_alert=True,
        )
        return

    # Serialize questions into state data
    serialized_questions = []
    for q in questions:
        serialized_questions.append(
            {
                "id": q.id,
                "question_text": q.question_text,
                "options": q.options,
                "correct_option_id": q.correct_option_id,
                "explanation": q.explanation,
                "shortcut_trick": q.shortcut_trick,
                "difficulty": q.difficulty,
                "chapter_name": q.chapter.name if q.chapter else "",
                "sub_type_name": q.sub_type.name if q.sub_type else "",
            }
        )

    await state.update_data(
        mode=mode,
        timer=timer,
        questions=serialized_questions,
        current_index=0,
        score=0,
        answers=[],
        start_time=time.time(),
        question_start_time=time.time(),
    )
    await state.set_state(QuizFSM.active_quiz)

    # Render first question
    first_q = serialized_questions[0]
    total_q = len(serialized_questions)

    # Format question text
    q_obj = Question(
        id=first_q["id"],
        question_text=first_q["question_text"],
        options_raw="",
        correct_option_id=first_q["correct_option_id"],
        explanation=first_q["explanation"],
        shortcut_trick=first_q["shortcut_trick"],
        difficulty=first_q["difficulty"],
    )
    q_obj.options = first_q["options"]

    card_text = QuizEngine.format_question_card(
        question=q_obj,
        current_index=0,
        total_questions=total_q,
        selected_option=None,
    )

    await callback.message.edit_text(
        text=card_text,
        reply_markup=build_interactive_quiz_kb(
            q_id=first_q["id"],
            options=first_q["options"],
            selected_opt=None,
            correct_opt=None,
        ),
        parse_mode="HTML",
    )
    await callback.answer()


# --- INTERACTIVE QUESTION ANSWERING & NAVIGATION ---

@router.callback_query(QuizAnsCB.filter())
async def cb_handle_quiz_answer(
    callback: types.CallbackQuery, callback_data: QuizAnsCB, state: FSMContext
) -> None:
    """Handle user clicking an answer option button."""
    data = await state.get_data()
    questions = data.get("questions", [])
    current_idx = data.get("current_index", 0)
    score = data.get("score", 0)
    answers = data.get("answers", [])
    q_start = data.get("question_start_time", time.time())

    if current_idx >= len(questions):
        await callback.answer("Quiz already completed.", show_alert=True)
        return

    curr_q = questions[current_idx]
    if curr_q["id"] != callback_data.q_id:
        await callback.answer("Question state mismatch.", show_alert=True)
        return

    selected_opt = callback_data.opt
    correct_opt = curr_q["correct_option_id"]
    is_correct = selected_opt == correct_opt
    time_taken = max(1.0, time.time() - q_start)

    if is_correct:
        score += 1

    answers.append(
        {
            "question_id": curr_q["id"],
            "selected_option": selected_opt,
            "is_correct": is_correct,
            "time_taken": time_taken,
        }
    )

    # Record attempt asynchronously in DB
    user = callback.from_user
    async with get_db() as session:
        await StatsService.record_attempt(
            session=session,
            user_id=user.id,
            question_id=curr_q["id"],
            selected_option=selected_opt,
            is_correct=is_correct,
            time_taken=time_taken,
            attempt_type="DM_PRACTICE",
            username=user.username,
            full_name=user.full_name,
        )

    await state.update_data(
        score=score,
        answers=answers,
    )

    has_next = current_idx + 1 < len(questions)

    # Format card with revealed answer & solution
    q_obj = Question(
        id=curr_q["id"],
        question_text=curr_q["question_text"],
        options_raw="",
        correct_option_id=curr_q["correct_option_id"],
        explanation=curr_q["explanation"],
        shortcut_trick=curr_q["shortcut_trick"],
        difficulty=curr_q["difficulty"],
    )
    q_obj.options = curr_q["options"]

    card_text = QuizEngine.format_question_card(
        question=q_obj,
        current_index=current_idx,
        total_questions=len(questions),
        selected_option=selected_opt,
    )

    await callback.message.edit_text(
        text=card_text,
        reply_markup=build_interactive_quiz_kb(
            q_id=curr_q["id"],
            options=curr_q["options"],
            selected_opt=selected_opt,
            correct_opt=correct_opt,
            has_next=has_next,
        ),
        parse_mode="HTML",
    )
    await callback.answer(
        "🎉 Correct!" if is_correct else "❌ Incorrect!"
    )


@router.callback_query(QuizNavCB.filter(F.action == "next"))
async def cb_next_question(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Proceed to next question or show scorecard."""
    data = await state.get_data()
    questions = data.get("questions", [])
    current_idx = data.get("current_index", 0) + 1

    if current_idx >= len(questions):
        # Quiz completed -> Show Scorecard!
        score = data.get("score", 0)
        total = len(questions)
        total_time = max(1.0, time.time() - data.get("start_time", time.time()))
        exam_name = data.get("exam_name", "Exam")
        subject_name = data.get("subject_name", "Subject")
        user_name = callback.from_user.full_name or callback.from_user.first_name

        scorecard_text = QuizEngine.format_scorecard(
            user_name=user_name,
            exam_name=exam_name,
            subject_name=subject_name,
            score=score,
            total=total,
            total_time_seconds=total_time,
            answers=data.get("answers", []),
        )

        await state.clear()
        is_admin = settings.is_admin(callback.from_user.id)
        await callback.message.edit_text(
            text=scorecard_text,
            reply_markup=build_main_menu_kb(is_admin=is_admin),
            parse_mode="HTML",
        )
        await callback.answer("Test completed!")
        return

    # Render next question
    await state.update_data(
        current_index=current_idx,
        question_start_time=time.time(),
    )
    next_q = questions[current_idx]

    q_obj = Question(
        id=next_q["id"],
        question_text=next_q["question_text"],
        options_raw="",
        correct_option_id=next_q["correct_option_id"],
        explanation=next_q["explanation"],
        shortcut_trick=next_q["shortcut_trick"],
        difficulty=next_q["difficulty"],
    )
    q_obj.options = next_q["options"]

    card_text = QuizEngine.format_question_card(
        question=q_obj,
        current_index=current_idx,
        total_questions=len(questions),
        selected_option=None,
    )

    await callback.message.edit_text(
        text=card_text,
        reply_markup=build_interactive_quiz_kb(
            q_id=next_q["id"],
            options=next_q["options"],
            selected_opt=None,
            correct_opt=None,
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(QuizNavCB.filter(F.action == "quit"))
async def cb_quit_quiz(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Quit active quiz early."""
    data = await state.get_data()
    answers = data.get("answers", [])
    score = data.get("score", 0)
    total_attempted = len(answers)

    await state.clear()
    is_admin = settings.is_admin(callback.from_user.id)

    msg = (
        f"🛑 <b>Practice Session Ended</b>\n\n"
        f"You answered <b>{total_attempted}</b> questions with <b>{score}</b> correct.\n"
        f"Your progress has been saved to your profile."
    )
    await callback.message.edit_text(
        text=msg,
        reply_markup=build_main_menu_kb(is_admin=is_admin),
        parse_mode="HTML",
    )
    await callback.answer("Practice ended")
