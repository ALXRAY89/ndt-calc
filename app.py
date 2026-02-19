import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="NDT ISO Expert Calc", layout="wide")

def get_iso_limits(w):
    """Лимиты SRb (мкм) для Класса А и В по ISO 17636-2"""
    if w <= 1.2: return 50, 40
    if w <= 2.0: return 63, 50
    if w <= 3.5: return 80, 63
    if w <= 5.0: return 100, 80
    if w <= 12: return 130, 100
    if w <= 40: return 160, 130
    return 200, 160

# --- ПАНЕЛЬ УПРАВЛЕНИЯ ---
st.sidebar.header("⚙️ Параметры системы")
f_mm = st.sidebar.slider("Фокус источника f (мм)", 0.1, 4.0, 0.4, step=0.1)
srb_det = st.sidebar.number_input("Реальное SRb детектора (мкм)", value=80)
fdd = st.sidebar.slider("Расстояние FDD (мм)", 200, 2000, 600)
w = st.sidebar.slider("Толщина / Расстояние b (мм)", 1, 200, 50)

st.sidebar.header("📸 SNR и Время")
frame_time = st.sidebar.number_input("Время кадра (сек)", value=0.2)
target_snr = st.sidebar.selectbox("Целевой SNR_norm", [130, 70, 250], index=0)

# --- МАТЕМАТИКА ---
a = fdd - w
# 1. Расчет разрешения
ug = (f_mm * 1000) * (w / a)
up = srb_det / (fdd / a)
current_srb = np.sqrt(ug**2 + up**2)
limit_a, limit_b = get_iso_limits(w)

# 2. Расчет f_min (ISO 17636-2: f >= 7.5 * f_mm^(2/3) * b^(2/3) для Класса B)
# Упрощенная формула стандарта для Класса B: f_min = b * (f_mm / 0.1)**(2/3) * k
k_class_b = 7.5 
f_min_iso = k_class_b * (f_mm**(2/3)) * (w**(1/3)) * 10 # примерный расчет f_min в мм

# 3. Накопление SNR
needed_n = int((target_snr / 15)**2)
total_exposure = needed_n * frame_time

# --- ИНТЕРФЕЙС ---
st.title("🩻 NDT ISO Expert: Разрешение, SNR и Геометрия")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Разрешение SRb", f"{current_srb:.1f} мкм")
    st.write("✅ OK" if current_srb <= limit_b else "❌ FAIL")

with col2:
    st.metric("Мин. FDD (ISO)", f"{f_min_iso + w:.0f} мм")
    st.caption("По геом. нерезкости")

with col3:
    st.metric("Кадров (N)", f"{needed_n}")
    st.caption(f"Для SNR={target_snr}")

with col4:
    st.metric("Экспозиция", f"{total_exposure/60:.1f} мин")

# График
b_axis = np.linspace(1, 200, 400)
a_axis = fdd - b_axis
total_line = np.sqrt(((f_mm*1000)*(b_axis/a_axis))**2 + (srb_det/(fdd/a_axis))**2)

fig = go.Figure()
fig.add_trace(go.Scatter(x=b_axis, y=total_line, name="SRb_image", line=dict(width=3)))
fig.add_trace(go.Scatter(x=[w], y=[current_srb], marker=dict(size=12, color='red'), name="Текущая точка"))
fig.add_hline(y=limit_b, line_dash="dash", line_color="green", annotation_text="Лимит B")
st.plotly_chart(fig, use_container_width=True)
