import streamlit as st
import numpy as np
import plotly.graph_objects as go
from PIL import Image, ImageDraw, ImageFont
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

st.title("🔬 Продвинутый NDT & Микрофокус Оптимизатор v12")

# --- ПАНЕЛЬ УПРАВЛЕНИЯ (ВАШ ИНТЕРФЕЙС) ---
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

# --- ИНТЕРФЕЙС ВЫВОДА ---
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Оптим. позиция", f"{b_opt:.1f} мм"); st.caption(f"M = {m_val:.2f}")
with c2: st.metric("SRb (Центр)", f"{res_center:.1f} мкм"); st.write("✅ Класс B" if res_worst <= limit_b else "❌ Вне B")
with c3: st.metric("Худшее (Края)", f"{res_worst:.1f} мкм"); st.caption(f"Лимит B: {limit_b} мкм")
with c4: st.metric("Сложность", f"{materials[material]*(wall_w/10):.1f} x")

# --- ГРАФИК ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=b_axis, y=res_axis, name="SRb на объекте", line=dict(width=3, color='#1f77b4')))
fig.add_vrect(x0=max(0, b_opt-obj_size/2), x1=min(fdd, b_opt+obj_size/2), fillcolor="rgba(255, 127, 14, 0.2)", line_width=0, annotation_text="ОБЪЕКТ")
fig.add_trace(go.Scatter(x=[b_opt], y=[res_center], mode='markers', marker=dict(size=12, color='red', symbol='diamond'), name="Оптимум"))
fig.add_hline(y=limit_b, line_dash="dot", line_color="green", annotation_text="Лимит B")
st.plotly_chart(fig, use_container_width=True)

# --- ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЯ-ПРОТОКОЛА (ВМЕСТО PDF) ---
def create_report_image():
    # Создаем холст
    img = Image.new('RGB', (800, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Текст протокола (используем стандартный шрифт PIL)
    text = f"""
    ПРОТОКОЛ РАСЧЕТА NDT (ISO 17636-2)
    ----------------------------------
    Материал: {material}
    Толщина стенки: {wall_w} мм
    Фокус: {f_mkm} мкм
    Детектор (SRb_det): {srb_det:.1f} мкм
    ----------------------------------
    Оптимальная позиция (b): {b_opt:.1f} мм
    Увеличение (M): {m_val:.2f}
    Разрешение (SRb центр): {res_center:.1f} мкм
    Статус: {"СООТВЕТСТВУЕТ КЛАССУ B" if res_worst <= limit_b else "НЕ СООТВЕТСТВУЕТ"}
    Запас по лимиту ({limit_b} мкм): {((limit_b - res_worst)/limit_b * 100):.1f}%
    """
    
    # Отрисовка текста (построчно для надежности)
    y_offset = 20
    for line in text.split('\n'):
        draw.text((40, y_offset), line.strip(), fill=(0, 0, 0))
        y_offset += 35
        
    # Сохраняем в буфер
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

st.divider()
if st.button("🖼️ Сформировать картинку-протокол"):
    img_data = create_report_image()
    st.image(img_data, caption="Готовый протокол для пересылки")
    st.download_button(
        label="📥 Скачать изображение",
        data=img_data,
        file_name="ndt_report.png",
        mime="image/png"
    )

# Текстовая версия для копирования в мессенджер
with st.expander("📝 Текст для мессенджера (скопировать)"):
    msg = f"📊 NDT Отчет: {material} {wall_w}мм. Фокус {f_mkm}мкм. SRb={res_center:.1f}мкм. Позиция b={b_opt:.1f}мм. Статус: {'✅ OK' if res_worst <= limit_b else '❌ FAIL'}."
    st.code(msg)
