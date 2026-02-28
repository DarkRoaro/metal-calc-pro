import streamlit as st
import ezdxf
import math
import numpy as np
from scipy.spatial import Voronoi
from io import BytesIO, StringIO

# --- 1. ЗАЩИТА ПАРОЛЕМ (Через Secrets) ---
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

# --- 2. ЛОГИКА РАСЧЕТА ---
class MetalLogic:
    def __init__(self):
        self.materials = {
            "Сталь": {"density": 7850, "price": 1.6},
            "Алюминий": {"density": 2700, "price": 4.8},
            "Нержавейка": {"density": 8000, "price": 6.0}
        }

    def get_dxf_length(self, file_bytes):
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
                elif e.dxftype() == 'ARC':
                    length += math.radians(e.dxf.end_angle - e.dxf.start_angle) * e.dxf.radius
                elif e.dxftype() == 'CIRCLE':
                    length += 2 * math.pi * e.dxf.radius
            return length / 1000 # в метры
        except:
            return 0

# --- 3. ГЕНЕРАТОР ДИЗАЙНА ---
def generate_voronoi(width, height, pts_count):
    points = np.random.rand(pts_count, 2) * [width, height]
    # Границы для стабильности сетки
    points = np.vstack([points, [[0,0], [width,0], [width,height], [0,height]]])
    vor = Voronoi(points)
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    for ridge in vor.ridge_vertices:
        if -1 not in ridge:
            v1, v2 = vor.vertices[ridge[0]], vor.vertices[ridge[1]]
            if (0 <= v1[0] <= width and 0 <= v1[1] <= height and 
                0 <= v2[0] <= width and 0 <= v2[1] <= height):
                msp.add_line(v1, v2)
    msp.add_lwpolyline([(0,0), (width,0), (width,height), (0,height), (0,0)])
    return doc

# --- 4. ИНТЕРФЕЙС ПРИЛОЖЕНИЯ ---
st.set_page_config(page_title="ArtMetal Pro", page_icon="⚒️")
logic = MetalLogic()

st.title("⚒️ ArtMetal: Калькулятор & Дизайн")

tab1, tab2 = st.tabs(["💰 Расчет заказа", "🎨 Генератор дизайна"])

with tab1:
    st.header("Параметры изделия")
    col1, col2 = st.columns(2)
    with col1:
        mat_name = st.selectbox("Материал", list(logic.materials.keys()))
        thick = st.number_input("Толщина (мм)", 0.5, 20.0, 3.0)
        area = st.number_input("Площадь детали (м2)", 0.01, 10.0, 0.5)
    
    with col2:
        dxf_file = st.file_uploader("Загрузить чертеж (DXF)", type="dxf")
        manual_len = st.number_input("Или введи длину реза (м)", 0.0, 500.0, 0.0)

    if st.button("РАССЧИТАТЬ СТОИМОСТЬ", type="primary"):
        cut_len = logic.get_dxf_length(dxf_file) if dxf_file else manual_len
        
        mat = logic.materials[mat_name]
        weight = area * (thick / 1000) * mat["density"]
        mat_cost = weight * mat["price"] * 1.1 # +10% отход
        work_cost = (cut_len / 0.5 / 60) * 45.0 # пример: 45 евро/час
        
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Вес", f"{round(weight, 1)} кг")
        c2.metric("Длина реза", f"{round(cut_len, 1)} м")
        c3.metric("ИТОГО", f"{round(mat_cost + work_cost, 2)} €")
        st.caption(f"Включая налог и амортизацию оборудования")

with tab2:
    st.header("Генератор паттерна Вороного")
    gw = st.number_input("Ширина (мм)", 100, 2500, 500)
    gh = st.number_input("Высота (мм)", 100, 2500, 800)
    gpts = st.slider("Сложность узора", 5, 150, 40)
    
    if st.button("Создать уникальный чертеж"):
        new_dxf = generate_voronoi(gw, gh, gpts)
        out = StringIO()
        new_dxf.write(out)
        st.download_button(
            label="📥 СКАЧАТЬ DXF ДЛЯ СТАНКА",
            data=out.getvalue(),
            file_name="generated_art.dxf",
            mime="application/dxf"
        )
        st.success("Узор готов! Теперь ты можешь загрузить этот файл во вкладку 'Расчет'.")

st.sidebar.markdown("---")
st.sidebar.info(f"Таллинн 2024 | Мехатроник-Арт")