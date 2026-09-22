import io
import re
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from openpyxl.styles import Font, PatternFill, Alignment

# ---------- НАСТРОЙКА ----------
st.set_page_config(page_title="Журнал — Алгебра 10 А", page_icon="📘", layout="wide")

TOPICS = [
    "Повторение курса 9 класса", "Функции и графики",
    "Тригонометрические функции", "Тригонометрические уравнения",
    "Преобразование выражений", "Производная",
    "Применение производной", "Итоговое повторение",
]

QUESTION_BANK = {
    "Повторение курса 9 класса": [
        "Решите уравнение x² − 5x + 6 = 0.",
        "Упростите выражение (a+b)² − (a−b)².",
        "Найдите область определения функции y = √(x−3).",
        "Решите неравенство 2x − 7 > 0.",
        "Постройте график y = |x| и опишите его свойства.",
    ],
    "Функции и графики": [
        "Найдите область значений функции y = x² − 4x + 5.",
        "Определите чётность функции y = x³ − x.",
        "Постройте график y = 1/x и опишите его асимптоты.",
        "Найдите нули функции y = x² − 9.",
        "Как из графика y = f(x) получить y = f(x−2)+3?",
    ],
    "Тригонометрические функции": [
        "Вычислите sin(π/6) + cos(π/3).",
        "Определите период функции y = sin(2x).",
        "Найдите область значений y = 3cos x − 1.",
        "Постройте график y = tg x на [0; 2π].",
        "Выразите cos²x через sin²x.",
    ],
    "Тригонометрические уравнения": [
        "Решите уравнение sin x = 1/2.",
        "Решите уравнение cos x = 0.",
        "Решите уравнение tg x = √3.",
        "Решите 2sin²x − sin x − 1 = 0.",
        "Решите sin x + cos x = 0.",
    ],
    "Преобразование выражений": [
        "Упростите (sin x + cos x)².",
        "Докажите тождество 1 + tg²x = 1/cos²x.",
        "Упростите sin(π − x).",
        "Разложите на множители sin²x − cos²x.",
        "Вычислите cos 2x, если sin x = 0,6.",
    ],
    "Производная": [
        "Найдите производную f(x)=x³−2x.",
        "Найдите производную f(x)=sin x · x.",
        "Найдите производную f(x)=(2x+1)⁵.",
        "Найдите производную f(x)=ln x + eˣ.",
        "Найдите f′(1), если f(x)=x²+3x.",
    ],
    "Применение производной": [
        "Найдите точки экстремума f(x)=x³−3x.",
        "Найдите промежутки возрастания f(x)=x²−4x.",
        "Напишите уравнение касательной к y=x² в точке x=1.",
        "Найдите наибольшее значение f(x)=−x²+4x на [0;3].",
        "Исследуйте функцию y=x³−3x² и постройте график.",
    ],
    "Итоговое повторение": [
        "Решите систему: { x+y=5; x−y=1 }.",
        "Упростите (a−b)(a+b) − a².",
        "Решите уравнение 2ˣ = 8.",
        "Найдите производную f(x)=cos x.",
        "Решите неравенство x² − 4 < 0.",
    ],
}

# ---------- OCR ----------
@st.cache_data(show_spinner=False)
def parse_pdf(file_bytes: bytes) -> list:
    import pdfplumber
    import pytesseract
    from pdf2image import convert_from_bytes

    name_rx = re.compile(r"([А-ЯЁӘҒҚҢӨҰҮҺІ][а-яёәғқңөұүһі\-]+(?:\s+[А-ЯЁӘҒҚҢӨҰҮҺІ][а-яёәғқңөұүһі\-]+){1,3})")
    mark_rx = re.compile(r"^(1|2|3|4|5|10|А|С|Н)$", re.IGNORECASE)

    def extract(text):
        out, seen = [], set()
        for line in text.splitlines():
            line = line.strip()
            if not line or re.search(r"учител|мұғалім|teacher|тоқсан|четверть", line, re.I):
                continue
            if re.fullmatch(r"[\d\s\.\-\/№#]+", line):
                continue
            m = name_rx.search(line)
            if not m:
                continue
            name = m.group(1).strip()
            if len(name.replace(" ", "")) < 4 or name.lower() in seen:
                continue
            seen.add(name.lower())
            tail = line[m.end():]
            tokens = re.split(r"[\s,;|\t]+", tail)
            marks = [t.upper() for t in tokens if mark_rx.match(t)]
            out.append({"name": name, "marks": marks})
        return out

    text_chunks = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text_chunks.append(page.extract_text() or "")
    students = extract("\n".join(text_chunks))

    if not students:
        images = convert_from_bytes(file_bytes, dpi=300)
        ocr_text = []
        for img in images:
            try:
                ocr_text.append(pytesseract.image_to_string(img, lang="rus+kaz+eng"))
            except Exception:
                ocr_text.append(pytesseract.image_to_string(img, lang="rus+eng"))
        students = extract("\n".join(ocr_text))

    return students


