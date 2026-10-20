import html
from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from config import settings
from database.connection import get_db
from database.models import Exam, User
from keyboards.callbacks import NavCB
from keyboards.inline_builders import build_main_menu_kb
from services.stats_service import StatsService

router = Router(name="stats_router")


@router.message(Command("stats"))
async def cmd_stats(message: types.Message) -> None:
    """Display personal performance statistics and subject-wise accuracy."""
    user = message.from_user
    if not user:
        return

    async with get_db() as session:
        stats = await StatsService.get_user_profile_stats(session=session, user_id=user.id)

    name = html.escape(user.full_name or user.first_name)
    total = stats["total_attempts"]
    correct = stats["correct_attempts"]
    accuracy = stats["accuracy"]
    speed = stats["avg_speed"]
    target_exam = html.escape(stats["target_exam"])

    if total == 0:
        text = (
            f"📊 <b>Personal Performance Analytics</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Candidate:</b> {name}\n"
            f"🎯 <b>Target Exam:</b> {target_exam}\n\n"
            f"ℹ️ <i>You haven't attempted any questions yet!</i>\n"
            f"Start your first quiz session using /quiz or tap below."
        )
    else:
        text = (
            f"📊 <b>Personal Performance Analytics</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Candidate:</b> {name}\n"
            f"🎯 <b>Target Exam:</b> {target_exam}\n\n"
            f"📈 <b>Overall Metrics:</b>\n"
            f"• <b>Total Attempted:</b> <code>{total}</code>\n"
            f"• <b>Correct Answers:</b> <code>{correct}</code>\n"
            f"• <b>Accuracy Rate:</b> <code>{accuracy}%</code>\n"
            f"• <b>Average Speed:</b> <code>{speed}s / question</code>\n\n"
            f"📚 <b>Subject-wise Accuracy Breakdown:</b>\n"
        )
        for sub in stats["breakdown"]:
            sub_name = html.escape(sub["subject"])
            s_acc = sub["accuracy"]
            s_tot = sub["total"]
            s_cor = sub["correct"]
            bar = "🟩" if s_acc >= 75 else ("🟨" if s_acc >= 50 else "🟥")
            text += f"{bar} <b>{sub_name}:</b> {s_acc:.1f}% ({s_cor}/{s_tot})\n"

        text += (
            f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <i>Tip: Practice daily to improve your speed and accuracy!</i>"
        )

    is_admin = settings.is_admin(user.id)
    await message.answer(
        text=text,
        reply_markup=build_main_menu_kb(is_admin=is_admin),
        parse_mode="HTML",
    )


@router.callback_query(NavCB.filter(F.to == "stats"))
async def cb_stats(callback: types.CallbackQuery) -> None:
    """Callback query handler for stats."""
    user = callback.from_user
    async with get_db() as session:
        stats = await StatsService.get_user_profile_stats(session=session, user_id=user.id)

    name = html.escape(user.full_name or user.first_name)
    total = stats["total_attempts"]
    correct = stats["correct_attempts"]
    accuracy = stats["accuracy"]
    speed = stats["avg_speed"]
    target_exam = html.escape(stats["target_exam"])

    if total == 0:
        text = (
            f"📊 <b>Personal Performance Analytics</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Candidate:</b> {name}\n"
            f"🎯 <b>Target Exam:</b> {target_exam}\n\n"
            f"ℹ️ <i>You haven't attempted any questions yet!</i>\n"
            f"Start your first quiz session using /quiz or tap below."
        )
    else:
        text = (
            f"📊 <b>Personal Performance Analytics</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Candidate:</b> {name}\n"
            f"🎯 <b>Target Exam:</b> {target_exam}\n\n"
            f"📈 <b>Overall Metrics:</b>\n"
            f"• <b>Total Attempted:</b> <code>{total}</code>\n"
            f"• <b>Correct Answers:</b> <code>{correct}</code>\n"
            f"• <b>Accuracy Rate:</b> <code>{accuracy}%</code>\n"
            f"• <b>Average Speed:</b> <code>{speed}s / question</code>\n\n"
            f"📚 <b>Subject-wise Accuracy Breakdown:</b>\n"
        )
        for sub in stats["breakdown"]:
            sub_name = html.escape(sub["subject"])
            s_acc = sub["accuracy"]
            s_tot = sub["total"]
            s_cor = sub["correct"]
            bar = "🟩" if s_acc >= 75 else ("🟨" if s_acc >= 50 else "🟥")
            text += f"{bar} <b>{sub_name}:</b> {s_acc:.1f}% ({s_cor}/{s_tot})\n"

        text += (
            f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <i>Tip: Practice daily to improve your speed and accuracy!</i>"
        )

    is_admin = settings.is_admin(user.id)
    await callback.message.edit_text(
        text=text,
        reply_markup=build_main_menu_kb(is_admin=is_admin),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: types.Message) -> None:
    """Display channel and global top 10 leaderboard."""
    async with get_db() as session:
        lb = await StatsService.get_leaderboard(session=session, limit=10)

    if not lb:
        text = (
            f"🏆 <b>ExamPrep Channel Leaderboard</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>No attempts recorded on the leaderboard yet!</i>\n"
            f"Participate in channel quiz polls or take DM quizzes to rank first!"
        )
    else:
        text = (
            f"🏆 <b>ExamPrep Hall of Fame — Top 10 Performers</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for item in lb:
            rank = item["rank"]
            icon = medals.get(rank, f"<b>#{rank}</b>")
            name = html.escape(item["name"])
            score = item["score"]
            tot = item["total"]
            acc = item["accuracy"]
            text += f"{icon} {name}\n   └ Score: <b>{score} / {tot}</b> pts | Acc: <b>{acc}%</b>\n\n"

        text += (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 <i>Answer polls in the channel to climb the leaderboard!</i>"
        )

    is_admin = settings.is_admin(message.from_user.id) if message.from_user else False
    await message.answer(
        text=text,
        reply_markup=build_main_menu_kb(is_admin=is_admin),
        parse_mode="HTML",
    )


@router.callback_query(NavCB.filter(F.to == "lb"))
async def cb_leaderboard(callback: types.CallbackQuery) -> None:
    """Callback handler for leaderboard."""
    async with get_db() as session:
        lb = await StatsService.get_leaderboard(session=session, limit=10)

    if not lb:
        text = (
            f"🏆 <b>ExamPrep Channel Leaderboard</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>No attempts recorded on the leaderboard yet!</i>\n"
            f"Participate in channel quiz polls or take DM quizzes to rank first!"
        )
    else:
        text = (
            f"🏆 <b>ExamPrep Hall of Fame — Top 10 Performers</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for item in lb:
            rank = item["rank"]
            icon = medals.get(rank, f"<b>#{rank}</b>")
            name = html.escape(item["name"])
            score = item["score"]
            tot = item["total"]
            acc = item["accuracy"]
            text += f"{icon} {name}\n   └ Score: <b>{score} / {tot}</b> pts | Acc: <b>{acc}%</b>\n\n"

        text += (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 <i>Answer polls in the channel to climb the leaderboard!</i>"
        )

    is_admin = settings.is_admin(callback.from_user.id)
    await callback.message.edit_text(
        text=text,
        reply_markup=build_main_menu_kb(is_admin=is_admin),
        parse_mode="HTML",
    )
    await callback.answer()
