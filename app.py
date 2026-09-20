import io
import streamlit as st
import ezdxf
from ezdxf.enums import TextEntityAlignment

# ==============================================================================
# 1. محرك الأوتوكاد والرسم الهندسي (CAD & DXF Generator Engine)
# ==============================================================================
def generate_glass_dxf(
    template: str,
    W_wall: float,
    H_wall: float,
    W_door: float,
    H_door: float,
    X_door: float,
    glass_thick: int,
    glass_type: str,
    glass_color: str,
    hardware_finish: str,
    gaps: dict
) -> bytes:
    """
    محرك توليد ملف الأوتوكاد DXF التلقائي شاملاً الواجهة، الألواح، الخلوصات، وجدول الـ BOM
    """
    # استخراج الخوصات الاسمية
    g_bot = gaps["G_bot"]["nom"]
    g_top = gaps["G_top"]["nom"]
    g_mid = gaps["G_mid"]["nom"]
    g_side = gaps["G_side"]["nom"]
    g_frame = gaps["G_frame"]["nom"]

    # حساب هندسة ودلف الأبواب
    if template == "B":  # باب مزدوج
        w_single_door = (W_door - (2 * g_side) - g_mid) / 2.0
        num_doors = 2
    elif template in ["A", "C"]:  # باب مفرد
        w_single_door = W_door - (2 * g_side)
        num_doors = 1
    else:  # قاطع ثابت بدون أبواب (D)
        w_single_door = 0.0
        num_doors = 0

    h_door_panel = H_door - g_bot - g_top if num_doors > 0 else 0.0

    # حساب الوزن الشامل لوزن لوح الباب (+10% معامل أمان)
    door_weight_raw = (w_single_door / 1000.0) * (h_door_panel / 1000.0) * glass_thick * 2.5
    door_weight_total = door_weight_raw * 1.10 if num_doors > 0 else 0.0

    # اختيار قدرة الماكينة الأرضية
    if num_doors == 0:
        spring_model = "N/A (Fixed Partition)"
    elif door_weight_total <= 75:
        spring_model = "Floor Spring EN3 (Cap <= 75 kg)"
    elif door_weight_total <= 105:
        spring_model = "Floor Spring EN4 (Cap <= 105 kg)"
    elif door_weight_total <= 150:
        spring_model = "Floor Spring EN5 Heavy Duty (Cap <= 150 kg)"
    else:
        spring_model = "CRITICAL: Custom Heavy Pivot System (>150 kg)"

    # إنشاء ملف DXF وتأسيس الطبقات
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # إنشاء الطبقات والألوان
    doc.layers.add("A-WALL-OUTLINE", color=2)   # أصفر (الفتحة المعمارية)
    doc.layers.add("A-GLASS-FIXED", color=4)    # سماوي (الزجاج الثابت والفرامة)
    doc.layers.add("A-GLASS-DOOR", color=1)     # أحمر (الأبواب المتحركة)
    doc.layers.add("A-HARDWARE", color=3)       # أخضر (الإكسسوارات والماكينة)
    doc.layers.add("A-TABLE", color=7)          # أبيض (جدول البيانات BOM)

    # 1. رسم حدود الفتحة المعمارية الخارجية
    msp.add_lwpolyline(
        [(0, 0), (W_wall, 0), (W_wall, H_wall), (0, H_wall)],
        close=True,
        dxfattribs={"layer": "A-WALL-OUTLINE"}
    )

    # 2. رسم ألواح الزجاج بناءً على النموذج
    if template in ["A", "B", "C"]:
        # اللوح الثابت الأيسر
        w_left_fixed = X_door - g_frame - (g_side / 2.0)
        if w_left_fixed > 0:
            msp.add_lwpolyline(
                [
                    (g_frame, g_frame),
                    (g_frame + w_left_fixed, g_frame),
                    (g_frame + w_left_fixed, H_wall - g_frame),
                    (g_frame, H_wall - g_frame)
                ],
                close=True,
                dxfattribs={"layer": "A-GLASS-FIXED"}
            )

        # الفرامة العلوية فوق الباب
        h_transom = H_wall - H_door - g_frame
        if h_transom > 0:
            msp.add_lwpolyline(
                [
                    (X_door, H_door + (g_top / 2.0)),
                    (X_door + W_door, H_door + (g_top / 2.0)),
                    (X_door + W_door, H_wall - g_frame),
                    (X_door, H_wall - g_frame)
                ],
                close=True,
                dxfattribs={"layer": "A-GLASS-FIXED"}
            )

        # دلف الأبواب والإكسسوارات
        if template == "B":  # باب مزدوج
            x_d1 = X_door + g_side
            # الدلفة اليسرى
            msp.add_lwpolyline(
                [
                    (x_d1, g_bot),
                    (x_d1 + w_single_door, g_bot),
                    (x_d1 + w_single_door, g_bot + h_door_panel),
                    (x_d1, g_bot + h_door_panel)
                ],
                close=True,
                dxfattribs={"layer": "A-GLASS-DOOR"}
            )
            # الدلفة اليمنى
            x_d2 = x_d1 + w_single_door + g_mid
            msp.add_lwpolyline(
                [
                    (x_d2, g_bot),
                    (x_d2 + w_single_door, g_bot),
                    (x_d2 + w_single_door, g_bot + h_door_panel),
                    (x_d2, g_bot + h_door_panel)
                ],
                close=True,
                dxfattribs={"layer": "A-GLASS-DOOR"}
            )
            # رسم تمثيلي لماكينات الأرضية
            msp.add_lwpolyline([(x_d1, 0), (x_d1 + 120, 0), (x_d1 + 120, g_bot), (x_d1, g_bot)], close=True, dxfattribs={"layer": "A-HARDWARE"})
            msp.add_lwpolyline([(x_d2 + w_single_door - 120, 0), (x_d2 + w_single_door, 0), (x_d2 + w_single_door, g_bot), (x_d2 + w_single_door - 120, g_bot)], close=True, dxfattribs={"layer": "A-HARDWARE"})

        else:  # باب مفرد (A أو C)
            x_d = X_door + g_side
            msp.add_lwpolyline(
                [
                    (x_d, g_bot),
                    (x_d + w_single_door, g_bot),
                    (x_d + w_single_door, g_bot + h_door_panel),
                    (x_d, g_bot + h_door_panel)
                ],
                close=True,
                dxfattribs={"layer": "A-GLASS-DOOR"}
            )
            # رسم تمثيلي لماكينة الأرضية
            msp.add_lwpolyline([(x_d, 0), (x_d + 120, 0), (x_d + 120, g_bot), (x_d, g_bot)], close=True, dxfattribs={"layer": "A-HARDWARE"})

        # اللوح الثابت الأيمن
        x_right_start = X_door + W_door + (g_side / 2.0)
        w_right_fixed = W_wall - x_right_start - g_frame
        if w_right_fixed > 0:
            msp.add_lwpolyline(
                [
                    (x_right_start, g_frame),
                    (x_right_start + w_right_fixed, g_frame),
                    (x_right_start + w_right_fixed, H_wall - g_frame),
                    (x_right_start, H_wall - g_frame)
                ],
                close=True,
                dxfattribs={"layer": "A-GLASS-FIXED"}
            )

    elif template == "D":  # قاطع ثابت كامل
        msp.add_lwpolyline(
            [
                (g_frame, g_frame),
                (W_wall - g_frame, g_frame),
                (W_wall - g_frame, H_wall - g_frame),
                (g_frame, H_wall - g_frame)
            ],
            close=True,
            dxfattribs={"layer": "A-GLASS-FIXED"}
        )

    # 3. إنشاء جدول التقطيع والمواصفات الفنية (BOM Table)
    table_x = W_wall + 500
    table_y = H_wall
    table = msp.add_table(
        insert=(table_x, table_y),
        nrows=9,
        ncols=3,
        width=2200,
        height=950,
        dxfattribs={"layer": "A-TABLE"}
    )

    bom_data = [
        ["ITEM / SPECIFICATION", "CALCULATED VALUE", "TOLERANCES & NOTES"],
        ["Partition Model", f"Template Model ({template})", f"Overall Size: {W_wall:.0f}x{H_wall:.0f} mm"],
        ["Glass Specification", f"{glass_thick}mm Tempered ({glass_type})", f"Glass Color: {glass_color}"],
        ["Door Leaf Cut Size", f"{w_single_door:.1f} x {h_door_panel:.1f} mm" if num_doors > 0 else "N/A", f"G_bot={g_bot}mm | G_top={g_top}mm"],
        ["Leaf Weight (Raw / Safety)", f"{door_weight_raw:.1f} kg / {door_weight_total:.1f} kg" if num_doors > 0 else "N/A", "Includes +10% Operational Safety"],
        ["Floor Spring Capacity", spring_model, f"Hardware Finish: {hardware_finish}"],
        ["Bottom & Top Gaps", f"G_bot={g_bot}mm | G_top={g_top}mm", f"Limits: Bot[{gaps['G_bot']['min']}-{gaps['G_bot']['max']}]mm"],
        ["Side & Frame Gaps", f"G_side={g_side}mm | G_frame={g_frame}mm", f"Limits: Frame[{gaps['G_frame']['min']}-{gaps['G_frame']['max']}]mm"],
        ["Factory Edge Rules", "Flat Polish All Edges & Drill", "DO NOT CUT OR DRILL AFTER TEMPERING"]
    ]

    for r, row in enumerate(bom_data):
        for c, val in enumerate(row):
            cell = table.get_cell(r, c)
            cell.text = str(val)
            cell.text_alignment = TextEntityAlignment.MIDDLE_CENTER

    # تصدير كملف بايتات لـ Streamlit
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