def build_rows(students_raw, topics=TOPICS):
    result = []
    for s in students_raw:
        row = {"name": s["name"]}
        marks = s.get("marks", [])
        for i, t in enumerate(topics):
            mark = str(marks[i] if i < len(marks) else "").strip().upper()
            if mark in ("А", "С", "Н"):
                row[t] = "А" if mark == "А" else ("С" if mark == "С" else "")
            else:
                try:
                    v = int(mark)
                    row[t] = v if 1 <= v <= 5 else ""
                except ValueError:
                    row[t] = ""
        result.append(row)
    return result


def analyze(row, topics=TOPICS):
    scores, strong, weak, missing = [], [], [], []
    for t in topics:
        v = row.get(t, "")
        if v in ("А", "С"):
            missing.append({"topic": t, "reason": v})
        elif isinstance(v, int):
            scores.append(v)
            if v >= 4:
                strong.append({"topic": t, "value": v})
            elif v <= 3:
                weak.append({"topic": t, "value": v})
    return {
        "avg": round(sum(scores) / len(scores), 2) if scores else 0.0,
        "strong": strong, "weak": weak, "missing": missing,
    }


def top_best(rows, n=3, topics=TOPICS):
    return sorted([(r["name"], analyze(r, topics)["avg"]) for r in rows],
                  key=lambda x: x[1], reverse=True)[:n]


def top_worst(rows, n=3, topics=TOPICS):
    scored = [(r["name"], analyze(r, topics)["avg"]) for r in rows]
    scored = [(n_, a) for n_, a in scored if a > 0]
    return sorted(scored, key=lambda x: x[1])[:n]


def recommendations(row, topics=TOPICS):
    a = analyze(row, topics)
    recs = []
    for w in a["weak"]:
        recs.append(f"📉 «{w['topic']}» — балл {w['value']}. Повторить теорию и решить 5–7 задач.")
    for m in a["missing"]:
        reason = "болел" if m["reason"] == "А" else "уважительная"
        recs.append(f"🩺 «{m['topic']}» — пропуск ({reason}). Изучить тему и ответить на вопросы.")
    if not recs:
        recs.append("✅ Слабых тем и пропусков нет. Отличная работа!")
    return recs

# ---------- UI ----------
st.markdown("### 👩‍🏫 Учитель")
teacher = st.text_input("ФИО", value="Иванова Айгуль Сериковна", label_visibility="collapsed")
st.markdown(
    f"<div style='background:#e0f2fe;border-left:4px solid #0284c7;"
    f"padding:10px 14px;border-radius:8px;margin-bottom:16px'><b>Учитель:</b> {teacher}</div>",
    unsafe_allow_html=True,
)

st.title("📘 Журнал — Алгебра и начала анализа — 10 А")
st.header("1. Загрузите PDF-журнал")
uploaded = st.file_uploader("PDF", type=["pdf"])

if uploaded is not None:
    with st.spinner("Распознаём PDF…"):
        try:
            students_raw = parse_pdf(uploaded.read())
        except Exception as e:
            st.error(f"Ошибка: {e}")
            students_raw = []
    if students_raw:
        st.session_state["rows"] = build_rows(students_raw)
        st.success(f"✅ Распознано учеников: {len(st.session_state['rows'])}")
    else:
        st.warning("⚠ Не распознан ни один ученик.")

if "rows" not in st.session_state:
    st.info("Загрузите PDF-файл, чтобы начать.")
    st.stop()

rows = st.session_state["rows"]

# ТОП
st.header("2. Топ лучших и топ худших")
c1, c2 = st.columns(2)
with c1:
    st.subheader("🏆 Топ‑3 лучших")
    for i, (nm, av) in enumerate(top_best(rows), 1):
        st.markdown(f"{['🥇','🥈','🥉'][i-1]} **{nm}** — {av:.2f}")
with c2:
    st.subheader("⚠ Топ‑3 отстающих")
    for i, (nm, av) in enumerate(top_worst(rows), 1):
        st.markdown(f"🔻 **{nm}** — {av:.2f}")

# СВОДКА
st.header("3. Сводка по всем ученикам")
summary = []
for r in rows:
    a = analyze(r)
    summary.append({
        "Ученик": r["name"],
        "Средний балл": a["avg"],
        "Сильные темы": ", ".join(f"{x['topic']} ({x['value']})" for x in a["strong"]) or "—",
        "Слабые темы": ", ".join(f"{x['topic']} ({x['value']})" for x in a["weak"]) or "—",
        "Пропуски": ", ".join(f"{x['topic']} ({x['reason']})" for x in a["missing"]) or "—",
    })
