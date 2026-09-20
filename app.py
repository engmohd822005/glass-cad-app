import io
import streamlit as st
import ezdxf

# ==============================================================================
# 1. أدوات الرسم الهندسي المتقدمة (CAD Helper Functions)
# ==============================================================================

def add_cad_dimension(msp, p1, p2, text, offset=150, is_horizontal=True, layer="A-DIMS"):
    """
    رسم خط بعد هندسي متكامل (Dimension Line + Extension Lines + Ticks + Text)
    """
    x1, y1 = p1
    x2, y2 = p2
    
    if is_horizontal:
        dim_y = y1 + offset if offset > 0 else y1 + offset
        # خطوط الامتداد الراسية
        msp.add_line((x1, y1 + (10 if offset>0 else -10)), (x1, dim_y + (20 if offset>0 else -20)), dxfattribs={"layer": layer})
        msp.add_line((x2, y2 + (10 if offset>0 else -10)), (x2, dim_y + (20 if offset>0 else -20)), dxfattribs={"layer": layer})
        # خط البعد الأفقي
        msp.add_line((x1, dim_y), (x2, dim_y), dxfattribs={"layer": layer})
        # الشخطات المائلة (Ticks 45 deg)
        msp.add_line((x1 - 15, dim_y - 15), (x1 + 15, dim_y + 15), dxfattribs={"layer": layer})
        msp.add_line((x2 - 15, dim_y - 15), (x2 + 15, dim_y + 15), dxfattribs={"layer": layer})
        # النص المركزي
        mid_x = (x1 + x2) / 2.0
        msp.add_text(str(text), dxfattribs={"layer": layer, "height": 30, "insert": (mid_x - 40, dim_y + 10)})
    else:
        dim_x = x1 + offset if offset > 0 else x1 + offset
        # خطوط الامتداد الأفقية
        msp.add_line((x1 + (10 if offset>0 else -10), y1), (dim_x + (20 if offset>0 else -20), y1), dxfattribs={"layer": layer})
        msp.add_line((x2 + (10 if offset>0 else -10), y2), (dim_x + (20 if offset>0 else -20), y2), dxfattribs={"layer": layer})
        # خط البعد الرأسي
        msp.add_line((dim_x, y1), (dim_x, y2), dxfattribs={"layer": layer})
        # الشخطات المائلة
        msp.add_line((dim_x - 15, y1 - 15), (dim_x + 15, y1 + 15), dxfattribs={"layer": layer})
        msp.add_line((dim_x - 15, y2 - 15), (dim_x + 15, y2 + 15), dxfattribs={"layer": layer})
        # النص المركزي
        mid_y = (y1 + y2) / 2.0
        msp.add_text(str(text), dxfattribs={"layer": layer, "height": 30, "insert": (dim_x + 10, mid_y - 15)})


