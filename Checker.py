import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
from shapely.geometry import Point, Polygon
import re
import os

# ----------------------------
# إعدادات الصفحة
# ----------------------------
st.set_page_config(page_title="Urban Cordon Checker", page_icon="🌍", layout="wide")

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stApp > header {display: none;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ----------------------------
# Session State
# ----------------------------
if "search_result" not in st.session_state:
    st.session_state.search_result = None
if "input_coords" not in st.session_state:
    st.session_state.input_coords = ""

# ----------------------------
# Helpers
# ----------------------------
def dms_to_decimal(deg, minute, sec, sign=1):
    return sign * (float(deg) + float(minute)/60.0 + float(sec)/3600.0)

def parse_decimal_or_dms_text(user_input: str):
    """يدعم إدخال المستخدم: decimal أو DMS نصي."""
    if not user_input:
        return None

    # Decimal: "lat, lon"
    try:
        clean = user_input.replace(",", " ").split()
        if len(clean) >= 2:
            lat = float(clean[0])
            lon = float(clean[1])
            return lat, lon
    except:
        pass

    # DMS نصي: 30°43'12.1"N 31°17'04.2"E
    try:
        parts = re.findall(r"(\d+)[°](\d+)['](\d+\.?\d*)[\"]([NSEW])", user_input)
        if len(parts) >= 2:
            def one(part):
                deg, m, s, d = part
                val = float(deg) + float(m)/60 + float(s)/3600
                if d in ["S","W"]:
                    val = -val
                return val
            lat = one(parts[0])
            lon = one(parts[1])
            return lat, lon
    except:
        pass

    return None

def order_points_by_angle(latlon_points):
    """
    إعادة ترتيب نقاط (lat, lon) حول مركزها لتكوين محيط بدون قفزات كبيرة.
    مفيد عندما يكون ترتيب الجدول غير مرتب على محيط الحدود.
    """
    pts = np.array(latlon_points, dtype=float)  # [ [lat, lon], ... ]
    center = pts.mean(axis=0)
    angles = np.arctan2(pts[:,0] - center[0], pts[:,1] - center[1])  # atan2(lat-center, lon-center)
    order = np.argsort(angles)
    ordered = [tuple(pts[i]) for i in order]
    return ordered

def close_ring(points):
    if points and points[0] != points[-1]:
        return points + [points[0]]
    return points

def build_safe_polygon(latlon_points):
    """
    يبني Polygon “آمن”:
    1) يرتب النقاط حول المركز
    2) يغلق الحلقة
    3) يحول لـ Shapely (lon, lat)
    4) لو فيه تقاطع ذاتي، يعالجه بـ buffer(0)
    """
    ordered = order_points_by_angle(latlon_points)
    ordered = close_ring(ordered)

    poly = Polygon([(lon, lat) for lat, lon in ordered])

    # محاولة إصلاح لو polygon غير صالح (self-intersection)
    if not poly.is_valid:
        poly = poly.buffer(0)

    # لو مازال غير صالح أو فاضي
    if poly.is_empty:
        return None, ordered

    # بعد الإصلاح، قد يكون الناتج MultiPolygon أحيانًا، لكننا نستخدم covers لاحقًا بشكل آمن.
    return poly, ordered

def load_points_file():
    """
    يقرأ points.csv أو points.xlsx من نفس مجلد التطبيق.
    """
    if os.path.exists("points.csv"):
        df = pd.read_csv("points.csv")
        return df, "points.csv"
    if os.path.exists("points.xlsx"):
        df = pd.read_excel("points.xlsx")
        return df, "points.xlsx"
    return None, None

def df_to_latlon(df):
    """
    df columns:
    Point | East_D | East_M | East_S | North_D | North_M | North_S
    East = Longitude (E positive)
    North = Latitude (N positive)
    """
    required = {"Point","East_D","East_M","East_S","North_D","North_M","North_S"}
    if not required.issubset(set(df.columns)):
        raise ValueError("ملف النقاط لا يحتوي الأعمدة المطلوبة.")

    # Longitude (East)
    lon = df.apply(lambda r: dms_to_decimal(r["East_D"], r["East_M"], r["East_S"], sign=1), axis=1)
    # Latitude (North)
    lat = df.apply(lambda r: dms_to_decimal(r["North_D"], r["North_M"], r["North_S"], sign=1), axis=1)

    out = pd.DataFrame({
        "Point": df["Point"].astype(int),
        "lat": lat.astype(float),
        "lon": lon.astype(float)
    }).sort_values("Point")

    return out

# ----------------------------
# UI
# ----------------------------
st.title("🌍 كشف الحيز العمراني")
st.caption("النقاط تُقرأ من ملف points.csv أو points.xlsx. أول 4 نقاط Polygon منفصل، والباقي Polygon رئيسي.")

df_raw, fname = load_points_file()
if df_raw is None:
    st.error("لم أجد ملف النقاط. ضع points.csv أو points.xlsx في نفس مجلد التطبيق (Repository).")
    st.stop()

try:
    pts_df = df_to_latlon(df_raw)
except Exception as e:
    st.error(f"خطأ في قراءة الملف: {e}")
    st.stop()

# Split first 4 points (Point 1-4) and main (5-205)
sub_df = pts_df[pts_df["Point"].between(1,4)]
main_df = pts_df[~pts_df["Point"].between(1,4)]

sub_points = list(zip(sub_df["lat"], sub_df["lon"]))
main_points = list(zip(main_df["lat"], main_df["lon"]))

sub_poly, sub_ring = build_safe_polygon(sub_points)
main_poly, main_ring = build_safe_polygon(main_points)

if sub_poly is None or main_poly is None:
    st.error("تعذر تكوين Polygon صالح من النقاط (قد يكون هناك تكرار/نقاط غير كافية/أخطاء إدخال).")
    st.stop()

# ----------------------------
# GPS box
# ----------------------------
st.markdown("""
<div style="direction: rtl; text-align: center; border: 2px solid #FF4B4B; padding: 15px; border-radius: 10px; margin-bottom: 15px; background-color: #f9f9f9;">
    <h4 style="margin: 0; color: #31333F;">📍 استخدم موقعك الحالي</h4>
</div>
""", unsafe_allow_html=True)

try:
    loc = get_geolocation(component_key="get_loc")
    if loc:
        current_lat = loc["coords"]["latitude"]
        current_lon = loc["coords"]["longitude"]
        st.session_state.input_coords = f"{current_lat}, {current_lon}"
        st.success(f"📍 تم التقاط الموقع: {current_lat:.6f}, {current_lon:.6f}")
except Exception:
    st.warning("⚠️ يرجى تفعيل الموقع أو الإدخال اليدوي.")

st.write("---")
st.write("📝 **أو أدخل الإحداثيات يدوياً (Decimal أو DMS):**")
user_input = st.text_input("الإحداثيات:", key="input_coords", placeholder="30.727313, 31.284638")

if st.button("فحص الموقع ورسم الخريطة", type="primary"):
    parsed = parse_decimal_or_dms_text(user_input)
    if not parsed:
        st.warning("❌ تأكد من صحة الإدخال.")
        st.session_state.search_result = None
    else:
        lat, lon = parsed
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            st.warning("❌ نطاق الإحداثيات غير صحيح.")
            st.session_state.search_result = None
        else:
            p = Point(lon, lat)  # Shapely (lon, lat)
            inside = (sub_poly.covers(p) or main_poly.covers(p))
            st.session_state.search_result = {"lat": lat, "lon": lon, "is_inside": inside}

# ----------------------------
# Result + Map
# ----------------------------
if st.session_state.search_result is not None:
    r = st.session_state.search_result
    lat, lon, inside = r["lat"], r["lon"], r["is_inside"]

    st.markdown("---")
    if inside:
        st.success("✅ **النتيجة: الأرض داخل الحيز العمراني.**")
    else:
        st.error("⛔ **النتيجة: الأرض خارج الحيز العمراني.**")
    st.info(f"الإحداثيات: {lat}, {lon}")

    m = folium.Map(location=[lat, lon], zoom_start=17, control_scale=True)

    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        attr="Google",
        name="Google Satellite",
        overlay=False,
        control=True
    ).add_to(m)

    folium.TileLayer("OpenStreetMap", name="OpenStreetMap", overlay=False, control=True).add_to(m)

    # رسم المضلع الرئيسي (مرتّب)
    folium.Polygon(
        locations=main_ring,  # (lat, lon)
        color="yellow",
        weight=3,
        fill=True,
        fill_opacity=0.20,
        popup="الحيز العمراني (الرئيسي)"
    ).add_to(m)

    # رسم الجزء المنفصل (مرتّب)
    folium.Polygon(
        locations=sub_ring,
        color="orange",
        weight=3,
        fill=True,
        fill_opacity=0.25,
        popup="جزء منفصل من الحيز"
    ).add_to(m)

    folium.Marker(
        [lat, lon],
        popup="موقع الأرض",
        icon=folium.Icon(color="green" if inside else "red", icon="info-sign")
    ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    st_folium(m, width=None, height=560)

# Debug (اختياري)
with st.expander("عرض معلومات النقاط (Debug)"):
    st.write(f"مصدر النقاط: {fname}")
    st.write("عدد نقاط الجزء المنفصل:", len(sub_df))
    st.write("عدد نقاط الحيز الرئيسي:", len(main_df))
    st.write("صلاحية sub_poly:", sub_poly.is_valid)
    st.write("صلاحية main_poly:", main_poly.is_valid)
    st.dataframe(pts_df.head(10))
