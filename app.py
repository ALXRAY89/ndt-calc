import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Ultra NDT Optimizer v8", layout="wide")

# --- Справочники ---
def get_iso_limits(w):
    if w <= 1.2: return 50, 40
    if w <= 5.0: return 100, 80
    if w <= 12: return 130, 100
    if w <= 40: return 160, 130
    return 200, 160

materials = {
    "Алюминий": 1.0, 
    "Титан": 1.7,
    "Сталь": 2.9, 
    "Нерж. сталь": 3.0
}

st.title("🔬 Advanced NDT & Microfocus Optimizer v8")

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

# --- МАТЕМАТИКА (РАСЧЕТ В ПЛОСКОСТИ ОБЪЕКТА) ---
def calc_res_target(b_dist):
    a = fdd - b_dist # расстояние источник-объект
    if a <= 0.5: return f_mkm # предел у фокуса
    m = fdd / a
    # Нерезкость в плоскости объекта:
    # Ug_target = f * (b/a) / M = f * (b/fdd)
    # Up_target = pixel_det / M
    ug_t = f_mkm * (b_dist / fdd)
    up_t = srb_det / m
    return np.sqrt(ug_t**2 + up_t**2)

# Поиск минимума (оптимальное положение b)
b_axis = np.linspace(0, fdd * 0.98, 1000)
res_axis = [calc_res_target(x) for x in b_axis]
idx_min = np.argmin(res_axis)
b_opt = b_axis[idx_min]

# Параметры для выбранной точки
b_front = b_opt + (obj_size / 2)
b_back = b_opt - (obj_size / 2)
res_center = res_axis[idx_min]
res_worst = max(calc_res_target(b_front), calc_res_target(b_back))
limit_a, limit_b = get_iso_limits(wall_w)

# --- ИНТЕРФЕЙС ВЫВОДА ---
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
    exp_factor = materials[material] * (wall_w / 10)
    st.metric("Сложность экспо", f"{exp_factor:.1f} x")

# --- ГРАФИК ---
fig = go.Figure()
# Основная кривая
fig.add_trace(go.Scatter(x=b_axis, y=res_axis, name="Разрешение на объекте", line=dict(width=3, color='#1f77b4')))

# Визуализация габарита объекта
fig.add_vrect(x0=max(0, b_back), x1=min(fdd, b_front), 
              fillcolor="rgba(255, 127, 14, 0.2)", line_width=0,
              annotation_text="ОБЪЕКТ", annotation_position="top left")

# Точка оптимума
fig.add_trace(go.Scatter(x=[b_opt], y=[res_center], mode='markers', 
                         marker=dict(size=12, color='red', symbol='diamond'), name="Оптимум"))

fig.add_hline(y=limit_b, line_dash="dot", line_color="green", annotation_text="Limit B")

fig.update_layout(
    xaxis_title="Расстояние от детектора (мм)",
    yaxis_title="SRb на объекте (мкм)",
    yaxis_range=[0, min(max(res_axis), res_center*5)],
    hovermode="x unified",
    template="plotly_white"
)
st.plotly_chart(fig, use_container_width=True)

st.info(f"**Анализ:** Для фокуса {f_mkm} мкм минимальное разрешение составляет {res_center:.1f} мкм. "
        f"Удаление объекта от детектора (рост b) улучшает разрешение за счет увеличения M, "
        f"пока геометрическая нерезкость фокуса не начнет доминировать.")
