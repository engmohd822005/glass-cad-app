import io
import streamlit as st
import ezdxf

# ==============================================================================
# 1. أدوات الرسم الهندسي والأبعاد (CAD Engine Helpers)
# ==============================================================================

def add_clean_dimension(msp, p1, p2, text, offset=200, is_horizontal=True, layer="A-DIMS"):
    """
    رسم خط بعد هندسي نقي ودقيق بدون تداخل النصوص
    """
    x1, y1 = p1
    x2, y2 = p2
    
    if is_horizontal:
        dim_y = y1 + offset
        ext_dir = 15 if offset > 0 else -15
        
        # خطوط الامتداد
        msp.add_line((x1, y1 + ext_dir), (x1, dim_y + ext_dir), dxfattribs={"layer": layer})
        msp.add_line((x2, y2 + ext_dir), (x2, dim_y + ext_dir), dxfattribs={"layer": layer})
        # خط البعد
        msp.add_line((x1, dim_y), (x2, dim_y), dxfattribs={"layer": layer})
        # التحديد المائل (Ticks)
        msp.add_line((x1 - 12, dim_y - 12), (x1 + 12, dim_y + 12), dxfattribs={"layer": layer})
        msp.add_line((x2 - 12, dim_y - 12), (x2 + 12, dim_y + 12), dxfattribs={"layer": layer})
        # كتابة النص الممركز
        mid_x = (x1 + x2) / 2.0
        msp.add_mtext(
            text,
            dxfattribs={
                "layer": layer,
                "char_height": 28,
                "insert": (mid_x, dim_y + (12 if offset > 0 else -35)),
                "attachment_point": 5
            }
        )
    else:
        dim_x = x1 + offset
        ext_dir = 15 if offset > 0 else -15
        
        # خطوط الامتداد
        msp.add_line((x1 + ext_dir, y1), (dim_x + ext_dir, y1), dxfattribs={"layer": layer})
        msp.add_line((x2 + ext_dir, y2), (dim_x + ext_dir, y2), dxfattribs={"layer": layer})
        # خط البعد
        msp.add_line((dim_x, y1), (dim_x, y2), dxfattribs={"layer": layer})
        # التحديد المائل
        msp.add_line((dim_x - 12, y1 - 12), (dim_x + 12, y1 + 12), dxfattribs={"layer": layer})
        msp.add_line((dim_x - 12, y2 - 12), (dim_x + 12, y2 + 12), dxfattribs={"layer": layer})
        # النص الممركز
        mid_y = (y1 + y2) / 2.0
        msp.add_mtext(
            text,
            dxfattribs={
                "layer": layer,
                "char_height": 28,
                "insert": (dim_x + (35 if offset > 0 else -35), mid_y),
                "attachment_point": 5
            }
        )


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


def draw_hardware_bom_table(msp, start_x, start_y, data):
    """
    رسم جدول حصر الإكسسوارات والمواصفات التنفيذية
    """
    col_widths = [700, 1000, 1500]
    row_height = 90
    num_rows = len(data)
    total_width = sum(col_widths)
    total_height = num_rows * row_height

    # الإطار الخارجي للجدول
    msp.add_polyline2d(
        [(start_x, start_y), (start_x + total_width, start_y), (start_x + total_width, start_y - total_height), (start_x, start_y - total_height)],
        close=True, dxfattribs={"layer": "A-TABLE"}
    )

    # الصفوف الأفقية
    for r in range(1, num_rows):
        y = start_y - (r * row_height)
        msp.add_line((start_x, y), (start_x + total_width, y), dxfattribs={"layer": "A-TABLE"})

    # الأعمدة الرأسية
    curr_x = start_x
    for w in col_widths[:-1]:
        curr_x += w
        msp.add_line((curr_x, start_y), (curr_x, start_y - total_height), dxfattribs={"layer": "A-TABLE"})

    # كتابة النصوص داخل الخلايا
    for r_idx, row in enumerate(data):
        cell_y = start_y - (r_idx * row_height) - (row_height / 2.0)
        curr_x = start_x
        for c_idx, text in enumerate(row):
            cell_x = curr_x + 20
            h = 24 if r_idx == 0 else 18
            msp.add_mtext(
                text,
                dxfattribs={
                    "layer": "A-TABLE",
                    "char_height": h,
                    "insert": (cell_x, cell_y),
                    "attachment_point": 4
                }
            )
            curr_x += col_widths[c_idx]


