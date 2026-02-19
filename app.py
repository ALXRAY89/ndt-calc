import streamlit as st
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import base64

st.set_page_config(page_title="NDT ISO Pro Expert", layout="wide")

# --- Справочники ---
def get_iso_limits(w):
    if w <= 1.2: return 50, 40
    if w <= 5.0: return 100, 80
    if w <= 12: return 130, 100
    if w <= 40: return 160, 130
    return 200, 160

materials = {"Алюминий": 1.0, "Титан": 1.7, "Сталь": 2.9, "Нерж. сталь": 3.0}

st.title("🔬 Advanced NDT & Microfocus Optimizer v9")

# --- ПАНЕЛЬ УПРАВЛЕНИЯ (БЕЗ ИЗМЕНЕНИЙ) ---
with st.sidebar:
    st.header("💡 Источник")
    src_type = st.radio("Диапазон фокуса", ["Микро (1-100 мкм)", "Макро (0.1-3 мм)"])
    f_mkm = st.slider("Размер фокуса (мкм)", 1, 100, 10) if src_type == "Микро (1-100 мкм)" else st.slider("Размер фокуса (мм)", 0.1, 3.0, 0.4, 0.1) * 1000
    
    st.header("📲 Детектор")
    pixel = st.number_input("Пиксель (мкм)", value=64)
    mtf_k = st.slider("MTF (размытие)", 1.0, 3.0, 1.6)
    srb_det = pixel * mtf_k

    st.header("📐 Геометрия и Объект")
    fdd = st.slider("FDD (мм)", 200, 1000, 600)
    obj_size = st.slider("Габарит образца (мм)", 1, 100, 20)
    wall_w = st.slider("Толщина стенок (мм)", 1, 100, 10)
    material = st.selectbox("Материал", list(materials.keys()))

# --- МАТЕМАТИКА (ПЛОСКОСТЬ ОБЪЕКТА) ---
def calc_res_target(b_dist):
    a = fdd - b_dist
    if a <= 0.5: return f_mkm
    m = fdd / a
    ug_t = f_mkm * (b_dist / fdd)
    up_t = srb_det / m
    return np.sqrt(ug_t**2 + up_t**2)

b_axis = np.linspace(0, fdd * 0.98, 1000)
res_axis = [calc_res_target(x) for x in b_axis]
idx_min = np.argmin(res_axis)
b_opt = b_axis[idx_min]

b_front, b_back = b_opt + (obj_size / 2), b_opt - (obj_size / 2)
res_center = res_axis[idx_min]
res_worst = max(calc_res_target(b_front), calc_res_target(b_back))
limit_a, limit_b = get_iso_limits(wall_w)
m_val = fdd / (fdd - b_opt)

# --- ИНТЕРФЕЙС ВЫВОДА ---
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Оптим. позиция", f"{b_opt:.1f} мм"); st.caption(f"Увеличение M = {m_val:.2f}")
with c2: st.metric("SRb (Центр)", f"{res_center:.1f} мкм"); st.write("✅ Класс B" if res_worst <= limit_b else "❌ Вне B")
with c3: st.metric("Худшее (Края)", f"{res_worst:.1f} мкм"); st.caption(f"Лимит B: {limit_b} мкм")
with c4: st.metric("Сложность", f"{materials[material]*(wall_w/10):.1f} x")

# --- ГРАФИК ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=b_axis, y=res_axis, name="SRb на объекте", line=dict(width=3, color='#1f77b4')))
fig.add_vrect(x0=max(0, b_back), x1=min(fdd, b_front), fillcolor="rgba(255, 127, 14, 0.2)", line_width=0, annotation_text="ОБЪЕКТ")
fig.add_trace(go.Scatter(x=[b_opt], y=[res_center], mode='markers', marker=dict(size=12, color='red', symbol='diamond'), name="Оптимум"))
fig.add_hline(y=limit_b, line_dash="dot", line_color="green", annotation_text="Limit B")
st.plotly_chart(fig, use_container_width=True)

# --- СЕКЦИЯ ПРОТОКОЛА ---
st.divider()
st.subheader("📋 Рекомендуемый протокол съемки")

col_p1, col_p2 = st.columns(2)
with col_p1:
    st.markdown(f"""
    **Параметры установки:**
    - **Позиция объекта:** {b_opt:.1f} мм от детектора
    - **Расстояние до источника (f):** {fdd - b_opt:.1f} мм
    - **Рекомендуемое увеличение (M):** {m_val:.2f}
    - **Обоснование:** Данная геометрия минимизирует суммарную нерезкость в плоскости объекта, 
    уравновешивая геометрическое размытие фокуса ({f_mkm} мкм) и дискретизацию детектора ({srb_det:.1f} мкм).
    """)

with col_p2:
    st.markdown(f"""
    **Оценка качества (ISO 17636-2):**
    - **Требуемое разрешение (Класс B):** {limit_b} мкм
    - **Прогноз разрешения (SRb):** {res_worst:.1f} мкм
    - **Запас качества:** {((limit_b - res_worst)/limit_b * 100):.1} %
    """)

# --- ФУНКЦИЯ ГЕНЕРАЦИИ PDF ---
def create_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, txt="NDT INSPECTION PROTOCOL (ISO 17636-2)", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(190, 10, txt=f"Material: {material} | Wall Thickness: {wall_w} mm", ln=True)
    pdf.cell(190, 10, txt=f"Focal Spot: {f_mkm} um | Pixel: {pixel} um (MTF k={mtf_k})", ln=True)
    pdf.cell(190, 10, txt=f"FDD: {fdd} mm | Optimized Object Position b: {b_opt:.1f} mm", ln=True)
    pdf.cell(190, 10, txt=f"Target Resolution (SRb): {res_center:.1f} um (Worst: {res_worst:.1f} um)", ln=True)
    pdf.cell(190, 10, txt=f"Calculated Magnification (M): {m_val:.2f}", ln=True)
    pdf.ln(5)
    pdf.multi_cell(190, 10, txt=f"JUSTIFICATION: The object is centered at the resolution minimum where Ug=Up. For Class B compliance (limit {limit_b} um), this geometry provides a safety margin of {((limit_b - res_worst)/limit_b * 100):.1f}%.")
    return pdf.output(dest='S').encode('latin-1')

pdf_data = create_pdf()
st.download_button(label="📥 Экспорт протокола в PDF", data=pdf_data, file_name="ndt_protocol.pdf", mime="application/pdf")
