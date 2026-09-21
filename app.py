import io
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from openpyxl.styles import Font, PatternFill, Alignment

from ocr import parse_pdf
from analysis import (
    TOPICS,
    build_dataframe,
    analyze_student,
    top_best,
    top_worst,
    recommendations,
    questions_for_topics,
)

# ---------- НАСТРОЙКА СТРАНИЦЫ ----------
st.set_page_config(
    page_title="Журнал — Алгебра и начала анализа — 10 А",
    page_icon="📘",
    layout="wide",
)

# ---------- УЧИТЕЛЬ ----------
st.markdown("### 👩‍🏫 Учитель")
teacher = st.text_input(
    "ФИО учителя (отображается сверху, в таблицу не входит)",
    value="Иванова Айгуль Сериковна",
    label_visibility="collapsed",
)
st.markdown(f"<div style='background:#e0f2fe;border-left:4px solid #0284c7;padding:10px 14px;border-radius:8px;margin-bottom:16px'>"
            f"<b>Учитель:</b> {teacher}</div>", unsafe_allow_html=True)

st.title("📘 Журнал — Алгебра и начала анализа — 10 А")

# ---------- ЗАГРУЗКА PDF ----------
st.header("1. Загрузите PDF-журнал")
uploaded = st.file_uploader("PDF-файл журнала", type=["pdf"])
use_ocr = st.checkbox("Использовать OCR для сканов", value=True)

if uploaded is not None:
    with st.spinner("Распознаём PDF…"):
        try:
            students_raw = parse_pdf(uploaded.read(), use_ocr=use_ocr)
        except Exception as e:
            st.error(f"Ошибка распознавания: {e}")
            students_raw = []

    if not students_raw:
        st.warning("⚠ Не удалось распознать ни одного ученика. "
                   "Попробуйте включить OCR или загрузить Excel.")
    else:
        rows = build_dataframe(students_raw, TOPICS)
        st.success(f"✅ Распознано учеников: {len(rows)}")

        # Кэшируем в session_state, чтобы не терять при перерисовке
        st.session_state["rows"] = rows

# ---------- ЗАГРУЗКА EXCEL (запасной вариант) ----------
with st.expander("📊 Или загрузить готовый Excel"):
    xlsx = st.file_uploader("Excel-файл (.xlsx)", type=["xlsx"], key="xlsx")
    if xlsx is not None:
        try:
            df = pd.read_excel(xlsx)
            if "Ученик" in df.columns:
                df = df.rename(columns={"Ученик": "name"})
            rows = df.to_dict(orient="records")
            st.session_state["rows"] = rows
            st.success(f"✅ Загружено из Excel: {len(rows)} учеников")
        except Exception as e:
            st.error(f"Ошибка Excel: {e}")

