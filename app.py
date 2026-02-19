import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Microfocus Optimizer", layout="wide")

def get_iso_limits(w):
    if w <= 1.2: return 50, 40
    if w <= 5.0: return 100, 80
    if w <= 12: return 130, 100
    if w <= 40: return 160, 130
    return 200, 160

st.title("🔬 Микрофокусный оптимизатор (Центровка в оптимуме)")

# --- ВВОД ПАРАМЕТРОВ ---
with st.sidebar:
    st.header("💡 Источник")
    src_mode = st.radio("Режим фокуса", ["Микро (мкм)", "Макро (мм)"])
    if src_mode == "Микро (мкм)":
        f_mkm = st.number_input("Размер фокуса (мкм)", 5, 1000, 20)
    else:
        f_mkm = st.number_input("Размер фокуса (мм)", 0.1, 5.0, 0.4) * 1000
    
    st.header("📲 Детектор")
    pixel = st.number_input("Пиксель (мкм)", value=64)
    mtf_k = st.slider("MTF коэфф. (размытие)", 1.0, 3.0, 1.6)
    srb_det = pixel * mtf_k

    st.header("📐 Геометрия")
    fdd = st.number_input("FDD (мм)", value=600)
    obj_size = st.number_input("Габарит образца (мм)", value=30)
    total_w = st.number_input("Общая толщина стенок (мм)", value=10)

# --- МАТЕМАТИКА ОПТИМИЗАЦИИ ---
# Оптимальное увеличение M_opt = sqrt(srb_det / f_mkm) + 1 (приблизительно)
# Точное M_opt, где Ug = Up: M_opt = 1 + sqrt(srb_det / f_mkm)
m_opt = 1 + np.sqrt(srb_det / f_mkm)
# Расстояние от детектора до центра объекта b_opt
b_opt = fdd * (1 - 1/m_opt)

# Границы образца относительно оптимума
b_front = b_opt + (obj_size / 2) # Сторона к источнику
b_back = b_opt - (obj_size / 2)  # Сторона к детектору

def calc_res(dist):
    a = fdd - dist
    if a <= 0: return 1000
    ug = f_mkm * (dist / a)
    up = srb_det / (fdd / a)
    return np.sqrt(ug**2 + up**2)

res_center = calc_res(b_opt)
res_worst = max(calc_res(b_front), calc_res(b_back))
limit_a, limit_b = get_iso_limits(total_w)

# --- ИНТЕРФЕЙС ---
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Оптим. позиция центра", f"{b_opt:.1f} мм")
    st.caption(f"Увеличение M = {fdd/(fdd-b_opt):.2f}")
with c2:
    st.metric("Разрешение в центре", f"{res_center:.1f} мкм")
    st.write("✅ OK (Класс B)" if res_worst <= limit_b else "⚠️ Риск по Классу B")
with c3:
    st.metric("Худшее в объеме", f"{res_worst:.1f} мкм")
    st.caption("На границах габарита")

# --- ГРАФИК ---
b_axis = np.linspace(0.1, fdd * 0.9, 1000)
res_axis = [calc_res(x) for x in b_axis]

fig = go.Figure()
fig.add_trace(go.Scatter(x=b_axis, y=res_axis, name="Профиль SRb", line=dict(width=3)))

# Выделение габарита объекта (центрировано в минимуме)
fig.add_vrect(x0=max(0, b_back), x1=min(fdd, b_front), 
              fillcolor="rgba(255, 165, 0, 0.3)", line_width=0,
              annotation_text="Габарит объекта", annotation_position="top left")

# Точка оптимума
fig.add_trace(go.Scatter(x=[b_opt], y=[res_center], mode='markers', 
                         marker=dict(size=12, color='red', symbol='x'), name="Оптимум"))

fig.add_hline(y=limit_b, line_dash="dot", line_color="green", annotation_text="Лимит B")
fig.update_layout(xaxis_title="Расстояние от детектора (мм)", yaxis_title="SRb (мкм)",
                  yaxis_range=[0, min(max(res_axis), res_center*3)], hovermode="x")
st.plotly_chart(fig, use_container_width=True)