summary_df = pd.DataFrame(summary).sort_values("Средний балл", ascending=False)
st.dataframe(summary_df, use_container_width=True)

# ЖУРНАЛ
st.header("4. Данные журнала (можно править)")
journal_df = pd.DataFrame(rows).rename(columns={"name": "Ученик"})
edited = st.data_editor(journal_df, use_container_width=True, num_rows="dynamic")
if st.button("💾 Применить правки"):
    st.session_state["rows"] = edited.rename(columns={"Ученик": "name"}).to_dict(orient="records")
    st.rerun()

# ГРАФИК
st.header("5. График развития по темам")
student_name = st.selectbox("Выберите ученика", [r["name"] for r in rows])
row = next(r for r in rows if r["name"] == student_name)
a = analyze(row)
y_vals, colors = [], []
for t in TOPICS:
    v = row.get(t, "")
    if v in ("А", "С"):
        y_vals.append(None); colors.append("#f59e0b")
    elif isinstance(v, int):
        y_vals.append(v)
        colors.append("#16a34a" if v >= 4 else "#dc2626" if v <= 3 else "#2563eb")
    else:
        y_vals.append(None); colors.append("#94a3b8")

fig = go.Figure()
fig.add_trace(go.Scatter(x=TOPICS, y=y_vals, mode="lines+markers",
                         line=dict(color="#2563eb", width=2),
                         marker=dict(size=10, color=colors),
                         name="Балл", connectgaps=True))
fig.update_layout(yaxis=dict(range=[0, 5], dtick=1), xaxis=dict(title="Темы"), height=380)
st.plotly_chart(fig, use_container_width=True)
st.markdown(f"**Средний балл:** {a['avg']:.2f} • **Сильных:** {len(a['strong'])} • **Слабых:** {len(a['weak'])} • **Пропусков:** {len(a['missing'])}")

# СИЛЬНЫЕ
st.header("6. Сильные стороны")
if a["strong"]:
    for s in a["strong"]:
        st.markdown(f"<div style='background:#ecfdf5;border-left:4px solid #10b981;padding:8px 12px;"
                    f"border-radius:8px;margin:4px 0'><b>{s['topic']}</b> — балл <b>{s['value']}</b></div>",
                    unsafe_allow_html=True)
else:
    st.info("Пока нет тем с оценкой 4–5.")

# РЕКОМЕНДАЦИИ
st.header("7. Слабые стороны и рекомендации")
for rec in recommendations(row):
    st.markdown(f"<div style='background:#fff7ed;border-left:4px solid #f97316;padding:8px 12px;"
                f"border-radius:8px;margin:4px 0'>{rec}</div>", unsafe_allow_html=True)

# ВОПРОСЫ
st.header("8. Вопросы для отработки")
targets = list(dict.fromkeys([m["topic"] for m in a["missing"]] + [w["topic"] for w in a["weak"]]))
if targets:
    for t in targets:
        st.markdown(f"**{t}**")
        for i, q in enumerate(QUESTION_BANK.get(t, []), 1):
            st.markdown(f"{i}. {q}")
else:
    st.info("Нет тем для отработки.")

# ЭКСПОРТ
st.header("9. Экспорт и печать")
def build_excel():
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        journal_df.to_excel(writer, sheet_name="Журнал", index=False)
        summary_df.to_excel(writer, sheet_name="Сводка", index=False)
        top_df = pd.DataFrame({
            "Место": [1, 2, 3],
            "Лучшие": [n for n, _ in top_best(rows)],
            "Средний (лучшие)": [a for _, a in top_best(rows)],
            "Худшие": [n for n, _ in top_worst(rows)],
            "Средний (худшие)": [a for _, a in top_worst(rows)],
        })
        top_df.to_excel(writer, sheet_name="Топ", index=False)
        rec_rows = [{"Ученик": r["name"], "Рекомендация": rec}
                    for r in rows for rec in recommendations(r)]
        pd.DataFrame(rec_rows).to_excel(writer, sheet_name="Рекомендации", index=False)
        wb = writer.book
        for ws in wb.worksheets:
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="2563EB")
                cell.alignment = Alignment(horizontal="center")
            for col in ws.columns:
                ml = max(len(str(c.value)) if c.value else 0 for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(ml + 2, 60)
    buffer.seek(0)
    return buffer.getvalue()

st.download_button("⬇ Скачать Excel", data=build_excel(), file_name="journal_algebra_10A.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
st.markdown("🖨 **Печать:** `Ctrl+P` в браузере.")