def draw_sheet_frame(msp, min_x, min_y, max_x, max_y, title_text):
    """
    رسم إطار اللوحة المعماري والخرطوشة (Title Block)
    """
    msp.add_polyline2d([(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)], close=True, dxfattribs={"layer": "A-BORDER"})
    msp.add_polyline2d([(min_x + 40, min_y + 40), (max_x - 40, min_y + 40), (max_x - 40, max_y - 40), (min_x + 40, max_y - 40)], close=True, dxfattribs={"layer": "A-BORDER"})

    tb_w, tb_h = 1300, 450
    tb_x = max_x - 40 - tb_w
    tb_y = min_y + 40

    msp.add_polyline2d([(tb_x, tb_y), (tb_x + tb_w, tb_y), (tb_x + tb_w, tb_y + tb_h), (tb_x, tb_y + tb_h)], close=True, dxfattribs={"layer": "A-BORDER"})
    
    msp.add_line((tb_x, tb_y + 320), (tb_x + tb_w, tb_y + 320), dxfattribs={"layer": "A-BORDER"})
    msp.add_line((tb_x, tb_y + 200), (tb_x + tb_w, tb_y + 200), dxfattribs={"layer": "A-BORDER"})
    msp.add_line((tb_x, tb_y + 100), (tb_x + tb_w, tb_y + 100), dxfattribs={"layer": "A-BORDER"})
    msp.add_line((tb_x + 650, tb_y), (tb_x + 650, tb_y + 200), dxfattribs={"layer": "A-BORDER"})

    msp.add_mtext("APPROVED SHOP DRAWING / مخطط ورشة معتمد", dxfattribs={"layer": "A-TEXT", "char_height": 26, "insert": (tb_x + 30, tb_y + 380)})
    msp.add_mtext(f"PROJECT: {title_text}", dxfattribs={"layer": "A-TEXT", "char_height": 24, "insert": (tb_x + 30, tb_y + 260)})
    msp.add_mtext("SCALE: 1:20 @ A1 / NTS", dxfattribs={"layer": "A-TEXT", "char_height": 20, "insert": (tb_x + 30, tb_y + 150)})
    msp.add_mtext("DWG NO: G-SD-101", dxfattribs={"layer": "A-TEXT", "char_height": 20, "insert": (tb_x + 680, tb_y + 150)})
    msp.add_mtext("DATE: 2026-09", dxfattribs={"layer": "A-TEXT", "char_height": 20, "insert": (tb_x + 30, tb_y + 50)})
    msp.add_mtext("REVISION: R1 (EXECUTION)", dxfattribs={"layer": "A-TEXT", "char_height": 20, "insert": (tb_x + 680, tb_y + 50)})


