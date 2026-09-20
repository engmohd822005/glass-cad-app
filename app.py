import io
import streamlit as st
import ezdxf

# ==============================================================================
# 1. دالة تقسيم الألواح الثابتة (Sub-division Logic)
# ==============================================================================
def calculate_panel_subdivision(total_w: float, max_w: float, gap: float, x_start: float, y_start: float, height: float):
    """
    تقسيم المساحات الثابتة إلى ألواح متساوية لا تتجاوز أقصى عرض مسموح
    """
    if total_w <= 0:
        return [], 0, 0.0

    # حساب عدد الألواح المطلوبة
    num_panels = int(total_w // max_w) + (1 if total_w % max_w > 0 else 0)
    if num_panels == 0:
        num_panels = 1

    # عرض اللوح الواحد بعد خصم الفواصل بين الألواح المتجاورة
    w_panel = (total_w - ((num_panels - 1) * gap)) / num_panels

    panels = []
    curr_x = x_start
    for _ in range(num_panels):
        p_box = [
            (curr_x, y_start),
            (curr_x + w_panel, y_start),
            (curr_x + w_panel, y_start + height),
            (curr_x, y_start + height)
        ]
        panels.append(p_box)
        curr_x += w_panel + gap

    return panels, num_panels, w_panel


# ==============================================================================
# 2. دالة رسم جدول الحصر المضمونة (Line-Based BOM Table)
# ==============================================================================
def draw_bom_table(msp, start_x, start_y, data):
    col_widths = [550, 750, 1100]  # عرض الأعمدة الثلاثة (مم)
    row_height = 80               # ارتفاع السطر (مم)
    num_rows = len(data)
    total_width = sum(col_widths)
    total_height = num_rows * row_height

    # رسم الحدود الخارجية
    msp.add_polyline2d(
        [
            (start_x, start_y),
            (start_x + total_width, start_y),
            (start_x + total_width, start_y - total_height),
            (start_x, start_y - total_height)
        ],
        close=True,
        dxfattribs={"layer": "A-TABLE"}
    )

    # رسم الأسطر الأفقية
    for r in range(1, num_rows):
        y = start_y - (r * row_height)
        msp.add_line((start_x, y), (start_x + total_width, y), dxfattribs={"layer": "A-TABLE"})

    # رسم الفواصل الرأسية
    curr_x = start_x
    for w in col_widths[:-1]:
        curr_x += w
        msp.add_line((curr_x, start_y), (curr_x, start_y - total_height), dxfattribs={"layer": "A-TABLE"})

    # كتابة النصوص
    for r_idx, row in enumerate(data):
        cell_y = start_y - (r_idx * row_height) - (row_height / 2.0) - 10
        curr_x = start_x
        for c_idx, text in enumerate(row):
            cell_x = curr_x + 20
            text_height = 24 if r_idx == 0 else 18
            msp.add_text(
                str(text),
                dxfattribs={
                    "layer": "A-TABLE",
                    "height": text_height,
                    "insert": (cell_x, cell_y)
                }
            )
            curr_x += col_widths[c_idx]


# ==============================================================================
# 3. محرك الأوتوكاد والتفاصيل الإنشائية (CAD DXF Engine)
# ==============================================================================
def generate_glass_dxf(
    template: str,
    W_wall: float,
    H_wall: float,
    W_door: float,
    H_door: float,
    X_door: float,
    max_glass_width: float,
    chassis_type: str,
    anchor_type: str,
    glass_thick: int,
    glass_type: str,
    glass_color: str,
    hardware_finish: str,
    gaps: dict
) -> bytes:

    g_bot = gaps["G_bot"]["nom"]
    g_top = gaps["G_top"]["nom"]
    g_mid = gaps["G_mid"]["nom"]
    g_side = gaps["G_side"]["nom"]
    g_frame = gaps["G_frame"]["nom"]

    # حساب هندسة ودلف الأبواب
    if template == "B":
        w_single_door = (W_door - (2 * g_side) - g_mid) / 2.0
        num_doors = 2
    elif template in ["A", "C"]:
        w_single_door = W_door - (2 * g_side)
        num_doors = 1
    else:
        w_single_door = 0.0
        num_doors = 0

    h_door_panel = H_door - g_bot - g_top if num_doors > 0 else 0.0

    # حساب وزن الدلفة مع 10% أمان
    door_weight_raw = (w_single_door / 1000.0) * (h_door_panel / 1000.0) * glass_thick * 2.5
    door_weight_total = door_weight_raw * 1.10 if num_doors > 0 else 0.0

    # قدرة الماكينة
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

    doc.layers.add("A-WALL-OUTLINE", color=2)   # أصفر
    doc.layers.add("A-GLASS-FIXED", color=4)    # سماوي
    doc.layers.add("A-GLASS-DOOR", color=1)     # أحمر
    doc.layers.add("A-CHASSIS", color=6)        # بنفسجي (القطاعات والشاسية)
    doc.layers.add("A-HARDWARE", color=3)       # أخضر
    doc.layers.add("A-TABLE", color=7)          # أبيض

    # 1. رسم حدود الفتحة المعمارية
    msp.add_lwpolyline([(0, 0), (W_wall, 0), (W_wall, H_wall), (0, H_wall)], close=True, dxfattribs={"layer": "A-WALL-OUTLINE"})

    total_fixed_panels_count = 0
    total_chassis_length_mm = 0.0

    # 2. رسم ألواح الزجاج وتقسيمها
    if template in ["A", "B", "C"]:
        # اللوح الثابت الأيسر (وتقسيمه)
        w_left_total = X_door - g_frame - (g_side / 2.0)
        left_panels, n_left, w_left_single = calculate_panel_subdivision(
            w_left_total, max_glass_width, g_mid, g_frame, g_frame, H_wall - (2 * g_frame)
        )
        for p_box in left_panels:
            msp.add_lwpolyline(p_box, close=True, dxfattribs={"layer": "A-GLASS-FIXED"})
        total_fixed_panels_count += n_left

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
            total_fixed_panels_count += 1

        # دلف الأبواب
        if template == "B":
            x_d1 = X_door + g_side
            msp.add_lwpolyline([(x_d1, g_bot), (x_d1 + w_single_door, g_bot), (x_d1 + w_single_door, g_bot + h_door_panel), (x_d1, g_bot + h_door_panel)], close=True, dxfattribs={"layer": "A-GLASS-DOOR"})
            x_d2 = x_d1 + w_single_door + g_mid
            msp.add_lwpolyline([(x_d2, g_bot), (x_d2 + w_single_door, g_bot), (x_d2 + w_single_door, g_bot + h_door_panel), (x_d2, g_bot + h_door_panel)], close=True, dxfattribs={"layer": "A-GLASS-DOOR"})
            msp.add_lwpolyline([(x_d1, 0), (x_d1 + 120, 0), (x_d1 + 120, g_bot), (x_d1, g_bot)], close=True, dxfattribs={"layer": "A-HARDWARE"})
            msp.add_lwpolyline([(x_d2 + w_single_door - 120, 0), (x_d2 + w_single_door, 0), (x_d2 + w_single_door, g_bot), (x_d2 + w_single_door - 120, g_bot)], close=True, dxfattribs={"layer": "A-HARDWARE"})
        else:
            x_d = X_door + g_side
            msp.add_lwpolyline([(x_d, g_bot), (x_d + w_single_door, g_bot), (x_d + w_single_door, g_bot + h_door_panel), (x_d, g_bot + h_door_panel)], close=True, dxfattribs={"layer": "A-GLASS-DOOR"})
            msp.add_lwpolyline([(x_d, 0), (x_d + 120, 0), (x_d + 120, g_bot), (x_d, g_bot)], close=True, dxfattribs={"layer": "A-HARDWARE"})

        # اللوح الثابت الأيمن (وتقسيمه)
        x_right_start = X_door + W_door + (g_side / 2.0)
        w_right_total = W_wall - x_right_start - g_frame
        right_panels, n_right, w_right_single = calculate_panel_subdivision(
            w_right_total, max_glass_width, g_mid, x_right_start, g_frame, H_wall - (2 * g_frame)
        )
        for p_box in right_panels:
            msp.add_lwpolyline(p_box, close=True, dxfattribs={"layer": "A-GLASS-FIXED"})
        total_fixed_panels_count += n_right

        # حساب طول الشاسية المطلوب (المحيط العلوي والسفلي والجانبي للثوابت)
        total_chassis_length_mm = (w_left_total * 2) + (w_right_total * 2) + (W_door * 2 if h_transom > 0 else 0) + (H_wall * 2)

    elif template == "D":  # قاطع ثابت كامل
        full_panels, n_full, w_full_single = calculate_panel_subdivision(
            W_wall - (2 * g_frame), max_glass_width, g_mid, g_frame, g_frame, H_wall - (2 * g_frame)
        )
        for p_box in full_panels:
            msp.add_lwpolyline(p_box, close=True, dxfattribs={"layer": "A-GLASS-FIXED"})
        total_fixed_panels_count = n_full
        total_chassis_length_mm = (W_wall * 2) + (H_wall * 2)

    # 3. إعداد بيانات جدول الحصر والتركيب (BOM Table)
    bom_data = [
        ["ITEM / SPECIFICATION", "CALCULATED VALUE", "INSTALLATION & FIXING NOTES"],
        ["Partition Model", f"Template Model ({template})", f"Overall Size: {W_wall:.0f}x{H_wall:.0f} mm"],
        ["Glass Specs & Finish", f"{glass_thick}mm Tempered ({glass_type})", f"Glass Color: {glass_color}"],
        ["Door Leaf Cut Size", f"{w_single_door:.1f} x {h_door_panel:.1f} mm" if num_doors > 0 else "N/A", f"G_bot={g_bot}mm | G_top={g_top}mm"],
        ["Leaf Weight & Spring", f"{door_weight_total:.1f} kg / {spring_model}", f"Finish: {hardware_finish}"],
        ["Fixed Panels Sub-Division", f"Total Fixed Panels: {total_fixed_panels_count} Pcs", f"Max Width Limit: {max_glass_width:.0f} mm"],
        ["Mounting Chassis / Profile", chassis_type, f"Total Length Needed: {total_chassis_length_mm/1000.0:.2f} L.M."],
        ["Anchoring Fasteners", anchor_type, "Fixing Pitch: @ 400mm c/c Max"],
        ["Sealant & Setting Blocks", "Structural Silicone + EPDM Blocks", "EPDM Blocks (5mm) under base edges"],
        ["Quality & Safety Rules", "Flat Polish Edges All Around", "DO NOT CUT OR DRILL AFTER TEMPERING"]
    ]

    draw_bom_table(msp, start_x=W_wall + 500, start_y=H_wall, data=bom_data)

    # تصدير الملف
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


# ==============================================================================
# 4. واجهة المستخدم التفاعلية (Streamlit UI Application)
# ==============================================================================
def main():
    st.set_page_config(page_title="حاسبة ورسومات الزجاج السكويريت", layout="wide", page_icon="📐")

    st.title("📐 تطبيق تفصيل الزجاج السكويريت وتوليد رسومات الأوتوكاد")
    st.caption("نظام حساب تقسيم الألواح، الأوزان، شاسيهات التركيب، وتوليد ملفات DXF الإنشائية")

    # الشريط الجانبي
    st.sidebar.header("⚙️ مواصفات الزجاج والإكسسوارات")
    glass_thick = st.sidebar.selectbox("سمك الزجاج (مم)", [10, 12, 15, 19], index=1)
    glass_type = st.sidebar.selectbox("نوع الزجاج", ["شفاف (Clear)", "سوبر شفاف (Extra Clear)", "فاميه / مظلل (Tinted)", "مثلج (Frosted)"])
    glass_color = st.sidebar.selectbox("لون الزجاج", ["بدون / شفاف", "رمادي (Grey)", "برونزي (Bronze)", "أخضر (Dark Green)", "أزرق (Blue)"])
    hardware_finish = st.sidebar.selectbox("تشطيب الإكسسوارات", ["S.S Satin (ستانلس مط)", "Polished Chrome (كروم لامع)", "Matte Black (أسود مط)", "Brushed Gold (ذهبي)"])

    st.sidebar.markdown("---")
    st.sidebar.header("🛠️ شاسية التركيب وتقسيم الألواح")
    max_glass_width = st.sidebar.number_input("أقصى عرض مسموح للوح الثابت (مم)", value=1200.0, step=100.0)
    chassis_type = st.sidebar.selectbox("نوع شاسية / قطاع التثبيت", [
        "قطاع ألومنيوم ظاهري U-Channel (30x35mm)",
        "مجرى ستانلس ستيل غاطس بالبلاط (Recessed SS Channel)",
        "كبسات تثبيت نقطية (Glass Patch Clamps)",
        "نظام أذرع السبايدر (Spider Glass Fittings)"
    ])
    anchor_type = st.sidebar.selectbox("نوع براغي التثبيت الإنشائي", [
        "خوابير توسع M8 x 65mm (Expansion Anchor Bolts)",
        "براغي تثبيت خرسانة M8 (Concrete Screw Anchors)",
        "براغي تثبيت للحديد (Self-Tapping Screws for Steel Frame)"
    ])

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

    # الواجهة الرئيسية
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
        st.error("⚠️ تحذير فني: وزن دلفة الباب يتجاوز 150 كجم! يجب تقليل أبعاد الباب أو استخدام سمك زجاج أقل.")

    st.markdown("---")
    st.subheader("💾 تصدير الرسم التنفيذي بصيغة أوتوكاد DXF")

    dxf_bytes = generate_glass_dxf(
        template=template,
        W_wall=W_wall,
        H_wall=H_wall,
        W_door=W_door,
        H_door=H_door,
        X_door=X_door,
        max_glass_width=max_glass_width,
        chassis_type=chassis_type,
        anchor_type=anchor_type,
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
