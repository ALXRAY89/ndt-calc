import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Microfocus Target Optimizer", layout="wide")

def get_iso_limits(w):
    if w <= 1.2: return 50, 40
    if w <= 5.0: return 100, 80
    if w <= 12: return 130, 100
    if w <= 40: return 160, 130
    return 200, 160

st.title("🔬 Микрофокусный оптимизатор: Разрешение на объекте")

with st.sidebar:
    st.header("💡 Источник")
    f_mkm = st.number_input("Размер фокуса (мкм)", 1, 3000, 10)
    st.header("📲 Детектор")
    pixel = st.number_input("Пиксель (мкм)", value=64)
    mtf_k = st.slider("MTF (размытие)", 1.0, 3.0, 1.6)
    srb_det = pixel * mtf_k
    st.header("📐 Геометрия")
    fdd = st.slider("FDD (мм)", 100, 1000, 600)
    obj_size = st.slider("Габарит объекта (мм)", 1, 100, 10)
    wall_w = st.slider("Толщина стенок (мм)", 1, 100, 5)

# --- НОВАЯ МАТЕМАТИКА (ПРИВЕДЕНИЕ К ОБЪЕКТУ) ---
def calc_res_target(b_dist):
    a = fdd - b_dist # расстояние источник-объект
    if a <= 0.1: return f_mkm # предел при M -> inf
    m = fdd / a
    ug = f_mkm * (m - 1)  # нерезкость в плоскости детектора
    up = srb_det          # нерезкость детектора
    # Суммарная нерезкость на детекторе, деленная на увеличение
    return np.sqrt(ug**2 + up**2) / m

# Поиск минимума (теперь он смещен к источнику)
b_axis = np.linspace(0, fdd - 1, 1000)
res_axis = [calc_res_target(x) for x in b_axis]
idx_min = np.argmin(res_axis)
b_opt = b_axis[idx_min]

b_front = b_opt + (obj_size / 2)
b_back = b_opt - (obj_size / 2)
res_center = res_axis[idx_min]
limit_a, limit_b = get_iso_limits(wall_w)

# --- ИНТЕРФЕЙС ---
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Оптим. позиция центра", f"{b_opt:.1f} мм")
    st.caption(f"Увеличение M = {fdd/(fdd-b_opt):.2f}")
with c2:
    st.metric("Разрешение на объекте", f"{res_center:.1f} мкм")
    st.write("✅ Класс B" if res_center <= limit_b else "❌ Вне B")
with c3:
    st.metric("Предел (размер фокуса)", f"{f_mkm} мкм")
    st.caption("Лучшее возможное разрешение")

# --- ГРАФИК ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=b_axis, y=res_axis, name="SRb на объекте", line=dict(width=3)))
fig.add_vrect(x0=max(0, b_back), x1=min(fdd, b_front), fillcolor="orange", opacity=0.2, annotation_text="ОБЪЕКТ")
fig.add_hline(y=limit_b, line_dash="dot", line_color="green", annotation_text="Limit B")

fig.update_layout(xaxis_title="Расстояние от детектора (мм)", yaxis_title="SRb_target (мкм)",
                  yaxis_range=[0, max(res_axis)*1.1], hovermode="x")
st.plotly_chart(fig, use_container_width=True)
