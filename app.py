import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="NDT ISO Pro Optimizer", layout="wide")

# --- Справочники ISO 17636-2 ---
def get_iso_limits(w):
    if w <= 1.2: return 50, 40
    if w <= 5.0: return 100, 80
    if w <= 12: return 130, 100
    if w <= 40: return 160, 130
    return 200, 160

materials = {"Алюминий": 1.0, "Титан": 1.7, "Сталь": 2.9, "Нерж. сталь": 3.0}

st.title("🔬 Продвинутый NDT & Микрофокус Оптимизатор")

# --- ПАНЕЛЬ УПРАВЛЕНИЯ С ПОДСКАЗКАМИ ---
with st.sidebar:
    st.header("💡 Источник")
    src_type = st.radio("Диапазон фокуса", ["Микро (1-100 мкм)", "Макро (0.1-3 мм)"], 
                        help="Выбор масштаба для удобства регулировки фокусного пятна.")
    
    if src_type == "Микро (1-100 мкм)":
        f_mkm = st.slider("Размер фокуса (мкм)", 1, 100, 10, 
                          help="Фактический размер излучающей области анода. Определяет предел разрешения при большом увеличении.")
    else:
        f_mkm = st.slider("Размер фокуса (мм)", 0.1, 3.0, 0.4, 0.1, 
                          help="Для стандартных трубок. Большая величина фокуса требует минимизации расстояния объект-детектор.")
    
    st.header("📲 Детектор")
    pixel = st.number_input("Пиксель (мкм)", value=64, 
                            help="Физический размер шага пикселей матрицы (Pixel Pitch).")
    mtf_k = st.slider("MTF (размытие)", 1.0, 3.0, 1.6, 
                      help="Коэффициент ухудшения разрешения из-за рассеяния света в сцинтилляторе. 1.6 — типично для CsI, 2.0+ — для Gadox.")
    srb_det = pixel * mtf_k

    st.header("📐 Геометрия и Объект")
    fdd = st.slider("FDD (мм)", 200, 1000, 600, 
                    help="Focus-to-Detector Distance. Общее расстояние от источника до детектора.")
    obj_size = st.slider("Габарит образца (мм)", 1, 100, 20, 
                         help="Размер объекта вдоль оси просвечивания. Позволяет оценить разницу разрешения между передней и задней стенками.")
    wall_w = st.slider("Толщина стенок (мм)", 1, 100, 10, 
                       help="Суммарная толщина поглощающего материала. Используется для определения лимитов разрешения по ISO 17636-2.")
    material = st.selectbox("Материал", list(materials.keys()), 
                            help="Тип материала влияет на расчет относительной сложности экспозиции.")

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

b_front = b_opt + (obj_size / 2)
b_back = b_opt - (obj_size / 2)
res_center = res_axis[idx_min]
res_worst = max(calc_res_target(b_front), calc_res_target(b_back))
limit_a, limit_b = get_iso_limits(wall_w)
m_val = fdd / (fdd - b_opt)

# --- ИНТЕРФЕЙС ВЫВОДА ---
c1, c2, c3, c4 = st.columns(4)
with c1: 
    st.metric("Оптим. позиция", f"{b_opt:.1f} мм", help="Расстояние от детектора до центра объекта для наилучшего разрешения.")
    st.caption(f"M = {m_val:.2f}")
with c2: 
    st.metric("SRb (Центр)", f"{res_center:.1f} мкм", help="Пространственное разрешение в центре объекта (в его плоскости).")
    st.write("✅ Класс B" if res_worst <= limit_b else "❌ Вне B")
with c3: 
    st.metric("Худшее (Края)", f"{res_worst:.1f} мкм", help="Максимальная нерезкость на границах габарита объекта.")
    st.caption(f"Лимит B: {limit_b} мкм")
with c4: 
    exp_factor = materials[material] * (wall_w / 10)
    st.metric("Сложность", f"{exp_factor:.1f} x", help="Относительный коэффициент времени экспозиции по сравнению с 10 мм алюминия.")

# --- ГРАФИК ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=b_axis, y=res_axis, name="SRb на объекте", line=dict(width=4, color='#1f77b4')))

fig.add_vrect(x0=max(0, b_back), x1=min(fdd, b_front), 
              fillcolor="rgba(255, 127, 14, 0.2)", line_width=0,
              annotation_text="ОБЪЕКТ", annotation_position="top left")

fig.add_trace(go.Scatter(x=[b_opt], y=[res_center], mode='markers', 
                         marker=dict(size=12, color='red', symbol='diamond'), name="Оптимум"))

fig.add_hline(y=limit_b, line_dash="dot", line_color="green", annotation_text="Лимит Класса B")

fig.update_layout(
    xaxis_title="Расстояние от детектора 'b' (мм)",
    yaxis_title="Разрешение SRb на объекте (мкм)",
    yaxis_range=[0, min(max(res_axis), res_center*5)],
    hovermode="x unified",
    template="plotly_white"
)
st.plotly_chart(fig, use_container_width=True)

# --- ТЕКСТОВЫЙ ПРОТОКОЛ ---
st.divider()
st.subheader("📋 Протокол рекомендуемых параметров")

report_text = f"""ПРОТОКОЛ РАСЧЕТА NDT (ISO 17636-2)
--------------------------------------
ОБЪЕКТ: {material}, толщина {wall_w} мм
СИСТЕМА: Фокус {f_mkm} мкм, Детектор {srb_det:.1f} мкм (эфф.)
--------------------------------------
РЕКОМЕНДУЕМАЯ ГЕОМЕТРИЯ:
- Дистанция FDD: {fdd} мм
- Позиция центра объекта (b): {b_opt:.1f} мм от детектора
- Увеличение (M): {m_val:.2f}
--------------------------------------
РЕЗУЛЬТАТ:
- SRb в центре: {res_center:.1f} мкм
- Худшее SRb в объеме: {res_worst:.1f} мкм
- Лимит Класса B: {limit_b} мкм
- СТАТУС: {"✅ СООТВЕТСТВУЕТ" if res_worst <= limit_b else "❌ НЕ СООТВЕТСТВУЕТ"}
--------------------------------------"""

st.code(report_text, language="text")
st.info("💡 Наведите на знак вопроса рядом с параметрами в меню для получения справки.")