def draw_execution_details(msp, x_base, y_base, glass_thick, chassis_type, anchor_type, spring_model, lock_type):
    """
    رسم المقاطع والتفاصيل الإنشائية المكبرة الموضحة لوسائل التثبيت
    """
    # 1. تفصيلة ماكينة الباب الأرضية
    fs_x, fs_y = x_base, y_base
    msp.add_polyline2d([(fs_x - 50, fs_y - 150), (fs_x + 450, fs_y - 150), (fs_x + 450, fs_y + 300), (fs_x - 50, fs_y + 300)], close=True, dxfattribs={"layer": "A-DETAILS"})
    msp.add_mtext("DETAIL 1: FLOOR SPRING & CEMENT BOX", dxfattribs={"layer": "A-TEXT", "char_height": 24, "insert": (fs_x - 20, fs_y + 250)})
    
    # صندوق الماكينة
    msp.add_polyline2d([(fs_x, fs_y), (fs_x + 340, fs_y), (fs_x + 340, fs_y + 140), (fs_x, fs_y + 140)], close=True, dxfattribs={"layer": "A-DETAILS"})
    msp.add_polyline2d([(fs_x + 10, fs_y + 10), (fs_x + 330, fs_y + 10), (fs_x + 330, fs_y + 130), (fs_x + 10, fs_y + 130)], close=True, dxfattribs={"layer": "A-HARDWARE"})
    msp.add_circle((fs_x + 60, fs_y + 70), radius=20, dxfattribs={"layer": "A-HARDWARE"})
    msp.add_mtext(f"Box: 340x140x65mm\nModel: {spring_model}\nLock: {lock_type}", dxfattribs={"layer": "A-TEXT", "char_height": 18, "insert": (fs_x - 20, fs_y - 100)})

    # 2. قطاع A-A لتثبيت الشاسية وتفصيلة البرغي
    sec_x, sec_y = x_base + 600, y_base
    msp.add_polyline2d([(sec_x - 100, sec_y - 150), (sec_x + 450, sec_y - 150), (sec_x + 450, sec_y + 300), (sec_x - 100, sec_y + 300)], close=True, dxfattribs={"layer": "A-DETAILS"})
    msp.add_mtext("SECTION A-A: FIXING & ANCHOR DETAIL", dxfattribs={"layer": "A-TEXT", "char_height": 24, "insert": (sec_x - 80, sec_y + 250)})

    # الخرسانة/الجدار
    msp.add_polyline2d([(sec_x - 50, sec_y - 80), (sec_x + 120, sec_y - 80), (sec_x + 120, sec_y), (sec_x - 50, sec_y)], close=True, dxfattribs={"layer": "A-WALL-OUTLINE"})
    # قطاع الشاسية
    msp.add_polyline2d([(sec_x, sec_y), (sec_x + 70, sec_y), (sec_x + 70, sec_y + 80), (sec_x, sec_y + 80)], close=True, dxfattribs={"layer": "A-CHASSIS"})
    msp.add_polyline2d([(sec_x + 6, sec_y + 6), (sec_x + 64, sec_y + 6), (sec_x + 64, sec_y + 80), (sec_x + 6, sec_y + 80)], close=True, dxfattribs={"layer": "A-CHASSIS"})
    
    # برغي التثبيت الإنشائي (Anchor Bolt)
    msp.add_polyline2d([(sec_x + 30, sec_y - 60), (sec_x + 40, sec_y - 60), (sec_x + 40, sec_y + 10), (sec_x + 30, sec_y + 10)], close=True, dxfattribs={"layer": "A-HARDWARE"})
    msp.add_circle((sec_x + 35, sec_y + 10), radius=10, dxfattribs={"layer": "A-HARDWARE"})

    # اللوح الزجاجي والسيليكون
    glass_x = sec_x + 35 - (glass_thick / 2.0)
    msp.add_polyline2d([(glass_x, sec_y + 15), (glass_x + glass_thick, sec_y + 15), (glass_x + glass_thick, sec_y + 200), (glass_x, sec_y + 200)], close=True, dxfattribs={"layer": "A-GLASS-FIXED"})
    msp.add_mtext(f"Fastener: {anchor_type}\nSetting Block: EPDM 5mm\nSealant: Structural Silicone", dxfattribs={"layer": "A-TEXT", "char_height": 18, "insert": (sec_x - 80, sec_y - 100)})

    # 3. تفصيلة الكبسولة العلوية والثقوب
    pch_x, pch_y = x_base + 1200, y_base
    msp.add_polyline2d([(pch_x - 50, pch_y - 150), (pch_x + 450, pch_y - 150), (pch_x + 450, pch_y + 300), (pch_x - 50, pch_y + 300)], close=True, dxfattribs={"layer": "A-DETAILS"})
    msp.add_mtext("DETAIL 3: TOP PATCH & GLASS CUTOUT", dxfattribs={"layer": "A-TEXT", "char_height": 24, "insert": (pch_x - 30, pch_y + 250)})

    msp.add_polyline2d([(pch_x, pch_y), (pch_x + 280, pch_y), (pch_x + 280, pch_y + 200), (pch_x, pch_y + 200)], close=True, dxfattribs={"layer": "A-GLASS-DOOR"})
    msp.add_polyline2d([(pch_x, pch_y + 135), (pch_x + 170, pch_y + 135), (pch_x + 170, pch_y + 200), (pch_x, pch_y + 200)], close=True, dxfattribs={"layer": "A-HARDWARE"})
    msp.add_circle((pch_x + 55, pch_y + 165), radius=14, dxfattribs={"layer": "A-HARDWARE"})
    msp.add_circle((pch_x + 130, pch_y + 165), radius=14, dxfattribs={"layer": "A-HARDWARE"})
    msp.add_mtext(f"Hole Dia: {glass_thick + 4}mm\nMin Edge Dist: {2.5 * glass_thick:.0f}mm\nPatch: Standard Top Fitting", dxfattribs={"layer": "A-TEXT", "char_height": 18, "insert": (pch_x - 30, pch_y - 100)})


