"""
Urban Cordon Checker - كشف الحيز العمراني
نسخة احترافية محسّنة
"""

import re
import streamlit as st
from shapely.geometry import Point, Polygon
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

# ─────────────────────────────────────────────
# 1.  إعدادات الصفحة
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="كشف الحيز العمراني",
    page_icon="🗺️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# 2.  CSS مُخصَّص
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');

#MainMenu, footer, header, .stApp > header { display: none !important; }

.stApp {
    font-family: 'Cairo', sans-serif;
    background: linear-gradient(135deg, #0f1923 0%, #1a2a3a 60%, #0d2137 100%);
    min-height: 100vh;
}

.main-header {
    text-align: center;
    padding: 2rem 1rem 1rem;
    background: linear-gradient(135deg, rgba(0,180,216,0.12), rgba(0,119,182,0.08));
    border: 1px solid rgba(0,180,216,0.25);
    border-radius: 16px;
    margin-bottom: 1.5rem;
    backdrop-filter: blur(10px);
}
.main-header h1 {
    font-size: 2rem;
    font-weight: 900;
    color: #00b4d8;
    margin: 0 0 .3rem;
    letter-spacing: 1px;
}
.main-header p {
    color: rgba(255,255,255,0.55);
    margin: 0;
    font-size: .95rem;
}

.card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.2rem;
    backdrop-filter: blur(8px);
}
.card-title {
    color: #90e0ef;
    font-weight: 700;
    font-size: 1rem;
    margin-bottom: .8rem;
    display: flex;
    align-items: center;
    gap: .5rem;
}

.result-inside {
    background: linear-gradient(135deg, rgba(0,200,100,0.15), rgba(0,150,80,0.1));
    border: 1px solid rgba(0,200,100,0.4);
    border-radius: 14px;
    padding: 1.2rem 1.6rem;
    text-align: center;
    color: #4ade80;
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 1rem;
}

.result-outside {
    background: linear-gradient(135deg, rgba(220,50,50,0.15), rgba(180,30,30,0.1));
    border: 1px solid rgba(220,50,50,0.4);
    border-radius: 14px;
    padding: 1.2rem 1.6rem;
    text-align: center;
    color: #f87171;
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 1rem;
}

.coord-badge {
    background: rgba(0,180,216,0.1);
    border: 1px solid rgba(0,180,216,0.25);
    border-radius: 8px;
    padding: .5rem 1rem;
    color: #90e0ef;
    font-size: .9rem;
    text-align: center;
    margin-bottom: 1rem;
    font-family: 'Courier New', monospace;
}

div[data-testid="stTextInput"] input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(0,180,216,0.35) !important;
    border-radius: 10px !important;
    color: #e0f7fa !important;
    font-family: 'Cairo', sans-serif !important;
    font-size: 1rem !important;
    text-align: right;
    direction: rtl;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #00b4d8 !important;
    box-shadow: 0 0 0 2px rgba(0,180,216,0.2) !important;
}
div[data-testid="stTextInput"] label {
    color: #90e0ef !important;
    font-weight: 600;
}

div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #0077b6, #00b4d8) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Cairo', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    padding: .65rem 2rem !important;
    width: 100%;
    transition: all .25s ease !important;
    box-shadow: 0 4px 15px rgba(0,119,182,0.35) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(0,180,216,0.45) !important;
}

div[data-testid="stSuccess"],
div[data-testid="stError"],
div[data-testid="stWarning"],
div[data-testid="stInfo"] {
    border-radius: 10px !important;
    font-family: 'Cairo', sans-serif !important;
    direction: rtl;
}

hr { border-color: rgba(255,255,255,0.08) !important; }

