# 🇮🇳 Telegram Quiz Bot for Indian Competitive Exams

A production-ready, asynchronous Telegram Quiz Bot built with **Python 3**, **aiogram 3.x**, and **SQLAlchemy (aiosqlite)**. Specially engineered for Indian government exams (**SSC, Banking, Railways, UPSC CSAT, UPSSSC PET**).

---

## 🌟 Key Features

1. **Conversational FSM Quiz Drill-Down (Direct Messages):**
   - **Exam Selection:** SSC (CGL, CHSL, MTS, CPO, Steno, Selection Post, GD), Banking (IBPS PO/Clerk, SBI PO/Clerk, CBO, Insurance), Railways (RRB NTPC, Group D, ALP, Tech, JE, RPF), UPSC CSAT, UPSSSC PET.
   - **Subject / Section Selection:** Dynamically loaded based on chosen exam.
   - **Scope Selection:** Chapter-wise practice vs Full-Subject Section Test.
   - **Chapter Selection:** Dynamically fetched from database.
   - **Question Composition:** Type-wise drills (e.g., Efficiency-based, Wages-based, Alternate days) vs Mix Questions.
   - **Timer & Mode Engine:**
     - *Untimed Practice:* Immediate feedback on tap with step-by-step solutions, formulas, and shortcut tricks.
     - *Timed Test:* 20-minute sectional mocks (~35s–60s/Q) and 30s / 45s / 60s fast drills.
   - **Comprehensive Scorecards:** Score, accuracy rate, speed (seconds/question), and topic breakdown.

2. **Admin Broadcast Engine (Telegram Channels):**
   - Interactive wizard (`/broadcast_quiz`, `/admin`) allowing admins to select Exam ➔ Subject ➔ Topic ➔ Question Count.
   - Pushes native Telegram Quiz Polls directly to `CHANNEL_ID`.
   - Listens to `poll_answer` events from channel members to compute channel leaderboards and accuracy metrics.

3. **Analytics & Performance Tracking:**
   - Personal accuracy analytics, streak, and subject-wise strength/weakness breakdown (`/stats`).
   - Channel Hall of Fame leaderboard (`/leaderboard`).

4. **Modular Architecture & Auto-Migration:**
   - Clean async repository pattern with SQLAlchemy 2.0.
   - Automatic database table creation and initial high-yield question seeding on startup.
   - Safe callback data strings (< 64 bytes) with `aiogram.filters.callback_data.CallbackData`.

---

## 📁 Directory Structure

```text
d:/TelegramQuizBot/
├── .env.example                # Environment variables template
├── .env                        # Active environment configuration
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
├── config.py                   # Pydantic Settings configuration loader
├── database/
│   ├── __init__.py
│   ├── connection.py           # Async engine & session factory
│   ├── models.py               # SQLAlchemy async ORM models
│   └── seed_data.py            # High-yield exam question bank & taxonomy
├── keyboards/
│   ├── __init__.py
│   ├── callbacks.py            # Compact aiogram CallbackData classes (<64 bytes)
│   └── inline_builders.py      # Dynamic InlineKeyboard builders with Back navigation
├── services/
│   ├── __init__.py
│   ├── quiz_engine.py          # Question querying, card formatting, scorecards
│   └── stats_service.py        # Attempt recording, analytics, and leaderboards
├── handlers/
│   ├── __init__.py
│   ├── start.py                # /start, /menu, /help, /cancel
│   ├── quiz_flow.py            # FSM drill-down engine & interactive DM quiz
│   ├── admin_broadcast.py      # Channel broadcast wizard & poll_answer listener
│   └── stats.py                # /stats and /leaderboard handlers
└── main.py                     # Bot entrypoint & lifecycle management
```

---

## ⚙️ Configuration (`.env`)

Create or edit `.env` in the root directory:

```env
# Telegram Bot Token from @BotFather
BOT_TOKEN=your_bot_token_here

# Target Telegram Channel ID for quiz broadcast (include -100 prefix)
CHANNEL_ID=-100xxxxxxxxxx

# Comma-separated Admin Telegram User IDs
ADMIN_IDS=123456789,987654321

# Async SQLite Database URL
DATABASE_URL=sqlite+aiosqlite:///quiz_bot.db

# Logging level
LOG_LEVEL=INFO
```

---

## 🚀 Quick Start & Running the Bot

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Bot
```bash
python main.py
```

*Note: On first run, the bot will automatically initialize the SQLite database schema and seed the initial question bank.*

---

## 🤖 Telegram Commands

### User Commands
- `/start` — Welcome screen and user profile setup
- `/menu` — Main navigation dashboard
- `/quiz` — Launch interactive Quiz Drill-Down
- `/stats` — View personal accuracy, speed, and subject breakdown
- `/leaderboard` — View Top 10 Channel Leaderboard
- `/help` — View user guide and documentation
- `/cancel` — Cancel current quiz/operation

### Admin Commands (Restricted to `ADMIN_IDS`)
- `/broadcast_quiz` — Launch interactive Channel Broadcast Wizard
- `/admin` — Open Admin Control Center
