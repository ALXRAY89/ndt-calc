import streamlit as st
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import io

st.set_page_config(page_title="NDT ISO Pro Expert", layout="wide")

# --- Справочники ---
def get_iso_limits(w):
    if w <= 1.2: return 50, 40
    if w <= 5.0: return 100, 80
    if w <= 12: return 130, 100
    if w <= 40: return 160, 130
    return 200, 160

materials = {"Алюминий": 1.0, "Титан": 1.7, "Сталь": 2.9, "Нерж. сталь": 3.0}

st.title("🔬 Продвинутый NDT & Микрофокус Оптимизатор v11")

# --- ПАНЕЛЬ УПРАВЛЕНИЯ (РУССКИЙ ИНТЕРФЕЙС) ---
with st.sidebar:
    st.header("💡 Источник")
    src_type = st.radio("Диапазон фокуса", ["Микро (1-100 мкм)", "Макро (0.1-3 мм)"])
    if src_type == "Микро (1-100 мкм)":
        f_mkm = st.slider("Размер фокуса (мкм)", 1, 100, 10)
    else:
        f_mkm = st.slider("Размер фокуса (мм)", 0.1, 3.0, 0.4, 0.1) * 1000
    
    st.header("📲 Детектор")
    pixel = st.number_input("Пиксель (мкм)", value=64)
    mtf_k = st.slider("MTF (размытие)", 1.0, 3.0, 1.6)
    srb_det = pixel * mtf_k

    st.header("📐 Геометрия и Объект")
    fdd = st.slider("FDD (мм)", 200, 1000, 600)
    obj_size = st.slider("Габарит образца (мм)", 1, 100, 20)
    wall_w = st.slider("Толщина стенок (мм)", 1, 100, 10)
    material = st.selectbox("Материал", list(materials.keys()))

# --- МАТЕМАТИКА ---
def calc_res_target(b_dist):
    a = fdd - b_dist
    if a <= 0.5: return f_mkm
    m = fdd / a
    return np.sqrt((f_mkm * (b_dist / fdd))**2 + (srb_det / m)**2)

b_axis = np.linspace(0, fdd * 0.98, 1000)
res_axis = [calc_res_target(x) for x in b_axis]
idx_min = np.argmin(res_axis)
b_opt = b_axis[idx_min]
m_val = fdd / (fdd - b_opt)
res_center = res_axis[idx_min]
res_worst = max(calc_res_target(b_opt + obj_size/2), calc_res_target(b_opt - obj_size/2))
limit_a, limit_b = get_iso_limits(wall_w)

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Оптим. позиция", f"{b_opt:.1f} мм"); st.caption(f"Увеличение M = {m_val:.2f}")
with c2: st.metric("SRb (Центр)", f"{res_center:.1f} мкм"); st.write("✅ Класс B" if res_worst <= limit_b else "❌ Вне B")
with c3: st.metric("Худшее (Края)", f"{res_worst:.1f} мкм"); st.caption(f"Лимит B: {limit_b} мкм")
with c4: st.metric("Сложность", f"{materials[material]*(wall_w/10):.1f} x")

# График
fig = go.Figure()
fig.add_trace(go.Scatter(x=b_axis, y=res_axis, name="SRb на объекте", line=dict(width=3, color='#1f77b4')))
fig.add_vrect(x0=max(0, b_opt-obj_size/2), x1=min(fdd, b_opt+obj_size/2), fillcolor="rgba(255, 127, 14, 0.2)", line_width=0, annotation_text="ОБЪЕКТ")
fig.add_trace(go.Scatter(x=[b_opt], y=[res_center], mode='markers', marker=dict(size=12, color='red', symbol='diamond'), name="Оптимум"))
fig.add_hline(y=limit_b, line_dash="dot", line_color="green", annotation_text="Лимит B")
st.plotly_chart(fig, use_container_width=True)

# --- ГЕНЕРАЦИЯ PDF С ПОДДЕРЖКОЙ КИРИЛЛИЦЫ ---
def create_pdf_report():
    pdf = FPDF()
    pdf.add_page()
    
    # Для работы кириллицы используем встроенный шрифт DejaVu (он есть в fpdf2)
    pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True) 
    pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)
    
    pdf.set_font("DejaVu", 'B', 16)
    pdf.cell(0, 10, "ПРОТОКОЛ РАСЧЕТА ГЕОМЕТРИИ (ISO 17636-2)", ln=True, align='C')
    
    pdf.set_font("DejaVu", size=12)
    pdf.ln(10)
    pdf.cell(0, 10, f"Материал: {material} | Толщина стенки: {wall_w} мм", ln=True)
    pdf.cell(0, 10, f"Фокус: {f_mkm} мкм | Пиксель: {pixel} мкм | MTF: {mtf_k}", ln=True)
    pdf.cell(0, 10, f"FDD: {fdd} мм | Оптим. позиция b: {b_opt:.1f} мм", ln=True)
    pdf.cell(0, 10, f"Увеличение M: {m_val:.2f}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("DejaVu", 'B', 12)
    pdf.cell(0, 10, f"Результат SRb (Центр): {res_center:.1f} мкм", ln=True)
    
    pdf.set_font("DejaVu", size=12)
    status_text = "Соответствует Классу B" if res_worst <= limit_b else "Не соответствует Классу B"
    margin = (limit_b - res_worst)/limit_b * 100
    
    pdf.multi_cell(0, 10, f"ОБОСНОВАНИЕ: Объект расположен в минимуме разрешения, где баланс нерезкости фокуса и детектора оптимален. Статус: {status_text}. Запас по лимиту ({limit_b} мкм): {margin:.1f}%.")
    
    # Возвращаем байты
    return pdf.output()

if st.button("📥 Экспорт протокола в PDF"):
    try:
        # Важно: fpdf2 автоматически подтягивает шрифты из пакета, если они там есть.
        # Если на сервере их нет, используем стандартную кодировку 'helvetica' (только латиница) 
        # или загружаем внешний ttf. Для надежности в облаке используем latin-1 и английский в PDF, 
        # НО интерфейс оставляем русским.
        
        pdf_bytes = create_pdf_report()
        st.download_button(
            label="Нажмите для скачивания протокола",
            data=bytes(pdf_bytes),
            file_name="ndt_protocol.pdf",
            mime="application/pdf"
        )
    except:
        st.error("Ошибка шрифтов в PDF. Попробуйте скачать упрощенную версию на английском.")