# ==============================================================================
# 2. المحرك الرئيسي لتوليد ملفات DXF المعمارية
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
    spring_model: str,
    lock_type: str,
    handle_type: str,
    silicone_type: str,
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
    door_weight_total = ((w_single_door / 1000.0) * (h_door_panel / 1000.0) * glass_thick * 2.5) * 1.10 if num_doors > 0 else 0.0

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # الطبقات
    doc.layers.add("A-WALL-OUTLINE", color=2)
    doc.layers.add("A-GLASS-FIXED", color=4)
    doc.layers.add("A-GLASS-DOOR", color=1)
    doc.layers.add("A-CHASSIS", color=6)
    doc.layers.add("A-HARDWARE", color=3)
    doc.layers.add("A-DIMS", color=2)
    doc.layers.add("A-DETAILS", color=5)
    doc.layers.add("A-TEXT", color=7)
    doc.layers.add("A-BORDER", color=7)
    doc.layers.add("A-TABLE", color=7)

    # 1. إطار الفتحة
    msp.add_lwpolyline([(0, 0), (W_wall, 0), (W_wall, H_wall), (0, H_wall)], close=True, dxfattribs={"layer": "A-WALL-OUTLINE"})

    total_fixed_panels_count = 0
    total_chassis_length_mm = 0.0

    # 2. رسم الواجهة
    if template in ["A", "B", "C"]:
        w_left_total = X_door - g_frame - (g_side / 2.0)
        left_panels, n_left, w_left_single = calculate_panel_subdivision(w_left_total, max_glass_width, g_mid, g_frame, g_frame, H_wall - (2 * g_frame))
        for p_box in left_panels:
            msp.add_lwpolyline(p_box, close=True, dxfattribs={"layer": "A-GLASS-FIXED"})
            add_clean_dimension(msp, (p_box[0][0], 0), (p_box[1][0], 0), f"{w_left_single:.0f} mm", offset=-250)
        total_fixed_panels_count += n_left

        h_transom = H_wall - H_door - g_frame
        if h_transom > 0:
            msp.add_lwpolyline([(X_door, H_door + (g_top / 2.0)), (X_door + W_door, H_door + (g_top / 2.0)), (X_door + W_door, H_wall - g_frame), (X_door, H_wall - g_frame)], close=True, dxfattribs={"layer": "A-GLASS-FIXED"})
            total_fixed_panels_count += 1
            add_clean_dimension(msp, (X_door + W_door, H_door), (X_door + W_door, H_wall), f"H_tr={h_transom:.0f}", offset=200, is_horizontal=False)

        if template == "B":
            x_d1 = X_door + g_side
            msp.add_lwpolyline([(x_d1, g_bot), (x_d1 + w_single_door, g_bot), (x_d1 + w_single_door, g_bot + h_door_panel), (x_d1, g_bot + h_door_panel)], close=True, dxfattribs={"layer": "A-GLASS-DOOR"})
            x_d2 = x_d1 + w_single_door + g_mid
            msp.add_lwpolyline([(x_d2, g_bot), (x_d2 + w_single_door, g_bot), (x_d2 + w_single_door, g_bot + h_door_panel), (x_d2, g_bot + h_door_panel)], close=True, dxfattribs={"layer": "A-GLASS-DOOR"})
            
            add_clean_dimension(msp, (x_d1, 0), (x_d1 + w_single_door, 0), f"Door 1={w_single_door:.0f}", offset=-250)
            add_clean_dimension(msp, (x_d2, 0), (x_d2 + w_single_door, 0), f"Door 2={w_single_door:.0f}", offset=-250)
            
            msp.add_circle((x_d1 + 60, g_bot / 2.0), radius=30, dxfattribs={"layer": "A-HARDWARE"})
            msp.add_circle((x_d2 + w_single_door - 60, g_bot / 2.0), radius=30, dxfattribs={"layer": "A-HARDWARE"})
        else:
            x_d = X_door + g_side
            msp.add_lwpolyline([(x_d, g_bot), (x_d + w_single_door, g_bot), (x_d + w_single_door, g_bot + h_door_panel), (x_d, g_bot + h_door_panel)], close=True, dxfattribs={"layer": "A-GLASS-DOOR"})
            add_clean_dimension(msp, (x_d, 0), (x_d + w_single_door, 0), f"Door={w_single_door:.0f}", offset=-250)
            msp.add_circle((x_d + 60, g_bot / 2.0), radius=30, dxfattribs={"layer": "A-HARDWARE"})

        add_clean_dimension(msp, (X_door, 0), (X_door, H_door), f"H_door={h_door_panel:.0f}", offset=-200, is_horizontal=False)

        x_right_start = X_door + W_door + (g_side / 2.0)
        w_right_total = W_wall - x_right_start - g_frame
        right_panels, n_right, w_right_single = calculate_panel_subdivision(w_right_total, max_glass_width, g_mid, x_right_start, g_frame, H_wall - (2 * g_frame))
        for p_box in right_panels:
            msp.add_lwpolyline(p_box, close=True, dxfattribs={"layer": "A-GLASS-FIXED"})
            add_clean_dimension(msp, (p_box[0][0], 0), (p_box[1][0], 0), f"{w_right_single:.0f} mm", offset=-250)
        total_fixed_panels_count += n_right

        total_chassis_length_mm = (w_left_total * 2) + (w_right_total * 2) + (W_door * 2 if h_transom > 0 else 0) + (H_wall * 2)

    elif template == "D":
        full_panels, n_full, w_full_single = calculate_panel_subdivision(W_wall - (2 * g_frame), max_glass_width, g_mid, g_frame, g_frame, H_wall - (2 * g_frame))
        for p_box in full_panels:
            msp.add_lwpolyline(p_box, close=True, dxfattribs={"layer": "A-GLASS-FIXED"})
            add_clean_dimension(msp, (p_box[0][0], 0), (p_box[1][0], 0), f"{w_full_single:.0f} mm", offset=-250)
        total_fixed_panels_count = n_full
        total_chassis_length_mm = (W_wall * 2) + (H_wall * 2)

    # الأبعاد الإجمالية
    add_clean_dimension(msp, (0, H_wall), (W_wall, H_wall), f"OVERALL WIDTH W = {W_wall:.0f} mm", offset=400)
    add_clean_dimension(msp, (0, 0), (0, H_wall), f"OVERALL HEIGHT H = {H_wall:.0f} mm", offset=-400, is_horizontal=False)

    # 3. جدول الحصر والتثبيت المعتمد
    bom_data = [
        ["ITEM / SPECIFICATION", "SELECTED VALUE / MODEL", "INSTALLATION & FIXING SPECS"],
        ["Partition Layout", f"Template ({template})", f"Overall Opening: {W_wall:.0f} x {H_wall:.0f} mm"],
        ["Glass Specification", f"{glass_thick}mm Tempered Glass", f"Type: {glass_type} | Color: {glass_color}"],
        ["Door Leaf Cut Size", f"{w_single_door:.1f} x {h_door_panel:.1f} mm" if num_doors > 0 else "N/A", f"Gaps: Bottom={g_bot}mm, Top={g_top}mm, Side={g_side}mm"],
        ["Door Leaf Weight", f"{door_weight_total:.1f} kg / Leaf", f"Hardware Finish: {hardware_finish}"],
        ["Floor Spring Machine", spring_model, "Box Cemented Level with Finished Floor"],
        ["Lock & Handles", f"{lock_type} / {handle_type}", "Pre-drilled Holes in Glass Before Tempering"],
        ["Fixing Anchors / Bolts", anchor_type, "Pitch: @ 400mm c/c Max Along Base Profile"],
        ["Chassis / Profiles", chassis_type, f"Total Profile Length: {total_chassis_length_mm/1000.0:.2f} L.M."],
        ["Sealants & Rubber", f"{silicone_type} + EPDM", "5mm EPDM Blocks Under Glass Base Edges"],
        ["Quality & Safety Rules", "Flat Polish All Edges First", "STRICTLY NO CUTTING/DRILLING AFTER TEMPERING"]
    ]

    draw_hardware_bom_table(msp, start_x=W_wall + 600, start_y=H_wall, data=bom_data)

    # 4. التفاصيل التنفيذية المكبرة
    draw_execution_details(
        msp,
        x_base=0,
        y_base=-900,
        glass_thick=glass_thick,
        chassis_type=chassis_type,
        anchor_type=anchor_type,
        spring_model=spring_model,
        lock_type=lock_type
    )

    # 5. إطار اللوحة والخرطوشة
    draw_sheet_frame(
        msp,
        min_x=-600,
        min_y=-1300,
        max_x=W_wall + 4000,
        max_y=H_wall + 700,
        title_text=f"TEMPERED GLASS PARTITION - MODEL {template}"
    )

    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


