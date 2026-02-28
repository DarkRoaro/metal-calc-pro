import streamlit as st
import ezdxf
import math
import numpy as np
from scipy.spatial import Voronoi
from io import BytesIO, StringIO
import matplotlib.pyplot as plt

# --- 1. СИСТЕМА ПАРОЛЯ (Берет пароль из Secrets) ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 ArtMetal Tallinn: Вход")
        st.text_input("Введите пароль доступа", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Введите пароль доступа", type="password", on_change=password_entered, key="password")
        st.error("😕 Неверный пароль")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. ФУНКЦИЯ ОТРИСОВКИ ЧЕРТЕЖА ---
def draw_dxf(doc):
    fig, ax = plt.subplots(figsize=(8, 8))
    msp = doc.modelspace()
    for e in msp:
        if e.dxftype() == 'LINE':
            ax.plot([e.dxf.start.x, e.dxf.end.x], [e.dxf.start.y, e.dxf.end.y], color='black', lw=0.7)
        elif e.dxftype() == 'LWPOLYLINE':
            pts = np.array(list(e.get_points()))
            ax.plot(pts[:, 0], pts[:, 1], color='black', lw=0.7)
        elif e.dxftype() == 'CIRCLE':
            circle = plt.Circle((e.dxf.center.x, e.dxf.center.y), e.dxf.radius, color='black', fill=False, lw=0.7)
            ax.add_patch(circle)
        elif e.dxftype() == 'ARC':
            # Упрощенная отрисовка дуги через точки
            pts = list(e.flattening(0.1))
            ax.plot([p.x for p in pts], [p.y for p in pts], color='black', lw=0.7)
            
    ax.set_aspect('equal')
    ax.axis('off')
    return fig

# --- 3. ЛОГИКА РАСЧЕТОВ ---
class MetalLogic:
    def __init__(self):
        self.materials = {
            "Сталь": {"density": 7850, "price": 1.6},
            "Алюминий": {"density": 2700, "price": 4.8},
            "Нержавейка": {"density": 8000, "price": 6.0}
        }

    def get_stats(self, file_bytes):
        try:
            doc = ezdxf.readfile(BytesIO(file_bytes.read()))
            msp = doc.modelspace()
            length = 0
            for e in msp:
                if e.dxftype() == 'LINE':
                    length += math.dist(e.dxf.start, e.dxf.end)
                elif e.dxftype() == 'LWPOLYLINE':
                    pts = e.get_points()
                    for i in range(len(pts)-1):
                        length += math.dist(pts[i], pts[i+1])
                elif e.dxftype() == 'CIRCLE':
                    length += 2 * math.pi * e.dxf.radius
                elif e.dxftype() == 'ARC':
                    length += math.radians(abs(e.dxf.end_angle - e.dxf.start_angle)) * e.dxf.radius
            return length / 1000, doc
        except:
            return 0, None

# --- 4. ГЕНЕРАТОР ДИЗАЙНА ---
def generate_voronoi(w, h, pts_count):
    # Генерируем случайные точки
    points = np.random.rand(pts_count, 2) * [w, h]
    
    # Добавляем жесткие границы, чтобы узор не «улетал»
    boundary = np.array([[0, 0], [w, 0], [w, h], [0, h]])
    points = np.vstack([points, boundary])
    
    vor = Voronoi(points)
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    for r in vor.ridge_vertices:
        if -1 not in r:
            v1 = vor.vertices[r[0]]
            v2 = vor.vertices[r[1]]
            
            # Правильная проверка: лежат ли обе точки внутри нашего листа
            # Проверяем X и Y для каждой точки отдельно
            if (0 <= v1[0] <= w and 0 <= v1[1] <= h and 
                0 <= v2[0] <= w and 0 <= v2[1] <= h):
                msp.add_line(v1, v2)
                
    # Добавляем рамку листа (контур)
    msp.add_lwpolyline([(0,0), (w,0), (w,h), (0,h), (0,0)])
    return doc

# --- 5. ИНТЕРФЕЙС ПРИЛОЖЕНИЯ ---
st.set_page_config(page_title="ArtMetal Tallinn", page_icon="⚒️")
logic = MetalLogic()

st.title("⚒️ ArtMetal: Дизайн и Расчет")

tab1, tab2 = st.tabs(["💰 Калькулятор заказа", "🎨 Генератор узоров"])

with tab1:
    st.header("Расчет по чертежу")
    col1, col2 = st.columns(2)
    
    with col1:
        mat_name = st.selectbox("Металл", list(logic.materials.keys()))
        thick = st.number_input("Толщина (мм)", 0.5, 30.0, 3.0)
        area = st.number_input("Площадь заготовки (м2)", 0.01, 10.0, 0.5)
        speed = st.slider("Скорость резки (м/мин)", 0.1, 5.0, 0.5)
    
    with col2:
        dxf_file = st.file_uploader("Загрузи свой DXF", type="dxf")
    
    if dxf_file:
        cut_len, doc = logic.get_stats(dxf_file)
        if doc:
            st.pyplot(draw_dxf(doc)) # Визуализация загруженного файла
            
            mat = logic.materials[mat_name]
            weight = area * (thick / 1000) * mat["density"]
            mat_cost = weight * mat["price"] * 1.1 # +10% отход
            work_time_min = cut_len / speed
            work_cost = (work_time_min / 60) * 50.0 # 50€/час работы
            
            st.divider()
            res1, res2, res3 = st.columns(3)
            res1.metric("Вес", f"{round(weight, 1)} кг")
            res2.metric("Длина реза", f"{round(cut_len, 2)} м")
            res3.metric("ЦЕНА", f"{round(mat_cost + work_cost, 2)} €")
            st.info(f"Время резки станка: {round(work_time_min, 1)} мин.")

with tab2:
    st.header("Генератор дизайна (Вороной)")
    gw = st.number_input("Ширина листа (мм)", 100, 2500, 500)
    gh = st.number_input("Высота листа (мм)", 100, 2500, 800)
    gpts = st.slider("Плотность узора", 5, 150, 40)
    
    if st.button("Сгенерировать новый дизайн"):
        new_doc = generate_voronoi(gw, gh, gpts)
        st.pyplot(draw_dxf(new_doc)) # Визуализация сгенерированного узора
        
        out = StringIO()
        new_doc.write(out)
        st.download_button(
            label="📥 СКАЧАТЬ DXF ДЛЯ ЛАЗЕРА",
            data=out.getvalue(),
            file_name="art_design.dxf",
            mime="application/dxf"
        )

st.sidebar.markdown("---")
st.sidebar.write("📍 **Tallinn, Lasnamäe / TTÜ**")
st.sidebar.write("🛠️ Приложение для мехатроника-художника")