div[data-testid="stIframe"] > iframe { border-radius: 14px !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 3.  حدود الحيز العمراني (205 نقطة) — (lat, lon)
# ─────────────────────────────────────────────
BOUNDARY_POINTS: list[tuple[float, float]] = [
    (30.722009, 31.295623), (30.721122, 31.295481), (30.721285, 31.294259), (30.722031, 31.294366), (30.725045, 31.294755),
    (30.730050, 31.302733), (30.730125, 31.302278), (30.729349, 31.302003), (30.729198, 31.302683), (30.729641, 31.302797),
    (30.729435, 31.303796), (30.727487, 31.303334), (30.727292, 31.304539), (30.726293, 31.304657), (30.726367, 31.304013),
    (30.725509, 31.303733), (30.725668, 31.303050), (30.725328, 31.302976), (30.725102, 31.302035), (30.724626, 31.301933),
    (30.724686, 31.300365), (30.723999, 31.300409), (30.724035, 31.299283), (30.724191, 31.299282), (30.724183, 31.299604),
    (30.724561, 31.299566), (30.724542, 31.298039), (30.724166, 31.298057), (30.724177, 31.298978), (30.723874, 31.298982),
    (30.723883, 31.298796), (30.723563, 31.298763), (30.723571, 31.299340), (30.723351, 31.299368), (30.723354, 31.299624),
    (30.723106, 31.299629), (30.723083, 31.299289), (30.722603, 31.299287), (30.722602, 31.299040), (30.722476, 31.298887),
    (30.722474, 31.298885), (30.723228, 31.298330), (30.723236, 31.298163), (30.723105, 31.298165), (30.723102, 31.297909),
    (30.722863, 31.297913), (30.722820, 31.298446), (30.722298, 31.298443), (30.722293, 31.296397), (30.724224, 31.296490),
    (30.724249, 31.295636), (30.723865, 31.295652), (30.723869, 31.295506), (30.723698, 31.295505), (30.723700, 31.295325),
    (30.723546, 31.295320), (30.723553, 31.295189), (30.723513, 31.295189), (30.723424, 31.295068), (30.723430, 31.294069),
    (30.722907, 31.294052), (30.722870, 31.295608), (30.722565, 31.295599), (30.722601, 31.295016), (30.722308, 31.294998),
    (30.722413, 31.293531), (30.722103, 31.293463), (30.722123, 31.293295), (30.722468, 31.293347), (30.722546, 31.292812),
    (30.722917, 31.292887), (30.722943, 31.292311), (30.722508, 31.292233), (30.722609, 31.291585), (30.722487, 31.291574),
    (30.722551, 31.291134), (30.722271, 31.290978), (30.722376, 31.290487), (30.723197, 31.290470), (30.723447, 31.289850),
    (30.722869, 31.289696), (30.722908, 31.289504), (30.723129, 31.289564), (30.723334, 31.288885), (30.722683, 31.288752),
    (30.722639, 31.288950), (30.722493, 31.288907), (30.722508, 31.288817), (30.722267, 31.288766), (30.722300, 31.288589),
    (30.721931, 31.288531), (30.721987, 31.288171), (30.722862, 31.287790), (30.722983, 31.287686), (30.723240, 31.287739),
    (30.723145, 31.287891), (30.724054, 31.288657), (30.724014, 31.288809), (30.723727, 31.288738), (30.723584, 31.289331),
    (30.723976, 31.289488), (30.724065, 31.289078), (30.724422, 31.289217), (30.724606, 31.287618), (30.725379, 31.287741),
    (30.725432, 31.287241), (30.726149, 31.287339), (30.726072, 31.286229), (30.726688, 31.288502), (30.726883, 31.286281),
    (30.726529, 31.286324), (30.726393, 31.285772), (30.726885, 31.285764), (30.726763, 31.285263), (30.725981, 31.285181),
    (30.726013, 31.284693), (30.726629, 31.284729), (30.726296, 31.283332), (30.727404, 31.283527), (30.727628, 31.282346),
    (30.727934, 31.282098), (30.727906, 31.282351), (30.728364, 31.282331), (30.728379, 31.282563), (30.728533, 31.282559),
    (30.728550, 31.282847), (30.728771, 31.282858), (30.728783, 31.283372), (30.728867, 31.283370), (30.728894, 31.283940),
    (30.729369, 31.283918), (30.729388, 31.284299), (30.729571, 31.284288), (30.729904, 31.285527), (30.730149, 31.285504),
    (30.730166, 31.285871), (30.730870, 31.285854), (30.730911, 31.286129), (30.731057, 31.286175), (30.731075, 31.286738),
    (30.731296, 31.286725), (30.731301, 31.286861), (30.731551, 31.286875), (30.731618, 31.286145), (30.732257, 31.286211),
    (30.732213, 31.286628), (30.732463, 31.286675), (30.733320, 31.287117), (30.733914, 31.287269), (30.733991, 31.286705),
    (30.734372, 31.286789), (30.734334, 31.287032), (30.735238, 31.287192), (30.735163, 31.287714), (30.735515, 31.287807),
    (30.735485, 31.287994), (30.735682, 31.288038), (30.736004, 31.288855), (30.735767, 31.288963), (30.736112, 31.290061),
    (30.736201, 31.290607), (30.736611, 31.290530), (30.736718, 31.292075), (30.737504, 31.292097), (30.737359, 31.293014),
    (30.737856, 31.293283), (30.737787, 31.294242), (30.737386, 31.294167), (30.736955, 31.295531), (30.736568, 31.295382),
    (30.736186, 31.296724), (30.735956, 31.296656), (30.735666, 31.297535), (30.735786, 31.297608), (30.735754, 31.297701),
    (30.736233, 31.297994), (30.735298, 31.300357), (30.735131, 31.300549), (30.735560, 31.300958), (30.735970, 31.301115),
    (30.735685, 31.302161), (30.735944, 31.302214), (30.735818, 31.302683), (30.735475, 31.301738), (30.734499, 31.301261),
    (30.734008, 31.302902), (30.734462, 31.303135), (30.734278, 31.303673), (30.734143, 31.303502), (30.734085, 31.303215),
    (30.733325, 31.302837), (30.733228, 31.303085), (30.733124, 31.303040), (30.732857, 31.304064), (30.732406, 31.303793),
    (30.732351, 31.304903), (30.731808, 31.304799), (30.731905, 31.304481), (30.730897, 31.304118), (30.730894, 31.304281),
    (30.731161, 31.304519), (30.731154, 31.303862), (30.730056, 31.303467), (30.730106, 31.303235), (30.729515, 31.303288),
    (30.722009, 31.295623),  # إغلاق المضلع
]

# ─────────────────────────────────────────────
# 4.  بناء المضلع (مرة واحدة فقط)
# ─────────────────────────────────────────────
@st.cache_resource
def build_polygon() -> Polygon:
    return Polygon([(lon, lat) for lat, lon in BOUNDARY_POINTS])

boundary_polygon = build_polygon()

# ─────────────────────────────────────────────
# 5.  دوال مساعدة
# ─────────────────────────────────────────────
def parse_dms(text: str) -> tuple | None:
    """تحويل صيغة DMS إلى عشري."""
    parts = re.findall(r"(\d+)[°](\d+)['](\d+\.?\d*)[\"]([NSEW])", text)
    if len(parts) < 2:
        return None
    results = []
    for deg, min_, sec, direction in parts:
        val = float(deg) + float(min_) / 60 + float(sec) / 3600
        if direction in ("S", "W"):
            val = -val
        results.append(val)
    return tuple(results[:2])


def parse_coords(text: str) -> tuple | None:
    """تحليل الإحداثيات من نص المستخدم (عشري أو DMS)."""
    try:
        parts = text.replace(",", " ").split()
        if len(parts) >= 2:
            lat, lon = float(parts[0]), float(parts[1])
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
    except ValueError:
        pass
    return parse_dms(text)


def build_map(lat: float, lon: float, is_inside: bool) -> folium.Map:
    """إنشاء خريطة Folium احترافية."""
    m = folium.Map(location=[lat, lon], zoom_start=17, tiles=None, prefer_canvas=True)

    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        attr="©️ Google",
        name="صور الأقمار الصناعية",
        overlay=False,
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        attr="©️ Google",
        name="خريطة عادية",
        overlay=False,
        control=True,
    ).add_to(m)

    folium.Polygon(
        locations=BOUNDARY_POINTS,
        color="#FFD700",
        weight=2.5,
        fill=True,
        fill_color="#FFD700",
        fill_opacity=0.12,
        tooltip="حدود الحيز العمراني",
    ).add_to(m)

    status_text = "داخل الحيز العمراني ✅" if is_inside else "خارج الحيز العمراني ⛔"
    folium.Marker(
        location=[lat, lon],
        tooltip=f"<b>{status_text}</b><br>({lat:.6f}, {lon:.6f})",
        icon=folium.Icon(color="green" if is_inside else "red", icon="map-marker", prefix="fa"),
    ).add_to(m)

    folium.CircleMarker(
        location=[lat, lon],
        radius=10,
        color="#00b4d8",
        fill=True,
        fill_color="#00b4d8",
        fill_opacity=0.25,
        weight=2,
    ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m

# ─────────────────────────────────────────────
# 6.  حالة الجلسة
# ─────────────────────────────────────────────
if "search_result" not in st.session_state:
    st.session_state.search_result = None
if "input_coords" not in st.session_state:
    st.session_state.input_coords = ""

# ─────────────────────────────────────────────
# 7.  الواجهة
# ─────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🗺️ كشف الحيز العمراني</h1>
    <p>أدخل إحداثيات الأرض أو استخدم موقعك الحالي للتحقق من وضعها</p>
</div>
""", unsafe_allow_html=True)

# ── بطاقة GPS ──────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">📡 تحديد الموقع تلقائياً</div>', unsafe_allow_html=True)

try:
    loc = get_geolocation(component_key="get_loc")
    if loc and "coords" in loc:
        gps_lat = loc["coords"]["latitude"]
        gps_lon = loc["coords"]["longitude"]
        st.session_state.input_coords = f"{gps_lat:.6f}, {gps_lon:.6f}"
        st.success(f"📍 تم التقاط الموقع بنجاح: **{gps_lat:.5f}**, **{gps_lon:.5f}**")
    else:
        st.info("اضغط على زر السماح بالموقع في المتصفح، أو أدخل الإحداثيات يدوياً أدناه.")
except Exception:
    st.warning("⚠️ تعذّر الوصول إلى GPS — يرجى الإدخال اليدوي.")

st.markdown("</div>", unsafe_allow_html=True)

# ── بطاقة الإدخال اليدوي ───────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">✍️ إدخال الإحداثيات يدوياً</div>', unsafe_allow_html=True)

user_input: str = st.text_input(
    label="الإحداثيات (خط العرض، خط الطول)",
    key="input_coords",
    placeholder="مثال: 30.727313, 31.284638",
    help="يقبل الصيغة العشرية (30.72, 31.28) أو صيغة الدرجات والدقائق DMS",
)

check_clicked = st.button("🔍 فحص الموقع ورسم الخريطة", type="primary")
st.markdown("</div>", unsafe_allow_html=True)

# ── المنطق الرئيسي ─────────────────────────
if check_clicked:
    if not user_input.strip():
        st.warning("⚠️ يرجى إدخال إحداثيات أولاً.")
        st.session_state.search_result = None
    else:
        parsed = parse_coords(user_input)
        if parsed:
            lat, lon = parsed
            point = Point(lon, lat)
            is_inside = boundary_polygon.contains(point)
            st.session_state.search_result = {"lat": lat, "lon": lon, "is_inside": is_inside}
        else:
            st.error("❌ صيغة الإحداثيات غير صحيحة. تأكد من الإدخال.")
            st.session_state.search_result = None

# ── النتيجة والخريطة ───────────────────────
if st.session_state.search_result:
    result = st.session_state.search_result
    lat: float = result["lat"]
    lon: float = result["lon"]
    is_inside: bool = result["is_inside"]

    st.markdown("---")

    if is_inside:
        st.markdown('<div class="result-inside">✅ الأرض داخل الحيز العمراني</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="result-outside">⛔ الأرض خارج الحيز العمراني</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="coord-badge">📌 {lat:.6f} ، {lon:.6f}</div>', unsafe_allow_html=True)

    with st.spinner("جارٍ تحميل الخريطة…"):
        folium_map = build_map(lat, lon, is_inside)
        st_folium(folium_map, width="100%", height=520, returned_objects=[])