# ==============================================================================
# 3. واجهة المستخدم والتطبيق (Streamlit Interface)
# ==============================================================================
def main():
    st.set_page_config(page_title="نظام المخططات التنفيذية للشوب دروينج للزجاج", layout="wide", page_icon="📐")

    st.title("📐 النظام الهندسي التنفيذي لإنتاج مخططات الورشة (Shop Drawings)")
    st.caption("برنامج حساب الفواصل، الأوزان، تحديد أدوات التثبيت والإكسسوارات، وتوليد ملفات أوتوكاد معتمدة للتركيب")

    # الشريط الجانبي - خيارات هندسية متكاملة
    st.sidebar.header("⚙️ 1. الزجاج وقطاعات التثبيت")
    glass_thick = st.sidebar.selectbox("سمك الزجاج (مم)", [10, 12, 15, 19], index=1)
    glass_type = st.sidebar.selectbox("نوع الزجاج", ["شفاف (Clear)", "سوبر شفاف (Extra Clear)", "فاميه (Tinted)", "صنفرة / مثلج (Frosted)"])
    glass_color = st.sidebar.selectbox("لون الزجاج", ["شفاف", "رمادي (Grey)", "برونزي (Bronze)", "أخضر (Green)"])
    max_glass_width = st.sidebar.number_input("أقصى عرض للوح الثابت (مم)", value=1200.0, step=100.0)

    chassis_type = st.sidebar.selectbox("قطاع التثبيت (Chassis)", [
        "U-Channel Aluminum 30x35mm",
        "Recessed Stainless Steel Channel 30x30mm",
        "Glass Clamps / Brackets Fixings"
    ])

    st.sidebar.markdown("---")
    st.sidebar.header("🔩 2. أدوات التثبيت والإكسسوارات (Fixings)")
    
    anchor_type = st.sidebar.selectbox("نوع براغي التثبيت (Fixing Anchors)", [
        "M8 x 75mm Heavy Duty Expansion Bolt",
        "M8 Chemical Anchor (Hilti HVU)",
        "M6 High Performance Concrete Screw"
    ])

    spring_model = st.sidebar.selectbox("الماكينة الأرضية (Floor Spring)", [
        "Dorma BTS 75V (EN 1-4 / <= 120kg)",
        "Dorma BTS 80 (EN 3-6 / <= 300kg)",
        "Geze TS 550 IS (HD / <= 250kg)",
        "Top & Bottom Heavy Duty Pivots"
    ])

    lock_type = st.sidebar.selectbox("نوع الكيلون والقفل (Lock System)", [
        "Center Patch Lock with Cylinder",
        "Bottom Corner Patch Lock",
        "Double Glass Corner Lock"
    ])

    handle_type = st.sidebar.selectbox("نوع المقبض (Door Handles)", [
        "Ladder Handle L=600mm Stainless Steel",
        "Ladder Handle L=1200mm Stainless Steel",
        "H-Type Tubular Handle L=450mm"
    ])

    silicone_type = st.sidebar.selectbox("نوع السيليكون ومواد العزل", [
        "Dow Corning 791 Structural Silicone",
        "Sikasil WS-605 S Weatherproofing",
        "Tremco Spectrem 2 Structural Glazing"
    ])

    hardware_finish = st.sidebar.selectbox("تشطيب الإكسسوارات", ["S.S Satin", "Polished Chrome", "Matte Black", "Brushed Gold"])

    st.sidebar.markdown("---")
    st.sidebar.header("📏 3. الخلوصات والفواصل (Gaps)")
    g_bot_nom = st.sidebar.slider("خلوص أسفل الباب (G_bot)", 6.0, 12.0, 8.0, 0.5)
    g_top_nom = st.sidebar.slider("فاصل أعلى الباب (G_top)", 3.0, 6.0, 4.0, 0.5)
    g_mid_nom = st.sidebar.slider("فاصل دلففتي الباب (G_mid)", 3.0, 6.0, 4.0, 0.5)
    g_side_nom = st.sidebar.slider("فاصل الباب والزجاج (G_side)", 3.0, 6.0, 4.0, 0.5)
    g_frame_nom = st.sidebar.slider("خلوص المجرى الجانبي (G_frame)", 4.0, 10.0, 5.0, 0.5)

    gaps_config = {
        "G_bot": {"nom": g_bot_nom},
        "G_top": {"nom": g_top_nom},
        "G_mid": {"nom": g_mid_nom},
        "G_side": {"nom": g_side_nom},
        "G_frame": {"nom": g_frame_nom}
    }

    # الصفحة الرئيسية
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("1. نموذج القاطع المعماري")
        template = st.radio(
            "اختر النموذج:",
            options=["A", "B", "C", "D"],
            format_func=lambda x: {
                "A": "نموذج (A): باب مفرد + فرامة + ثوابت",
                "B": "نموذج (B): باب مزدوج + فرامة + ثوابت",
                "C": "نموذج (C): قاطع جانبي مع باب",
                "D": "نموذج (D): قاطع ثابت بدون أبواب"
            }[x]
        )

    with col2:
        st.subheader("2. الأبعاد الإجمالية للموقع (مم)")
        c1, c2 = st.columns(2)
        W_wall = c1.number_input("عرض الفتحة (W)", value=4000.0, step=50.0)
        H_wall = c2.number_input("ارتفاع الفتحة (H)", value=3000.0, step=50.0)

        if template != "D":
            c3, c4, c5 = st.columns(3)
            W_door = c3.number_input("عرض فتحة الباب (W_door)", value=1000.0 if template in ["A", "C"] else 1800.0, step=50.0)
            H_door = c4.number_input("ارتفاع فتحة الباب (H_door)", value=2200.0, step=50.0)
            X_door = c5.number_input("موقع الباب من اليسار (X_door)", value=1200.0, step=50.0)
        else:
            W_door, H_door, X_door = 0.0, 0.0, 0.0

    st.markdown("---")
    st.subheader("📊 ملخص الحسابات الإنشائية للورشة")

    if template == "B":
        w_single_door = (W_door - (2 * g_side_nom) - g_mid_nom) / 2.0
    elif template in ["A", "C"]:
        w_single_door = W_door - (2 * g_side_nom)
    else:
        w_single_door = 0.0

    h_door_panel = H_door - g_bot_nom - g_top_nom if template != "D" else 0.0
    door_weight_total = ((w_single_door / 1000.0) * (h_door_panel / 1000.0) * glass_thick * 2.5) * 1.10 if template != "D" else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("عرض دلفة الباب المقطوعة", f"{w_single_door:.1f} مم" if template != "D" else "N/A")
    m2.metric("ارتفاع دلفة الباب المقطوعة", f"{h_door_panel:.1f} مم" if template != "D" else "N/A")
    m3.metric("وزن دلفة الباب (مع الأمان)", f"{door_weight_total:.1f} كجم" if template != "D" else "N/A")
    m4.metric("برغي التثبيت المعتمد", anchor_type.split()[0] + " Anchor")

    st.markdown("---")
    st.subheader("💾 تصدير مخطط الورشة المعتمد (.DXF)")

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
        spring_model=spring_model,
        lock_type=lock_type,
        handle_type=handle_type,
        silicone_type=silicone_type,
        glass_thick=glass_thick,
        glass_type=glass_type,
        glass_color=glass_color,
        hardware_finish=hardware_finish,
        gaps=gaps_config
    )

    st.download_button(
        label="📥 تنزيل مخطط الورشة التنفيذي المعتمد (DXF)",
        data=dxf_bytes,
        file_name=f"Execution_Shop_Drawing_{template}_t{glass_thick}mm.dxf",
        mime="application/dxf",
        type="primary"
    )

if __name__ == "__main__":
    main()
