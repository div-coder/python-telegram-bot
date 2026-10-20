import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Exam, Subject, Chapter, SubType, Question

logger = logging.getLogger(__name__)


async def seed_database_if_empty(session: AsyncSession) -> None:
    """Check if exams table is empty. If yes, seed complete competitive exam taxonomy and questions."""
    result = await session.execute(select(Exam).limit(1))
    if result.scalars().first() is not None:
        logger.info("Database already contains data. Skipping initial seeding.")
        return

    logger.info("Seeding initial exam catalog, subjects, chapters, subtypes, and question bank...")

    # 1. EXAMS DEFINITION
    exams_data = [
        # SSC
        {"name": "SSC CGL (Combined Graduate Level)", "code": "SSC_CGL", "category": "SSC Exams"},
        {"name": "SSC CHSL (10+2 Higher Secondary)", "code": "SSC_CHSL", "category": "SSC Exams"},
        {"name": "SSC MTS & Havaldar", "code": "SSC_MTS", "category": "SSC Exams"},
        {"name": "SSC CPO (Sub-Inspector in Delhi Police & CAPFs)", "code": "SSC_CPO", "category": "SSC Exams"},
        {"name": "SSC Stenographer Grade C & D", "code": "SSC_STENO", "category": "SSC Exams"},
        {"name": "SSC Selection Post (Phase)", "code": "SSC_SELECTION", "category": "SSC Exams"},
        {"name": "SSC GD Constable", "code": "SSC_GD", "category": "SSC Exams"},
        # Banking
        {"name": "IBPS PO / Clerk", "code": "IBPS_PO_CLERK", "category": "Banking Exams"},
        {"name": "SBI PO / Clerk", "code": "SBI_PO_CLERK", "category": "Banking Exams"},
        {"name": "SBI CBO (Circle Based Officer)", "code": "SBI_CBO", "category": "Banking Exams"},
        {"name": "Insurance Exams (LIC AAO / NIACL)", "code": "INSURANCE_EXAMS", "category": "Banking Exams"},
        # Railways
        {"name": "RRB NTPC (Non-Technical Popular Categories)", "code": "RRB_NTPC", "category": "Railways"},
        {"name": "RRB Group D", "code": "RRB_GROUP_D", "category": "Railways"},
        {"name": "RRB ALP (Assistant Loco Pilot)", "code": "RRB_ALP", "category": "Railways"},
        {"name": "RRB Technician", "code": "RRB_TECH", "category": "Railways"},
        {"name": "RRB JE (Junior Engineer)", "code": "RRB_JE", "category": "Railways"},
        {"name": "RPF Constable & SI", "code": "RPF_CONSTABLE", "category": "Railways"},
        # UPSC
        {"name": "UPSC CSAT (Civil Services Paper-II)", "code": "UPSC_CSAT", "category": "UPSC CSAT"},
        # UPSSSC
        {"name": "UPSSSC PET (Preliminary Eligibility Test)", "code": "UPSSSC_PET", "category": "UPSSSC PET"},
    ]

    exam_models = {}
    for item in exams_data:
        exam = Exam(name=item["name"], code=item["code"], category=item["category"])
        session.add(exam)
        exam_models[item["code"]] = exam

    await session.flush()

    # 2. SUBJECTS, CHAPTERS, SUBTYPES & QUESTIONS DEFINITION
    # Let's populate rich questions for major exams (SSC CGL, Banking SBI/IBPS, Railways NTPC, UPSC CSAT, UPSSSC PET)

    # --- SSC CGL DATA ---
    ssc_cgl = exam_models["SSC_CGL"]

    # Subject 1: Quantitative Aptitude
    subj_quant = Subject(exam_id=ssc_cgl.id, name="Quantitative Aptitude", code="SSC_QUANT")
    session.add(subj_quant)
    await session.flush()

    # Chapter 1.1: Time & Work
    chap_tw = Chapter(subject_id=subj_quant.id, name="Time & Work")
    session.add(chap_tw)
    await session.flush()

    st_tw_eff = SubType(chapter_id=chap_tw.id, name="Efficiency Based")
    st_tw_wages = SubType(chapter_id=chap_tw.id, name="Wages Based")
    st_tw_alt = SubType(chapter_id=chap_tw.id, name="Alternate Days")
    st_tw_pipes = SubType(chapter_id=chap_tw.id, name="Pipes & Cisterns")
    session.add_all([st_tw_eff, st_tw_wages, st_tw_alt, st_tw_pipes])
    await session.flush()

    q_tw_1 = Question(
        chapter_id=chap_tw.id,
        sub_type_id=st_tw_eff.id,
        question_text="A is 50% more efficient than B. If B alone can do a piece of work in 24 days, in how many days can A and B together finish the same work?",
        options_raw=json.dumps(["9.6 days", "10 days", "12 days", "8.4 days"], ensure_ascii=False),
        correct_option_id=0,
        explanation="Let efficiency of B = 2 units/day.\nEfficiency of A = 2 + 50% of 2 = 3 units/day.\nTotal Work = Efficiency of B × Days = 2 × 24 = 48 units.\nCombined Efficiency of (A + B) = 3 + 2 = 5 units/day.\nTime taken together = Total Work / Combined Efficiency = 48 / 5 = 9.6 days.",
        shortcut_trick="⚡ Shortcut: Efficiency Ratio A : B = 3 : 2. Total work = 2 × 24 = 48 units. Together = 48 / (3 + 2) = 9.6 days.",
        difficulty="Easy"
    )

    q_tw_2 = Question(
        chapter_id=chap_tw.id,
        sub_type_id=st_tw_wages.id,
        question_text="A, B and C can do a work in 6, 8 and 12 days respectively. Doing that work together they get an amount of ₹ 1350. What is B's share?",
        options_raw=json.dumps(["₹ 450", "₹ 600", "₹ 300", "₹ 500"], ensure_ascii=False),
        correct_option_id=0,
        explanation="Wages are divided in ratio of work done (efficiency per day).\nEfficiencies:\nA = 1/6, B = 1/8, C = 1/12.\nLCM of (6, 8, 12) = 24 units.\nEfficiency Ratio A : B : C = 4 : 3 : 2.\nSum of ratio parts = 4 + 3 + 2 = 9 parts = ₹ 1350.\n1 part = 1350 / 9 = ₹ 150.\nB's share (3 parts) = 3 × 150 = ₹ 450.",
        shortcut_trick="⚡ Shortcut: Ratio of efficiencies = 24/6 : 24/8 : 24/12 = 4 : 3 : 2. B's share = (3 / 9) × 1350 = ₹ 450.",
        difficulty="Medium"
    )

    q_tw_3 = Question(
        chapter_id=chap_tw.id,
        sub_type_id=st_tw_alt.id,
        question_text="A can finish a work in 12 days and B in 18 days. If they work on alternate days starting with A on the first day, in how many days will the work be completed?",
        options_raw=json.dumps(["14 1/3 days", "15 days", "14 1/2 days", "13 2/3 days"], ensure_ascii=False),
        correct_option_id=0,
        explanation="Total work = LCM(12, 18) = 36 units.\nEfficiency of A = 36/12 = 3 units/day.\nEfficiency of B = 36/18 = 2 units/day.\nIn a 2-day cycle (A + B), work done = 3 + 2 = 5 units.\nIn 7 cycles (14 days), work done = 7 × 5 = 35 units.\nRemaining work = 36 - 35 = 1 unit.\nOn day 15, A works: Time taken for 1 unit = 1/3 day.\nTotal Time = 14 + 1/3 = 14 1/3 days.",
        shortcut_trick="⚡ Formula: Total units = 36. 2-day work = 5. (7 × 2) = 14 days for 35 units. Remainder 1 unit done by A in 1/3 day. Total = 14 1/3 days.",
        difficulty="Medium"
    )

    session.add_all([q_tw_1, q_tw_2, q_tw_3])

    # Chapter 1.2: Percentages & Profit-Loss
    chap_pct = Chapter(subject_id=subj_quant.id, name="Percentages & Profit-Loss")
    session.add(chap_pct)
    await session.flush()

    st_pct_disc = SubType(chapter_id=chap_pct.id, name="Discount & Mark-up")
    st_pct_succ = SubType(chapter_id=chap_pct.id, name="Successive Percentage")
    session.add_all([st_pct_disc, st_pct_succ])
    await session.flush()

    q_pct_1 = Question(
        chapter_id=chap_pct.id,
        sub_type_id=st_pct_disc.id,
        question_text="A shopkeeper marks an article 40% above the cost price and allows a discount of 25% on the marked price. What is his profit or loss percentage?",
        options_raw=json.dumps(["5% Profit", "5% Loss", "10% Profit", "15% Profit"], ensure_ascii=False),
        correct_option_id=0,
        explanation="Let CP = 100.\nMarked Price (MP) = 100 + 40 = 140.\nDiscount = 25% of 140 = (1/4) × 140 = 35.\nSelling Price (SP) = 140 - 35 = 105.\nProfit = SP - CP = 105 - 100 = 5% Profit.",
        shortcut_trick="⚡ Net Change Formula: x + y + (xy/100) = 40 + (-25) + (40 × -25)/100 = 15 - 10 = +5% (Profit).",
        difficulty="Easy"
    )

    q_pct_2 = Question(
        chapter_id=chap_pct.id,
        sub_type_id=st_pct_succ.id,
        question_text="If the price of petrol increases by 25%, by what percentage must a person reduce consumption so that the overall expenditure remains unchanged?",
        options_raw=json.dumps(["20%", "25%", "16.66%", "18%"], ensure_ascii=False),
        correct_option_id=0,
        explanation="Let initial price = 100, consumption = 100 => Expenditure = 10,000.\nNew price = 125.\nNew consumption = 10,000 / 125 = 80.\nReduction = 100 - 80 = 20%.",
        shortcut_trick="⚡ Standard Trick: If price rises by r%, reduction = [r / (100 + r)] × 100 = [25 / 125] × 100 = 20%.",
        difficulty="Easy"
    )

    session.add_all([q_pct_1, q_pct_2])

    # Chapter 1.3: Number System & Algebra
    chap_alg = Chapter(subject_id=subj_quant.id, name="Number System & Algebra")
    session.add(chap_alg)
    await session.flush()

    st_alg_ident = SubType(chapter_id=chap_alg.id, name="Algebraic Identities")
    st_num_div = SubType(chapter_id=chap_alg.id, name="Divisibility & Remainder")
    session.add_all([st_alg_ident, st_num_div])
    await session.flush()

    q_alg_1 = Question(
        chapter_id=chap_alg.id,
        sub_type_id=st_alg_ident.id,
        question_text="If x + (1/x) = 5, find the value of x³ + (1/x³).",
        options_raw=json.dumps(["110", "125", "115", "140"], ensure_ascii=False),
        correct_option_id=0,
        explanation="Formula: If x + 1/x = k, then x³ + 1/x³ = k³ - 3k.\nHere k = 5.\nx³ + 1/x³ = 5³ - 3(5) = 125 - 15 = 110.",
        shortcut_trick="⚡ Formula: k³ - 3k = 5³ - 15 = 110.",
        difficulty="Easy"
    )

    q_alg_2 = Question(
        chapter_id=chap_alg.id,
        sub_type_id=st_num_div.id,
        question_text="What is the remainder when (7¹⁹ + 2) is divided by 6?",
        options_raw=json.dumps(["3", "1", "2", "0"], ensure_ascii=False),
        correct_option_id=0,
        explanation="7 mod 6 = 1.\n(7¹⁹ + 2) mod 6 = (1¹⁹ + 2) mod 6 = (1 + 2) mod 6 = 3 mod 6 = 3.",
        shortcut_trick="⚡ Binomial theorem / Remainder trick: (6 + 1)¹⁹ + 2 ≡ 1 + 2 = 3 (mod 6).",
        difficulty="Easy"
    )

    session.add_all([q_alg_1, q_alg_2])

    # Subject 2: General Intelligence & Reasoning (SSC)
    subj_reason = Subject(exam_id=ssc_cgl.id, name="General Intelligence & Reasoning", code="SSC_REASON")
    session.add(subj_reason)
    await session.flush()

    chap_syl = Chapter(subject_id=subj_reason.id, name="Syllogism")
    chap_code = Chapter(subject_id=subj_reason.id, name="Coding-Decoding & Analogy")
    session.add_all([chap_syl, chap_code])
    await session.flush()

    st_syl_few = SubType(chapter_id=chap_syl.id, name="Only a few cases")
    session.add(st_syl_few)
    await session.flush()

    q_syl_1 = Question(
        chapter_id=chap_syl.id,
        sub_type_id=st_syl_few.id,
        question_text="Statements:\n1. Only a few Pens are Books.\n2. All Books are Pensils.\n\nConclusions:\nI. Some Pensils are Pens.\nII. All Pens being Books is a possibility.",
        options_raw=json.dumps(["Only I follows", "Only II follows", "Both I and II follow", "Neither follows"], ensure_ascii=False),
        correct_option_id=0,
        explanation="1. 'Only a few Pens are Books' means: Some Pens are Books AND Some Pens are NOT Books.\n2. Since All Books are Pensils, the intersection of Pens and Books automatically creates an intersection between Pens and Pensils. Thus, Conclusion I 'Some Pensils are Pens' definitely follows.\n3. Since Some Pens are NOT Books, 'All Pens being Books' is NOT possible. Thus, II does not follow.",
        shortcut_trick="⚡ Golden Rule for 'Only a few A are B': 'All A can be B' is ALWAYS False. 'All B can be A' can be True.",
        difficulty="Medium"
    )

    q_code_1 = Question(
        chapter_id=chap_code.id,
        sub_type_id=None,
        question_text="In a certain code language, if 'LEMON' is written as 'ELMNO' (alphabetical order), how will 'MANGO' be written?",
        options_raw=json.dumps(["AGMNO", "AGMON", "GAMNO", "AMNGO"], ensure_ascii=False),
        correct_option_id=0,
        explanation="The letters of 'LEMON' (L, E, M, O, N) are arranged in ascending alphabetical order: E, L, M, N, O.\nApplying the same logic to 'MANGO' (M, A, N, G, O):\nAlphabetical sort: A, G, M, N, O.",
        shortcut_trick="⚡ Logic: Alphabetical sort of constituent letters.",
        difficulty="Easy"
    )

    session.add_all([q_syl_1, q_code_1])

    # Subject 3: English Language & Comprehension (SSC)
    subj_eng = Subject(exam_id=ssc_cgl.id, name="English Language & Comprehension", code="SSC_ENG")
    session.add(subj_eng)
    await session.flush()

    chap_grammar = Chapter(subject_id=subj_eng.id, name="Spotting Errors & Grammar")
    chap_vocab = Chapter(subject_id=subj_eng.id, name="Idioms & Vocabulary")
    session.add_all([chap_grammar, chap_vocab])
    await session.flush()

    q_eng_1 = Question(
        chapter_id=chap_grammar.id,
        sub_type_id=None,
        question_text="Identify the segment in the sentence which contains a grammatical error:\n'Neither the teacher (A) / nor the students (B) / was present (C) / in the laboratory. (D)'",
        options_raw=json.dumps(["was present", "Neither the teacher", "nor the students", "in the laboratory"], ensure_ascii=False),
        correct_option_id=0,
        explanation="Rule of Proximity: When two subjects are joined by 'Neither... nor' or 'Either... or', the verb must agree in number with the subject closest to it.\nHere, the closest subject is 'the students' (plural). Therefore, the plural auxiliary verb 'were present' must be used instead of 'was present'.",
        shortcut_trick="⚡ Subject-Verb Rule: In 'Neither S1 nor S2', verb agrees with S2 (students -> were).",
        difficulty="Easy"
    )

    q_eng_2 = Question(
        chapter_id=chap_vocab.id,
        sub_type_id=None,
        question_text="Select the most appropriate meaning of the idiom: 'To spill the beans'",
        options_raw=json.dumps(["To reveal a secret prematurely", "To drop food by accident", "To cause chaos in a meeting", "To work extremely hard"], ensure_ascii=False),
        correct_option_id=0,
        explanation="'To spill the beans' is an English idiom meaning to divulge confidential information or reveal a secret, often indiscreetly or prematurely.",
        shortcut_trick="⚡ Frequent SSC PYQ Idiom: Spill the beans = Reveal a secret.",
        difficulty="Easy"
    )

    session.add_all([q_eng_1, q_eng_2])

    # Subject 4: General Awareness (SSC)
    subj_ga = Subject(exam_id=ssc_cgl.id, name="General Awareness", code="SSC_GA")
    session.add(subj_ga)
    await session.flush()

    chap_polity = Chapter(subject_id=subj_ga.id, name="Indian Polity & Constitution")
    chap_hist = Chapter(subject_id=subj_ga.id, name="Modern Indian History")
    session.add_all([chap_polity, chap_hist])
    await session.flush()

    q_pol_1 = Question(
        chapter_id=chap_polity.id,
        sub_type_id=None,
        question_text="Which Article of the Indian Constitution is termed as the 'Heart and Soul of the Constitution' by Dr. B.R. Ambedkar?",
        options_raw=json.dumps(["Article 32", "Article 21", "Article 19", "Article 14"], ensure_ascii=False),
        correct_option_id=0,
        explanation="Dr. B. R. Ambedkar called Article 32 (Right to Constitutional Remedies) the 'heart and soul of the Constitution' because it guarantees the right to move the Supreme Court by appropriate proceedings for the enforcement of Fundamental Rights.",
        shortcut_trick="⚡ Key Fact: Article 32 = Constitutional Remedies (Writs: Habeas Corpus, Mandamus, Prohibition, Certiorari, Quo-Warranto).",
        difficulty="Easy"
    )

    q_hist_1 = Question(
        chapter_id=chap_hist.id,
        sub_type_id=None,
        question_text="In which year was the historic Non-Cooperation Movement launched by Mahatma Gandhi?",
        options_raw=json.dumps(["1920", "1919", "1922", "1930"], ensure_ascii=False),
        correct_option_id=0,
        explanation="The Non-Cooperation Movement was launched on 1 August 1920 by Mahatma Gandhi following the Rowlatt Act and Jallianwala Bagh massacre, and was called off in February 1922 following the Chauri Chaura incident.",
        shortcut_trick="⚡ Timeline: 1919 (Rowlatt & Jallianwala) -> 1920 (Non-Cooperation launched) -> 1922 (Chauri Chaura).",
        difficulty="Easy"
    )

    session.add_all([q_pol_1, q_hist_1])

    # --- BANKING EXAMS DATA (IBPS / SBI) ---
    banking = exam_models["SBI_PO_CLERK"]

    subj_bank_quant = Subject(exam_id=banking.id, name="Quantitative Aptitude (Data Analysis)", code="BANK_QUANT")
    subj_bank_reason = Subject(exam_id=banking.id, name="Reasoning Ability & Puzzles", code="BANK_REASON")
    session.add_all([subj_bank_quant, subj_bank_reason])
    await session.flush()

    chap_quad = Chapter(subject_id=subj_bank_quant.id, name="Quadratic Equations")
    chap_di = Chapter(subject_id=subj_bank_quant.id, name="Data Interpretation & Series")
    session.add_all([chap_quad, chap_di])
    await session.flush()

    q_bank_1 = Question(
        chapter_id=chap_quad.id,
        sub_type_id=None,
        question_text="In the following questions, two equations (I) and (II) are given:\nI. x² - 7x + 12 = 0\nII. y² - 9y + 20 = 0\nDetermine the relationship between x and y:",
        options_raw=json.dumps(["x ≤ y", "x ≥ y", "x < y", "x = y or Relationship cannot be established"], ensure_ascii=False),
        correct_option_id=0,
        explanation="Equation I: x² - 7x + 12 = 0 => (x - 3)(x - 4) = 0 => x = +3, +4.\nEquation II: y² - 9y + 20 = 0 => (y - 4)(y - 5) = 0 => y = +4, +5.\nComparing roots:\nx = 3 < (4, 5)\nx = 4 = 4 and x = 4 < 5\nIn all cases, x ≤ y.",
        shortcut_trick="⚡ Sign Rule: For ax² - bx + c = 0, both roots are positive. Roots of x: (3, 4); Roots of y: (4, 5) => x ≤ y.",
        difficulty="Medium"
    )

    chap_puzzle = Chapter(subject_id=subj_bank_reason.id, name="Puzzles & Seating Arrangement")
    session.add(chap_puzzle)
    await session.flush()

    q_bank_2 = Question(
        chapter_id=chap_puzzle.id,
        sub_type_id=None,
        question_text="8 persons A, B, C, D, E, F, G, H are sitting around a circular table facing the centre. A sits 3rd to the left of B. C sits 2nd to the right of A. Who sits opposite to C if G is exactly between A and B?",
        options_raw=json.dumps(["H or E depending on arrangements", "D", "B", "F"], ensure_ascii=False),
        correct_option_id=0,
        explanation="Total seats = 8. B at position 0. A sits 3rd to left of B (position 5). G is between A and B. C sits 2nd to the right of A (position 7). The opposite position to 7 is (7 + 4)%8 = position 3.",
        shortcut_trick="⚡ Circular 8-person rule: Person opposite to position k is at (k + 4) mod 8.",
        difficulty="Hard"
    )

    session.add_all([q_bank_1, q_bank_2])

    # --- RAILWAYS EXAMS DATA (RRB NTPC / GROUP D) ---
    rrb = exam_models["RRB_NTPC"]

    subj_rrb_sci = Subject(exam_id=rrb.id, name="General Science", code="RRB_SCI")
    subj_rrb_math = Subject(exam_id=rrb.id, name="Mathematics", code="RRB_MATH")
    session.add_all([subj_rrb_sci, subj_rrb_math])
    await session.flush()

    chap_phy = Chapter(subject_id=subj_rrb_sci.id, name="Physics & Optics")
    session.add(chap_phy)
    await session.flush()

    q_rrb_1 = Question(
        chapter_id=chap_phy.id,
        sub_type_id=None,
        question_text="What is the unit of electric power in SI units?",
        options_raw=json.dumps(["Watt", "Joule", "Ampere", "Volt"], ensure_ascii=False),
        correct_option_id=0,
        explanation="Power = Work / Time (Joule / second) = Watt. 1 Watt = 1 Joule per second. Kilowatt-hour (kWh) is the commercial unit of electric energy.",
        shortcut_trick="⚡ SI Unit: Power (P) = V × I => Watt.",
        difficulty="Easy"
    )

    chap_speed = Chapter(subject_id=subj_rrb_math.id, name="Speed, Time & Distance")
    session.add(chap_speed)
    await session.flush()

    q_rrb_2 = Question(
        chapter_id=chap_speed.id,
        sub_type_id=None,
        question_text="A train 180 metres long is running at a speed of 54 km/h. How much time will it take to pass a telegraph post?",
        options_raw=json.dumps(["12 seconds", "10 seconds", "15 seconds", "18 seconds"], ensure_ascii=False),
        correct_option_id=0,
        explanation="Speed in m/s = 54 × (5/18) = 15 m/s.\nDistance to cross a point object = Length of train = 180 m.\nTime = Distance / Speed = 180 / 15 = 12 seconds.",
        shortcut_trick="⚡ Speed conversion: km/h × (5/18) = m/s. 54 × (5/18) = 15 m/s. Time = 180 / 15 = 12 sec.",
        difficulty="Easy"
    )

    session.add_all([q_rrb_1, q_rrb_2])

    # --- UPSC CSAT DATA ---
    csat = exam_models["UPSC_CSAT"]

    subj_csat = Subject(exam_id=csat.id, name="Logical Reasoning & Basic Numeracy", code="CSAT_LR_NUM")
    session.add(subj_csat)
    await session.flush()

    chap_csat_num = Chapter(subject_id=subj_csat.id, name="Basic Numeracy & Combinatorics")
    session.add(chap_csat_num)
    await session.flush()

    q_csat_1 = Question(
        chapter_id=chap_csat_num.id,
        sub_type_id=None,
        question_text="How many 3-digit natural numbers can be formed using the digits 1, 2, 3, 4, 5 without repetition such that the number is divisible by 5?",
        options_raw=json.dumps(["12", "20", "24", "16"], ensure_ascii=False),
        correct_option_id=0,
        explanation="A number is divisible by 5 if its unit digit is 5 or 0. Since 0 is not in the set {1, 2, 3, 4, 5}, the unit place must be fixed with 5 (1 choice).\nFor the hundred's place, we have remaining 4 digits (4 choices).\nFor the ten's place, we have remaining 3 digits (3 choices).\nTotal Numbers = 4 × 3 × 1 = 12 numbers.",
        shortcut_trick="⚡ CSAT Pattern: Fix last digit as '5' (1 way). Remaining 2 places filled by 4 available digits = 4P2 = 4 × 3 = 12.",
        difficulty="Medium"
    )

    session.add(q_csat_1)

    # --- UPSSSC PET DATA ---
    pet = exam_models["UPSSSC_PET"]

    subj_pet = Subject(exam_id=pet.id, name="Elementary Arithmetic & General Hindi", code="PET_MATH_HINDI")
    session.add(subj_pet)
    await session.flush()

    chap_pet_hindi = Chapter(subject_id=subj_pet.id, name="General Hindi (सामान्य हिन्दी)")
    session.add(chap_pet_hindi)
    await session.flush()

    q_pet_1 = Question(
        chapter_id=chap_pet_hindi.id,
        sub_type_id=None,
        question_text="'सूर्योदय' शब्द का सही संधि-विच्छेद क्या है?",
        options_raw=json.dumps(["सूर्य + उदय", "सूर्यो + दय", "सूर्य + दय", "सूर्य + ऊदय"], ensure_ascii=False),
        correct_option_id=0,
        explanation="सूर्योदय = सूर्य + उदय (गुण स्वर संधि)। नियम: अ/आ + उ/ऊ = ओ (य का 'अ' + 'उ' = 'ओ').",
        shortcut_trick="⚡ गुण संधि नियम: अ + उ = ओ (सूर्य + उदय = सूर्योदय).",
        difficulty="Easy"
    )

    session.add(q_pet_1)

    # Also duplicate/link subjects to other SSC & Banking exams for comprehensive coverage
    for code, ex in exam_models.items():
        if code.startswith("SSC_") and code != "SSC_CGL":
            # Add basic subjects for each SSC variant
            s_q = Subject(exam_id=ex.id, name="Quantitative Aptitude", code=f"{code}_QUANT")
            s_r = Subject(exam_id=ex.id, name="General Intelligence & Reasoning", code=f"{code}_REASON")
            s_e = Subject(exam_id=ex.id, name="English Language", code=f"{code}_ENG")
            s_g = Subject(exam_id=ex.id, name="General Awareness", code=f"{code}_GA")
            session.add_all([s_q, s_r, s_e, s_g])
            await session.flush()

            ch_q = Chapter(subject_id=s_q.id, name="Arithmetic & Math Practice")
            ch_r = Chapter(subject_id=s_r.id, name="Logical Reasoning Drills")
            session.add_all([ch_q, ch_r])
            await session.flush()

            q_gen = Question(
                chapter_id=ch_q.id,
                sub_type_id=None,
                question_text=f"Sample Practice Question for {ex.name}:\nIf 15 men can complete a project in 10 days, in how many days can 25 men complete the same project?",
                options_raw=json.dumps(["6 days", "8 days", "5 days", "7.5 days"], ensure_ascii=False),
                correct_option_id=0,
                explanation="M1 × D1 = M2 × D2\n15 × 10 = 25 × D2\n150 = 25 × D2 => D2 = 6 days.",
                shortcut_trick="⚡ Formula: M1 D1 = M2 D2 => 15 × 10 / 25 = 6 days.",
                difficulty="Easy"
            )
            session.add(q_gen)

        elif (code.startswith("IBPS_") or code.startswith("SBI_") or code == "INSURANCE_EXAMS") and code != "SBI_PO_CLERK":
            s_q = Subject(exam_id=ex.id, name="Quantitative Aptitude", code=f"{code}_QUANT")
            s_r = Subject(exam_id=ex.id, name="Reasoning Ability", code=f"{code}_REASON")
            s_e = Subject(exam_id=ex.id, name="English Language", code=f"{code}_ENG")
            session.add_all([s_q, s_r, s_e])
            await session.flush()

            ch_q = Chapter(subject_id=s_q.id, name="Speed Maths & Simplification")
            session.add(ch_q)
            await session.flush()

            q_bank_gen = Question(
                chapter_id=ch_q.id,
                sub_type_id=None,
                question_text=f"[{ex.name}] Find the approximate value:\n√624.98 + (14.99 × 4.02) = ?",
                options_raw=json.dumps(["85", "75", "95", "65"], ensure_ascii=False),
                correct_option_id=0,
                explanation="√625 = 25.\n15 × 4 = 60.\n25 + 60 = 85.",
                shortcut_trick="⚡ Approximation: √625 + (15 × 4) = 25 + 60 = 85.",
                difficulty="Easy"
            )
            session.add(q_bank_gen)

        elif code.startswith("RRB_") or code.startswith("RPF_") and code != "RRB_NTPC":
            s_g = Subject(exam_id=ex.id, name="General Science & Math", code=f"{code}_GEN")
            session.add(s_g)
            await session.flush()

            ch_g = Chapter(subject_id=s_g.id, name="Railway General Science")
            session.add(ch_g)
            await session.flush()

            q_rrb_gen = Question(
                chapter_id=ch_g.id,
                sub_type_id=None,
                question_text=f"[{ex.name}] Which vitamin is chemically known as Ascorbic Acid?",
                options_raw=json.dumps(["Vitamin C", "Vitamin A", "Vitamin B12", "Vitamin D"], ensure_ascii=False),
                correct_option_id=0,
                explanation="Vitamin C is chemically known as Ascorbic Acid. Its deficiency causes Scurvy.",
                shortcut_trick="⚡ Vitamin C = Ascorbic acid (found in citrus fruits).",
                difficulty="Easy"
            )
            session.add(q_rrb_gen)

    await session.commit()
    logger.info("Database seeding successfully completed!")