# ---------- ЕСЛИ ЕСТЬ ДАННЫЕ ----------
if "rows" in st.session_state and st.session_state["rows"]:
    rows = st.session_state["rows"]

    # ---------- ТОП ЛУЧШИХ И ХУДШИХ ----------
    st.header("2. Топ лучших и топ худших учеников")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏆 Топ‑3 лучших")
        for i, (name, avg) in enumerate(top_best(rows, 3, TOPICS), 1):
            medal = ["🥇", "🥈", "🥉"][i - 1]
            st.markdown(f"{medal} **{name}** — средний балл **{avg:.2f}**")
    with col2:
        st.subheader("⚠ Топ‑3 отстающих")
        for i, (name, avg) in enumerate(top_worst(rows, 3, TOPICS), 1):
            st.markdown(f"🔻 **{name}** — средний балл **{avg:.2f}**")

    # ---------- СВОДКА ПО ВСЕМ УЧЕНИКАМ ----------
    st.header("3. Все ученики класса — сводка")
    summary = []
    for r in rows:
        a = analyze_student(r, TOPICS)
        summary.append({
            "Ученик": r["name"],
            "Средний балл": a["avg"],
            "Сильные темы": ", ".join(f"{x['topic']} ({x['value']})" for x in a["strong"]) or "—",
            "Слабые темы": ", ".join(f"{x['topic']} ({x['value']})" for x in a["weak"]) or "—",
            "Пропуски (А/С)": ", ".join(f"{x['topic']} ({x['reason']})" for x in a["missing"]) or "—",
        })
    summary_df = pd.DataFrame(summary).sort_values("Средний балл", ascending=False)
    st.dataframe(summary_df, use_container_width=True)

    # ---------- ЖУРНАЛ ----------
    st.header("4. Данные журнала (можно править)")
    journal_df = pd.DataFrame(rows)
    journal_df = journal_df.rename(columns={"name": "Ученик"})
    edited = st.data_editor(
        journal_df,
        use_container_width=True,
        num_rows="dynamic",
        key="journal_editor",
    )
    if st.button("💾 Применить правки"):
        edited = edited.rename(columns={"Ученик": "name"})
        st.session_state["rows"] = edited.to_dict(orient="records")
        st.success("Правки сохранены.")
        st.rerun()

    # ---------- ГРАФИК ПО УЧЕНИКУ ----------
    st.header("5. График развития по темам")
    student_name = st.selectbox("Выберите ученика", [r["name"] for r in rows])
    row = next(r for r in rows if r["name"] == student_name)
    a = analyze_student(row, TOPICS)

    y_vals = []
    colors = []
    for t in TOPICS:
        v = row.get(t, "")
        if v == "А" or v == "С":
            y_vals.append(None)
            colors.append("#f59e0b")
        elif isinstance(v, int):
            y_vals.append(v)
            colors.append("#16a34a" if v >= 4 else "#dc2626" if v <= 3 else "#2563eb")
        else:
            y_vals.append(None)
            colors.append("#94a3b8")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=TOPICS, y=y_vals,
        mode="lines+markers",
        line=dict(color="#2563eb", width=2),
        marker=dict(size=10, color=colors),
        name="Балл ученика",
        connectgaps=True,
    ))
    fig.update_layout(
        yaxis=dict(range=[0, 5], dtick=1, title="Балл"),
        xaxis=dict(title="Темы"),
        height=380,
        margin=dict(l=40, r=20, t=30, b=120),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f"**Средний балл:** {a['avg']:.2f} • "
        f"**Сильных тем:** {len(a['strong'])} • "
        f"**Слабых тем:** {len(a['weak'])} • "
        f"**Пропусков:** {len(a['missing'])}"
    )

    # ---------- СИЛЬНЫЕ СТОРОНЫ ----------
    st.header("6. Сильные стороны")
    if a["strong"]:
        for s in a["strong"]:
            st.markdown(
                f"<div style='background:#ecfdf5;border-left:4px solid #10b981;"
                f"padding:8px 12px;border-radius:8px;margin:4px 0'>"
                f"<b>{s['topic']}</b> — балл <b>{s['value']}</b></div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("Пока нет тем с оценкой 4–5.")

    # ---------- СЛАБЫЕ + РЕКОМЕНДАЦИИ ----------
    st.header("7. Слабые стороны и рекомендации")
    for rec in recommendations(row, TOPICS):
        st.markdown(
            f"<div style='background:#fff7ed;border-left:4px solid #f97316;"
            f"padding:8px 12px;border-radius:8px;margin:4px 0'>{rec}</div>",
            unsafe_allow_html=True,
        )

    # ---------- ВОПРОСЫ ----------
    st.header("8. Вопросы для отработки")
    targets = [m["topic"] for m in a["missing"]] + [w["topic"] for w in a["weak"]]
    targets = list(dict.fromkeys(targets))
    if targets:
        qmap = questions_for_topics(targets)
        for t, qs in qmap.items():
            st.markdown(f"**{t}**")
            for i, q in enumerate(qs, 1):
                st.markdown(f"{i}. {q}")
    else:
        st.info("Нет тем, требующих отработки.")

    # ---------- ЭКСПОРТ В EXCEL ----------
    st.header("9. Экспорт и печать")
    def build_excel() -> bytes:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            # Лист 1 — журнал
            jd = pd.DataFrame(rows).rename(columns={"name": "Ученик"})
            jd.to_excel(writer, sheet_name="Журнал", index=False)
            # Лист 2 — сводка
            summary_df.to_excel(writer, sheet_name="Сводка", index=False)
            # Лист 3 — топ
            top_df = pd.DataFrame({
                "Место": [1, 2, 3],
                "Лучшие": [n for n, _ in top_best(rows, 3, TOPICS)],
                "Средний балл (лучшие)": [a for _, a in top_best(rows, 3, TOPICS)],
                "Худшие": [n for n, _ in top_worst(rows, 3, TOPICS)],
                "Средний балл (худшие)": [a for _, a in top_worst(rows, 3, TOPICS)],
            })
            top_df.to_excel(writer, sheet_name="Топ", index=False)
            # Лист 4 — рекомендации
            rec_rows = []
            for r in rows:
                for rec in recommendations(r, TOPICS):
                    rec_rows.append({"Ученик": r["name"], "Рекомендация": rec})
            pd.DataFrame(rec_rows).to_excel(writer, sheet_name="Рекомендации", index=False)

            # Форматирование
            wb = writer.book
            for ws in wb.worksheets:
                for cell in ws[1]:
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.fill = PatternFill("solid", fgColor="2563EB")
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                for col in ws.columns:
                    max_len = max(len(str(c.value)) if c.value else 0 for c in col)
                    ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)
        buffer.seek(0)
        return buffer.getvalue()

    excel_bytes = build_excel()
    st.download_button(
        label="⬇ Скачать Excel (журнал + сводка + топ + рекомендации)",
        data=excel_bytes,
        file_name="journal_algebra_10A.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.markdown(
        "🖨 **Печать:** используйте сочетание `Ctrl+P` в браузере — "
        "интерфейс Streamlit корректно печатается."
    )

else:
    st.info("Загрузите PDF-журнал или Excel-файл, чтобы начать анализ.")