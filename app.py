import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.optimize import minimize_scalar

st.set_page_config(page_title="Ultra NDT Optimizer", layout="wide")

# --- Справочник ISO и Поглощение ---
def get_iso_limits(w):
    if w <= 1.2: return 50, 40
    if w <= 5.0: return 100, 80
    if w <= 12: return 130, 100
    if w <= 40: return 160, 130
    return 200, 160

# Коэффициенты относительной плотности/поглощения
materials = {
    "Алюминий": 1.0, 
    "Сталь": 2.9, 
    "Нерж. сталь": 3.0, 
    "Титан": 1.7
}

st.title("🔬 Ultra NDT & Microfocus Optimizer v6")

# --- ПАНЕЛЬ УПРАВЛЕНИЯ ---
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

# --- МАТЕМАТИКА ОПТИМИЗАЦИИ ---
def calc_res(b_dist):
    a = fdd - b_dist
    if a <= 0: return 2000
    ug = f_mkm * (b_dist / a)
    up = srb_det / (fdd / a)
    return np.sqrt(ug**2 + up**2)

# Численный поиск минимума функции разрешения на отрезке [0, FDD]
res_min_search = minimize_scalar(calc_res, bounds=(0, fdd*0.95), method='bounded')
b_opt = res_min_search.x

# Границы образца
b_front = b_opt + (obj_size / 2)
b_back = b_opt - (obj_size / 2)

res_center = calc_res(b_opt)
res_worst = max(calc_res(b_front), calc_res(b_back))
limit_a, limit_b = get_iso_limits(wall_w)

# --- ИНТЕРФЕЙС ---
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Оптим. позиция центра", f"{b_opt:.1f} мм")
    st.caption(f"M = {fdd/(fdd-b_opt):.2f}")
with c2:
    st.metric("Разрешение (Центр)", f"{res_center:.1f} мкм")
    st.write("✅ Класс B" if res_worst <= limit_b else "❌ Вне B")
with c3:
    st.metric("Худшее (Края)", f"{res_worst:.1f} мкм")
    st.caption(f"Лимит B: {limit_b} мкм")
with c4:
    # Примерный расчет экспозиции (базовая модель)
    exp_factor = materials[material] * (wall_w / 10)
    st.metric("Сложность", f"{exp_factor:.1f} x")
    st.caption("Относ. экспозиция")

# --- ГРАФИК ---
b_axis = np.linspace(0.01, fdd * 0.95, 1000)
res_axis = [calc_res(x) for x in b_axis]

fig = go.Figure()
fig.add_trace(go.Scatter(x=b_axis, y=res_axis, name="Профиль SRb", line=dict(width=3, color='#1f77b4')))

# Визуализация образца в ОПТИМУМЕ
fig.add_vrect(x0=max(0, b_back), x1=min(fdd, b_front), 
              fillcolor="rgba(255, 127, 14, 0.2)", line_width=0,
              annotation_text="ОБЪЕКТ", annotation_position="top left")

fig.add_trace(go.Scatter(x=[b_opt], y=[res_center], mode='markers', 
                         marker=dict(size=12, color='red', symbol='diamond'), name="Минимум"))

fig.add_hline(y=limit_b, line_dash="dot", line_color="green", annotation_text="Limit B")
fig.update_layout(xaxis_title="Расстояние от детектора (мм)", yaxis_title="Разрешение SRb (мкм)",
                  yaxis_range=[0, min(max(res_axis), res_center*5)], hovermode="x")
st.plotly_chart(fig, use_container_width=True)