def calculate_panel_subdivision(total_w: float, max_w: float, gap: float, x_start: float, y_start: float, height: float):
    if total_w <= 0:
        return [], 0, 0.0

    num_panels = int(total_w // max_w) + (1 if total_w % max_w > 0 else 0)
    if num_panels == 0:
        num_panels = 1

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


def draw_bilingual_bom_table(msp, start_x, start_y, data):
    col_widths = [600, 850, 1150]  # عرض الأعمدة (مم)
    row_height = 80                # ارتفاع السطر (مم)
    num_rows = len(data)
    total_width = sum(col_widths)
    total_height = num_rows * row_height

    # رسم الحدود الخارجية
    msp.add_polyline2d(
        [(start_x, start_y), (start_x + total_width, start_y), (start_x + total_width, start_y - total_height), (start_x, start_y - total_height)],
        close=True, dxfattribs={"layer": "A-TABLE"}
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

    # كتابة النصوص داخل الخلايا
    for r_idx, row in enumerate(data):
        cell_y = start_y - (r_idx * row_height) - (row_height / 2.0) - 8
        curr_x = start_x
        for c_idx, text in enumerate(row):
            cell_x = curr_x + 15
            text_height = 22 if r_idx == 0 else 16
            msp.add_text(str(text), dxfattribs={"layer": "A-TABLE", "height": text_height, "insert": (cell_x, cell_y)})
            curr_x += col_widths[c_idx]


def draw_sheet_title_block(msp, frame_min_x, frame_min_y, frame_max_x, frame_max_y, proj_title="TEMPERED GLASS SHOP DRAWING"):
    """
    رسم إطار اللوحة والخرطوشة المعتمدة (Title Block Frame)
    """
    # الإطار الخارجي المزدوج
    msp.add_polyline2d([(frame_min_x, frame_min_y), (frame_max_x, frame_min_y), (frame_max_x, frame_max_y), (frame_min_x, frame_max_y)], close=True, dxfattribs={"layer": "A-BORDER"})
    msp.add_polyline2d([(frame_min_x + 30, frame_min_y + 30), (frame_max_x - 30, frame_min_y + 30), (frame_max_x - 30, frame_max_y - 30), (frame_min_x + 30, frame_max_y - 30)], close=True, dxfattribs={"layer": "A-BORDER"})

    # الخرطوشة الزاوية في أسفل اليمين
    tb_w = 1200
    tb_h = 400
    tb_x = frame_max_x - 30 - tb_w
    tb_y = frame_min_y + 30

    msp.add_polyline2d([(tb_x, tb_y), (tb_x + tb_w, tb_y), (tb_x + tb_w, tb_y + tb_h), (tb_x, tb_y + tb_h)], close=True, dxfattribs={"layer": "A-BORDER"})
    
    # تقسيم الخرطوشة
    msp.add_line((tb_x, tb_y + 280), (tb_x + tb_w, tb_y + 280), dxfattribs={"layer": "A-BORDER"})
    msp.add_line((tb_x, tb_y + 180), (tb_x + tb_w, tb_y + 180), dxfattribs={"layer": "A-BORDER"})
    msp.add_line((tb_x, tb_y + 90), (tb_x + tb_w, tb_y + 90), dxfattribs={"layer": "A-BORDER"})
    msp.add_line((tb_x + 600, tb_y), (tb_x + 600, tb_y + 180), dxfattribs={"layer": "A-BORDER"})

    # كتابة بيانات الخرطوشة
    msp.add_text("PROJECT / المشروع: GLASS ELEVATION WORK", dxfattribs={"layer": "A-TEXT", "height": 22, "insert": (tb_x + 20, tb_y + 330)})
    msp.add_text(f"TITLE / اللوحة: {proj_title}", dxfattribs={"layer": "A-TEXT", "height": 24, "insert": (tb_x + 20, tb_y + 220)})
    msp.add_text("SCALE / المقياس: 1:20 / NTS", dxfattribs={"layer": "A-TEXT", "height": 20, "insert": (tb_x + 20, tb_y + 120)})
    msp.add_text("DRAWING NO: G-SD-001", dxfattribs={"layer": "A-TEXT", "height": 20, "insert": (tb_x + 620, tb_y + 120)})
    msp.add_text("DATE: 2026 / APPROVED SHOP DRAWING", dxfattribs={"layer": "A-TEXT", "height": 20, "insert": (tb_x + 20, tb_y + 30)})
    msp.add_text("REV: R0 (FINAL)", dxfattribs={"layer": "A-TEXT", "height": 20, "insert": (tb_x + 620, tb_y + 30)})


def draw_construction_details(msp, x_base, y_base, glass_thick, chassis_type, spring_model):
    """
    رسم التفاصيل الهندسية الثلاثة داخل إطارات مستقلة
    """
    # 1. تفصيلة ماكينة الباب الأرضية
    fs_x, fs_y = x_base, y_base
    msp.add_polyline2d([(fs_x - 50, fs_y - 120), (fs_x + 400, fs_y - 120), (fs_x + 400, fs_y + 280), (fs_x - 50, fs_y + 280)], close=True, dxfattribs={"layer": "A-DETAILS"})
    msp.add_text("DETAIL 1: FLOOR SPRING & BOTTOM PATCH", dxfattribs={"layer": "A-TEXT", "height": 24, "insert": (fs_x - 30, fs_y + 230)})
    
    msp.add_polyline2d([(fs_x, fs_y), (fs_x + 320, fs_y), (fs_x + 320, fs_y + 130), (fs_x, fs_y + 130)], close=True, dxfattribs={"layer": "A-DETAILS"})
    msp.add_polyline2d([(fs_x + 10, fs_y + 10), (fs_x + 310, fs_y + 10), (fs_x + 310, fs_y + 120), (fs_x + 10, fs_y + 120)], close=True, dxfattribs={"layer": "A-HARDWARE"})
    msp.add_circle((fs_x + 55, fs_y + 65), radius=18, dxfattribs={"layer": "A-HARDWARE"})
    msp.add_polyline2d([(fs_x + 55, fs_y + 39), (fs_x + 215, fs_y + 39), (fs_x + 215, fs_y + 91), (fs_x + 55, fs_y + 91)], close=True, dxfattribs={"layer": "A-HARDWARE"})
    msp.add_text(f"Cement Box: 320x130x60mm | {spring_model}", dxfattribs={"layer": "A-TEXT", "height": 16, "insert": (fs_x - 30, fs_y - 80)})

    # 2. قطاع رأسي لتثبيت الزجاج بالشاسية
    sec_x, sec_y = x_base + 550, y_base
    msp.add_polyline2d([(sec_x - 80, sec_y - 120), (sec_x + 400, sec_y - 120), (sec_x + 400, sec_y + 280), (sec_x - 80, sec_y + 280)], close=True, dxfattribs={"layer": "A-DETAILS"})
    msp.add_text("DETAIL 2: BASE U-CHANNEL SECTION A-A", dxfattribs={"layer": "A-TEXT", "height": 24, "insert": (sec_x - 60, sec_y + 230)})

    msp.add_polyline2d([(sec_x - 40, sec_y - 60), (sec_x + 100, sec_y - 60), (sec_x + 100, sec_y), (sec_x - 40, sec_y)], close=True, dxfattribs={"layer": "A-WALL-OUTLINE"})
    msp.add_polyline2d([(sec_x, sec_y), (sec_x + 60, sec_y), (sec_x + 60, sec_y + 70), (sec_x, sec_y + 70)], close=True, dxfattribs={"layer": "A-CHASSIS"})
    msp.add_polyline2d([(sec_x + 5, sec_y + 5), (sec_x + 55, sec_y + 5), (sec_x + 55, sec_y + 70), (sec_x + 5, sec_y + 70)], close=True, dxfattribs={"layer": "A-CHASSIS"})
    msp.add_polyline2d([(sec_x + 25, sec_y - 40), (sec_x + 35, sec_y - 40), (sec_x + 35, sec_y + 5), (sec_x + 25, sec_y + 5)], close=True, dxfattribs={"layer": "A-HARDWARE"})
    
    glass_x = sec_x + 30 - (glass_thick / 2.0)
    msp.add_polyline2d([(glass_x, sec_y + 10), (glass_x + glass_thick, sec_y + 10), (glass_x + glass_thick, sec_y + 180), (glass_x, sec_y + 180)], close=True, dxfattribs={"layer": "A-GLASS-FIXED"})
    msp.add_text(f"Profile: 30x35mm | Bolt: M8@400mm", dxfattribs={"layer": "A-TEXT", "height": 16, "insert": (sec_x - 60, sec_y - 80)})

    # 3. تفصيلة الكبسولة العلوية والثقوب
    pch_x, pch_y = x_base + 1100, y_base
    msp.add_polyline2d([(pch_x - 50, pch_y - 120), (pch_x + 400, pch_y - 120), (pch_x + 400, pch_y + 280), (pch_x - 50, pch_y + 280)], close=True, dxfattribs={"layer": "A-DETAILS"})
    msp.add_text("DETAIL 3: TOP PATCH & DRILLING", dxfattribs={"layer": "A-TEXT", "height": 24, "insert": (pch_x - 30, pch_y + 230)})

    msp.add_polyline2d([(pch_x, pch_y), (pch_x + 250, pch_y), (pch_x + 250, pch_y + 180), (pch_x, pch_y + 180)], close=True, dxfattribs={"layer": "A-GLASS-DOOR"})
    msp.add_polyline2d([(pch_x, pch_y + 128), (pch_x + 160, pch_y + 128), (pch_x + 160, pch_y + 180), (pch_x, pch_y + 180)], close=True, dxfattribs={"layer": "A-HARDWARE"})
    msp.add_circle((pch_x + 50, pch_y + 154), radius=glass_thick / 2.0 + 3, dxfattribs={"layer": "A-HARDWARE"})
    msp.add_circle((pch_x + 120, pch_y + 154), radius=glass_thick / 2.0 + 3, dxfattribs={"layer": "A-HARDWARE"})
    msp.add_text(f"Hole Dia (D >= {glass_thick}mm) | Edge >= {2*glass_thick}mm", dxfattribs={"layer": "A-TEXT", "height": 16, "insert": (pch_x - 30, pch_y - 80)})


# ==============================================================================
# 2. محرك الأوتوكاد ورسم الواجهة والأبعاد التلقائية (Main Engine)
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

    # حساب هندسة الأبواب
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

    door_weight_raw = (w_single_door / 1000.0) * (h_door_panel / 1000.0) * glass_thick * 2.5
    door_weight_total = door_weight_raw * 1.10 if num_doors > 0 else 0.0

    if num_doors == 0:
        spring_model = "N/A (Fixed Partition / بدون باب)"
    elif door_weight_total <= 75:
        spring_model = "Floor Spring EN3 (Cap <= 75 kg)"
    elif door_weight_total <= 105:
        spring_model = "Floor Spring EN4 (Cap <= 105 kg)"
    elif door_weight_total <= 150:
        spring_model = "Floor Spring EN5 Heavy Duty (Cap <= 150 kg)"
    else:
        spring_model = "CRITICAL: Custom Heavy Pivot (>150 kg)"

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # تأسيس الطبقات والألوان
    doc.layers.add("A-WALL-OUTLINE", color=2)   # أصفر
    doc.layers.add("A-GLASS-FIXED", color=4)    # سماوي
    doc.layers.add("A-GLASS-DOOR", color=1)     # أحمر
    doc.layers.add("A-CHASSIS", color=6)        # بنفسجي
    doc.layers.add("A-HARDWARE", color=3)       # أخضر
    doc.layers.add("A-DIMS", color=2)           # أصفر للأبعاد
    doc.layers.add("A-DETAILS", color=5)        # أزرق داكن
    doc.layers.add("A-TEXT", color=7)           # أبيض للنصوص
    doc.layers.add("A-BORDER", color=7)         # أبيض للخرطوشة
    doc.layers.add("A-TABLE", color=7)          # أبيض للجدول

    # 1. رسم حدود الفتحة المعمارية الرئيسية
    msp.add_lwpolyline([(0, 0), (W_wall, 0), (W_wall, H_wall), (0, H_wall)], close=True, dxfattribs={"layer": "A-WALL-OUTLINE"})

    total_fixed_panels_count = 0
    total_chassis_length_mm = 0.0

    # 2. رسم الألواح وتقسيمها
    if template in ["A", "B", "C"]:
        # اللوح الثابت الأيسر
        w_left_total = X_door - g_frame - (g_side / 2.0)
        left_panels, n_left, w_left_single = calculate_panel_subdivision(w_left_total, max_glass_width, g_mid, g_frame, g_frame, H_wall - (2 * g_frame))
        for p_box in left_panels:
            msp.add_lwpolyline(p_box, close=True, dxfattribs={"layer": "A-GLASS-FIXED"})
            # أبعاد الألواح الفرعية
            p_x1 = p_box[0][0]
            p_x2 = p_box[1][0]
            add_cad_dimension(msp, (p_x1, 0), (p_x2, 0), f"{w_left_single:.0f}", offset=-180, is_horizontal=True)
        total_fixed_panels_count += n_left

        # الفرامة العلوية فوق الباب
        h_transom = H_wall - H_door - g_frame
        if h_transom > 0:
            msp.add_lwpolyline([(X_door, H_door + (g_top / 2.0)), (X_door + W_door, H_door + (g_top / 2.0)), (X_door + W_door, H_wall - g_frame), (X_door, H_wall - g_frame)], close=True, dxfattribs={"layer": "A-GLASS-FIXED"})
            total_fixed_panels_count += 1
            # بعد ارتفاع الفرامة
            add_cad_dimension(msp, (X_door + W_door, H_door), (X_door + W_door, H_wall), f"H_tr={h_transom:.0f}", offset=150, is_horizontal=False)

        # دلف الأبواب والأبعاد
        if template == "B":
            x_d1 = X_door + g_side
            msp.add_lwpolyline([(x_d1, g_bot), (x_d1 + w_single_door, g_bot), (x_d1 + w_single_door, g_bot + h_door_panel), (x_d1, g_bot + h_door_panel)], close=True, dxfattribs={"layer": "A-GLASS-DOOR"})
            x_d2 = x_d1 + w_single_door + g_mid
            msp.add_lwpolyline([(x_d2, g_bot), (x_d2 + w_single_door, g_bot), (x_d2 + w_single_door, g_bot + h_door_panel), (x_d2, g_bot + h_door_panel)], close=True, dxfattribs={"layer": "A-GLASS-DOOR"})
            
            add_cad_dimension(msp, (x_d1, 0), (x_d1 + w_single_door, 0), f"D1={w_single_door:.0f}", offset=-180, is_horizontal=True)
            add_cad_dimension(msp, (x_d2, 0), (x_d2 + w_single_door, 0), f"D2={w_single_door:.0f}", offset=-180, is_horizontal=True)
            
            # تمثيل الماكينة وتصليح الدائرة
            msp.add_circle((x_d1 + 55, g_bot / 2.0), radius=25, dxfattribs={"layer": "A-HARDWARE"})
            msp.add_circle((x_d2 + w_single_door - 55, g_bot / 2.0), radius=25, dxfattribs={"layer": "A-HARDWARE"})
        else:
            x_d = X_door + g_side
            msp.add_lwpolyline([(x_d, g_bot), (x_d + w_single_door, g_bot), (x_d + w_single_door, g_bot + h_door_panel), (x_d, g_bot + h_door_panel)], close=True, dxfattribs={"layer": "A-GLASS-DOOR"})
            add_cad_dimension(msp, (x_d, 0), (x_d + w_single_door, 0), f"Door={w_single_door:.0f}", offset=-180, is_horizontal=True)
            msp.add_circle((x_d + 55, g_bot / 2.0), radius=25, dxfattribs={"layer": "A-HARDWARE"})

        # بعد ارتفاع الباب
        add_cad_dimension(msp, (X_door, 0), (X_door, H_door), f"H_door={h_door_panel:.0f}", offset=-150, is_horizontal=False)

        # اللوح الثابت الأيمن
        x_right_start = X_door + W_door + (g_side / 2.0)
        w_right_total = W_wall - x_right_start - g_frame
        right_panels, n_right, w_right_single = calculate_panel_subdivision(w_right_total, max_glass_width, g_mid, x_right_start, g_frame, H_wall - (2 * g_frame))
        for p_box in right_panels:
            msp.add_lwpolyline(p_box, close=True, dxfattribs={"layer": "A-GLASS-FIXED"})
            p_x1 = p_box[0][0]
            p_x2 = p_box[1][0]
            add_cad_dimension(msp, (p_x1, 0), (p_x2, 0), f"{w_right_single:.0f}", offset=-180, is_horizontal=True)
        total_fixed_panels_count += n_right

        total_chassis_length_mm = (w_left_total * 2) + (w_right_total * 2) + (W_door * 2 if h_transom > 0 else 0) + (H_wall * 2)

    elif template == "D":
        full_panels, n_full, w_full_single = calculate_panel_subdivision(W_wall - (2 * g_frame), max_glass_width, g_mid, g_frame, g_frame, H_wall - (2 * g_frame))
        for p_box in full_panels:
            msp.add_lwpolyline(p_box, close=True, dxfattribs={"layer": "A-GLASS-FIXED"})
            p_x1 = p_box[0][0]
            p_x2 = p_box[1][0]
            add_cad_dimension(msp, (p_x1, 0), (p_x2, 0), f"{w_full_single:.0f}", offset=-180, is_horizontal=True)
        total_fixed_panels_count = n_full
        total_chassis_length_mm = (W_wall * 2) + (H_wall * 2)

    # الأبعاد الإجمالية الرئيسية للفتحة
    add_cad_dimension(msp, (0, H_wall), (W_wall, H_wall), f"TOTAL WIDTH W = {W_wall:.0f} mm", offset=300, is_horizontal=True)
    add_cad_dimension(msp, (0, 0), (0, H_wall), f"TOTAL HEIGHT H = {H_wall:.0f} mm", offset=-300, is_horizontal=False)

    # دوائر وأسهم التأشير لربط التفاصيل بالواجهة (Detail Callout Circles)
    if template != "D":
        # مؤشر الماكينة DET-01
        msp.add_circle((X_door + 55, 0), radius=60, dxfattribs={"layer": "A-DETAILS"})
        msp.add_text("DET-01", dxfattribs={"layer": "A-DETAILS", "height": 20, "insert": (X_door + 30, -90)})
        # مؤشر الكبسولة العلوية DET-03
        msp.add_circle((X_door + 55, H_door), radius=60, dxfattribs={"layer": "A-DETAILS"})
        msp.add_text("DET-03", dxfattribs={"layer": "A-DETAILS", "height": 20, "insert": (X_door + 30, H_door + 80)})

    # مؤشر الشاسية DET-02
    msp.add_circle((0, H_wall / 2.0), radius=60, dxfattribs={"layer": "A-DETAILS"})
    msp.add_text("DET-02", dxfattribs={"layer": "A-DETAILS", "height": 20, "insert": (-120, H_wall / 2.0)})

    # 3. إعداد جدول الحصر ورسمه
    bom_data = [
        ["ITEM / العنصر", "CALCULATED VALUE / القيمة", "FIXING & INSTALLATION NOTES / ملاحظات التثبيت"],
        ["Partition Model / النموذج", f"Template Model ({template})", f"Overall Opening: {W_wall:.0f}x{H_wall:.0f} mm"],
        ["Glass Specs / المواصفات", f"{glass_thick}mm Tempered ({glass_type})", f"Glass Color: {glass_color}"],
        ["Door Leaf Size / المقاس", f"{w_single_door:.1f} x {h_door_panel:.1f} mm" if num_doors > 0 else "N/A", f"Clearances: G_bot={g_bot}mm | G_top={g_top}mm"],
        ["Leaf Weight & Spring / الوزن", f"{door_weight_total:.1f} kg / {spring_model}", f"Hardware Finish: {hardware_finish}"],
        ["Fixed Panels / الثوابت", f"Total Fixed Panels: {total_fixed_panels_count} Pcs", f"Max Width Limit: {max_glass_width:.0f} mm"],
        ["Profile Chassis / الشاسية", chassis_type, f"Total Profile Needed: {total_chassis_length_mm/1000.0:.2f} L.M."],
        ["Fasteners / البراغي", anchor_type, "Anchor Pitch: @ 400mm c/c Max"],
        ["Sealants / مواد العزل", "Structural Silicone + EPDM Blocks", "EPDM Setting Blocks (5mm) under base edges"],
        ["Quality Rules / شروط الجودة", "Flat Polish All Edges & Drill First", "DO NOT CUT OR DRILL AFTER TEMPERING"]
    ]

    draw_bilingual_bom_table(msp, start_x=W_wall + 500, start_y=H_wall, data=bom_data)

    # 4. رسم التفاصيل الهندسية المكبرة
    draw_construction_details(msp, x_base=0, y_base=-750, glass_thick=glass_thick, chassis_type=chassis_type, spring_model=spring_model)

    # 5. رسم إطار اللوحة والخرطوشة المتكاملة (A1/A3 Title Block)
    draw_sheet_title_block(
        msp,
        frame_min_x=-550,
        frame_min_y=-1100,
        frame_max_x=W_wall + 3200,
        frame_max_y=H_wall + 600,
        proj_title=f"TEMPERED GLASS PARTITION - MODEL {template}"
    )

    # تصدير الملف
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


# ==============================================================================
# 3. واجهة المستخدم التفاعلية (Streamlit UI Application)
# ==============================================================================
def main():
    st.set_page_config(page_title="حاسبة ورسومات الزجاج السكويريت الشاملة", layout="wide", page_icon="📐")

    st.title("📐 التطبيق الشامل لتفصيل الزجاج السكويريت والرسومات التنفيذية")
    st.caption("برنامج حساب الخلوصات، الأوزان، قدرة الماكينات، الشاسيهات، وتوليد ملفات DXF المعمارية")

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
        label="📥 تنزيل ملف الأوتوكاد التنفيذي الشامل (.dxf)",
        data=dxf_bytes,
        file_name=f"Comprehensive_Glass_Drawing_{template}_t{glass_thick}mm.dxf",
        mime="application/dxf",
        type="primary"
    )

if __name__ == "__main__":
    main()