# ==============================================================================
# 2. واجهة المستخدم التفاعلية (Streamlit UI Application)
# ==============================================================================
def main():
    st.set_page_config(page_title="حاسبة ورسومات الزجاج السكويريت", layout="wide", page_icon="📐")

    st.title("📐 تطبيق تفصيل الزجاج السكويريت وتوليد رسومات الأوتوكاد")
    st.caption("برنامج حساب الخلوصات، الأوزان، قدرة الماكينات الأرضية، وتوليد ملفات DXF معتمدة")

    # --------------------------------------------------------------------------
    # الشريط الجانبي: مواصفات الزجاج والفواصل
    # --------------------------------------------------------------------------
    st.sidebar.header("⚙️ مواصفات الزجاج والإكسسوارات")

    glass_thick = st.sidebar.selectbox("سمك الزجاج (مم)", [10, 12, 15, 19], index=1)
    glass_type = st.sidebar.selectbox("نوع الزجاج", ["شفاف (Clear)", "سوبر شفاف (Extra Clear)", "فاميه / مظلل (Tinted)", "مثلج (Frosted)"])
    glass_color = st.sidebar.selectbox("لون الزجاج", ["بدون / شفاف", "رمادي (Grey)", "برونزي (Bronze)", "أخضر (Dark Green)", "أزرق (Blue)"])
    hardware_finish = st.sidebar.selectbox("تشطيب الإكسسوارات", ["S.S Satin (ستانلس مط)", "Polished Chrome (كروم لامع)", "Matte Black (أسود مط)", "Brushed Gold (ذهبي)"])

    st.sidebar.markdown("---")
    st.sidebar.header("📏 نطاقات الخلوصات والفواصل (مم)")

    g_bot_nom = st.sidebar.slider("خلوص أسفل الباب (G_bot)", min_value=6.0, max_value=12.0, value=8.0, step=0.5)
    g_top_nom = st.sidebar.slider("فاصل أعلى الباب / الفرامة (G_top)", min_value=3.0, max_value=6.0, value=4.0, step=0.5)
    g_mid_nom = st.sidebar.slider("فاصل دلففتي الباب المزدوج (G_mid)", min_value=3.0, max_value=6.0, value=4.0, step=0.5)
    g_side_nom = st.sidebar.slider("فاصل الزجاج الثابت والباب (G_side)", min_value=3.0, max_value=6.0, value=4.0, step=0.5)
    g_frame_nom = st.sidebar.slider("خلوص قطاع U الجانبي (G_frame)", min_value=4.0, max_value=10.0, value=5.0, step=0.5)

    gaps_config = {
        "G_bot": {"min": 6.0, "nom": g_bot_nom, "max": 12.0},
        "G_top": {"min": 3.0, "nom": g_top_nom, "max": 6.0},
        "G_mid": {"min": 3.0, "nom": g_mid_nom, "max": 6.0},
        "G_side": {"min": 3.0, "nom": g_side_nom, "max": 6.0},
        "G_frame": {"min": 4.0, "nom": g_frame_nom, "max": 10.0}
    }

    # --------------------------------------------------------------------------
    # الشاشة الرئيسية: النماذج والمدخلات
    # --------------------------------------------------------------------------
    col_template, col_dims = st.columns([1, 2])

    with col_template:
        st.subheader("1. اختر نموذج الواجهة")
        template = st.radio(
            "نوع القاطع المعماري:",
            options=["A", "B", "C", "D"],
            format_func=lambda x: {
                "A": "نموذج (A): باب مفرد + فرامة + ثوابت",
                "B": "نموذج (B): باب مزدوج + فرامة + ثوابت",
                "C": "نموذج (C): قاطع متعدد الألواح مع باب",
                "D": "نموذج (D): قاطع ثابت بدون أبواب"
            }[x]
        )

    with col_dims:
        st.subheader("2. الأبعاد المعمارية للموقع (مم)")
        c1, c2 = st.columns(2)
        W_wall = c1.number_input("عرض الفتحة الكلي (W)", value=4000.0, step=50.0)
        H_wall = c2.number_input("ارتفاع الفتحة الكلي (H)", value=3000.0, step=50.0)

        if template != "D":
            c3, c4, c5 = st.columns(3)
            W_door = c3.number_input("عرض الباب الكلي (W_door)", value=1000.0 if template in ["A", "C"] else 1800.0, step=50.0)
            H_door = c4.number_input("ارتفاع الباب (H_door)", value=2200.0, step=50.0)
            X_door = c5.number_input("موقع الباب من اليسار (X_door)", value=1200.0, step=50.0)
        else:
            W_door, H_door, X_door = 0.0, 0.0, 0.0

    # --------------------------------------------------------------------------
    # الحسابات المباشرة والتوصيات
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📊 النتائج والتوصيات الفنية المباشرة")

    if template == "B":
        w_single_door = (W_door - (2 * g_side_nom) - g_mid_nom) / 2.0
    elif template in ["A", "C"]:
        w_single_door = W_door - (2 * g_side_nom)
    else:
        w_single_door = 0.0

    h_door_panel = H_door - g_bot_nom - g_top_nom if template != "D" else 0.0

    door_weight_raw = (w_single_door / 1000.0) * (h_door_panel / 1000.0) * glass_thick * 2.5
    door_weight_total = door_weight_raw * 1.10 if template != "D" else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("عرض دلفة الباب المقطوعة", f"{w_single_door:.1f} مم" if template != "D" else "N/A")
    m2.metric("ارتفاع دلفة الباب المقطوعة", f"{h_door_panel:.1f} مم" if template != "D" else "N/A")
    m3.metric("وزن الدلفة (مع أمان +10%)", f"{door_weight_total:.1f} كجم" if template != "D" else "N/A")

    if template == "D":
        m4.metric("قدرة الماكينة الأرضية", "لا يوجد باب")
    elif door_weight_total <= 75:
        m4.metric("قدرة الماكينة الأرضية", "Dorma BTS 75V / EN3", delta="سعة حتى 75 كجم")
    elif door_weight_total <= 105:
        m4.metric("قدرة الماكينة الأرضية", "Dorma BTS 80 / EN4", delta="سعة حتى 105 كجم")
    elif door_weight_total <= 150:
        m4.metric("قدرة الماكينة الأرضية", "Heavy Duty EN5", delta="سعة حتى 150 كجم")
    else:
        m4.metric("قدرة الماكينة الأرضية", "تجاوز الوزن!", delta="-خطر غير آمن", delta_color="inverse")
        st.error("⚠️ تحذير فني: وزن دلفة الباب يتجاوز 150 كجم! يجب تقليل أبعاد الباب أو استخدام سمك زجاج أقل أو نظام مفصلات حوائط شاقة بدلاً من الماكينات القياسية.")

    # --------------------------------------------------------------------------
    # توليد وتنزيل ملف الأوتوكاد DXF
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("💾 تصدير الرسم التنفيذي بصيغة أوتوكاد DXF")

    dxf_bytes = generate_glass_dxf(
        template=template,
        W_wall=W_wall,
        H_wall=H_wall,
        W_door=W_door,
        H_door=H_door,
        X_door=X_door,
        glass_thick=glass_thick,
        glass_type=glass_type,
        glass_color=glass_color,
        hardware_finish=hardware_finish,
        gaps=gaps_config
    )

    st.download_button(
        label="📥 تنزيل ملف الأوتوكاد التنفيذي (.dxf)",
        data=dxf_bytes,
        file_name=f"Glass_Shop_Drawing_{template}_t{glass_thick}mm.dxf",
        mime="application/dxf",
        type="primary"
    )

if __name__ == "__main__":
    main()