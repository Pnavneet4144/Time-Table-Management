from io import BytesIO
import base64
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO as BIO

DAYS_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]

FIXED_TIME_SLOTS = [
    ("09:30","10:30"),
    ("10:30","11:30"),
    ("11:30","12:30"),
    ("12:30","13:30"),
    ("13:30","14:30"),
    ("14:30","15:30"),
    ("15:30","16:30"),
    ("16:30","17:30"),
]
BREAK_SLOT = ("12:30","13:30")

WHITE        = colors.white
BLACK        = colors.black
BORDER_COLOR = colors.HexColor("#555555")
HEADER_GREY  = colors.HexColor("#e0e0e0")
TITLE_GREY   = colors.HexColor("#f0f0f0")
BLUE_HEADER  = colors.HexColor("#c8d4f0")
DARK_BLUE    = colors.HexColor("#1a237e")
BREAK_COLOR  = colors.HexColor("#eeeeee")

SUBJECT_COLORS = [
    colors.HexColor("#fff59d"),
    colors.HexColor("#a5d6a7"),
    colors.HexColor("#ef9a9a"),
    colors.HexColor("#b3e5fc"),
    colors.HexColor("#ce93d8"),
    colors.HexColor("#80cbc4"),
    colors.HexColor("#ffcc80"),
    colors.HexColor("#f48fb1"),
    colors.HexColor("#bcaaa4"),
    colors.HexColor("#b0bec5"),
]

def get_color(code, cmap):
    if code not in cmap:
        cmap[code] = SUBJECT_COLORS[len(cmap) % len(SUBJECT_COLORS)]
    return cmap[code]

def make_ps(name, **kw):
    return ParagraphStyle(name, parent=getSampleStyleSheet()["Normal"], **kw)

def generate_timetable_pdf(
    entries,
    college_name="Indian Institute of Information Technology",
    college_subtitle="(An Institute of National Importance by an Act of Parliament)",
    college_address="Gat No - 5 & 6, Vill - Nanoli-Tarf Chakan, PO \u2013 Talegaon, Tah \u2013 Maval, Dist - Pune, Maharashtra \u2013 410507",
    semester_label="Even Semester, AY 2025-26",
    section_label="4th Sem Section B CSE",
    location_label="LH8",
    logo_base64=None
) -> BytesIO:

    PAGE = landscape(A4)
    LM = RM = 1.3 * cm
    CONTENT_W = PAGE[0] - LM - RM

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=PAGE,
        leftMargin=LM, rightMargin=RM, topMargin=1.0*cm, bottomMargin=1.0*cm)

    hindi_s = make_ps("H",  fontSize=16, fontName="Helvetica-Bold", textColor=DARK_BLUE, alignment=TA_LEFT, leading=20)
    eng_s   = make_ps("E",  fontSize=10, fontName="Helvetica-Bold", textColor=BLACK,     alignment=TA_LEFT, leading=14)
    act_s   = make_ps("A",  fontSize=8,  fontName="Helvetica-Oblique", textColor=BLACK,  alignment=TA_LEFT, leading=11)
    addr_s  = make_ps("AD", fontSize=7,  textColor=colors.HexColor("#333"),              alignment=TA_LEFT, leading=10)
    cb9     = make_ps("CB", fontSize=8.5,fontName="Helvetica-Bold",                      alignment=TA_CENTER, leading=12)
    cc      = make_ps("CC", fontSize=7.5,leading=10, alignment=TA_CENTER)
    ccb     = make_ps("CCB",fontSize=7.5,fontName="Helvetica-Bold", leading=10,          alignment=TA_CENTER)
    cl      = make_ps("CL", fontSize=7.5,leading=10, alignment=TA_LEFT)
    clb     = make_ps("CLB",fontSize=7.5,fontName="Helvetica-Bold", leading=10,          alignment=TA_LEFT)
    brk_s   = make_ps("BRK",fontSize=7,  fontName="Helvetica-Bold", leading=9,           alignment=TA_CENTER, textColor=colors.HexColor("#444"))

    color_map    = {}
    subject_info = {}
    for e in entries:
        if e.subject:
            c = e.subject.code
            subject_info[c] = {"name": e.subject.name, "coord": e.subject.coordinator_name}
            get_color(c, color_map)

    days_present = sorted(set(e.day_of_week for e in entries),
        key=lambda d: DAYS_ORDER.index(d) if d in DAYS_ORDER else 99)
    if not days_present:
        days_present = ["Monday","Tuesday","Wednesday","Thursday","Friday"]

    entry_map = {}
    for e in entries:
        entry_map.setdefault((e.day_of_week, e.start_time, e.end_time), []).append(e)

    # ── 1. College Header ─────────────────────────────────────────────
    LOGO_W = 2.2 * cm
    TEXT_W = CONTENT_W - LOGO_W - 0.3 * cm

    if logo_base64:
        try:
            img_data = base64.b64decode(logo_base64)
            img_buf  = BIO(img_data)
            logo_img = Image(img_buf, width=LOGO_W*0.85, height=LOGO_W*0.85)
            logo_inner = logo_img
        except Exception:
            logo_inner = Paragraph("", cc)
    else:
        logo_inner = Paragraph("", cc)

    logo_tbl = Table([[logo_inner]], colWidths=[LOGO_W], rowHeights=[2.5*cm])
    logo_tbl.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.5,BORDER_COLOR),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
    ]))

    text_block = [
        Paragraph("\u092d\u093e\u0930\u0924\u0940\u092f \u0938\u0942\u091a\u0928\u093e \u092a\u094d\u0930\u094c\u0926\u094d\u092f\u094b\u0917\u093f\u0915\u0940 \u0938\u0902\u0938\u094d\u0925\u093e\u0928, \u092a\u0941\u0923\u0947", hindi_s),
        Paragraph(f"Indian Institute of Information Technology, Pune", eng_s),
        Paragraph(college_subtitle, act_s),
        Paragraph(college_address, addr_s),
    ]

    hdr = Table([[logo_tbl, text_block]], colWidths=[LOGO_W+0.3*cm, TEXT_W])
    hdr.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))

    # ── 2. Title rows ─────────────────────────────────────────────────
    def title_tbl(text, bg):
        t = Table([[Paragraph(text, cb9)]], colWidths=[CONTENT_W])
        t.setStyle(TableStyle([
            ("BOX",(0,0),(-1,-1),0.6,BORDER_COLOR),
            ("BACKGROUND",(0,0),(-1,-1),bg),
            ("TOPPADDING",(0,0),(-1,-1),4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ]))
        return t

    t1 = title_tbl(f"Time Table for {semester_label}, IIIT Pune", TITLE_GREY)
    t2 = title_tbl(f"Time Table {section_label}  (Location: {location_label})", BLUE_HEADER)

    # ── 3. Timetable grid (exact image format) ────────────────────────
    DAYS_BEFORE = [d for d in days_present if d in ["Monday","Tuesday","Wednesday"]]
    DAYS_AFTER  = [d for d in days_present if d in ["Thursday","Friday","Saturday"]]

    TIME_W  = 2.1 * cm
    BREAK_W = 1.2 * cm
    DAY_W   = (CONTENT_W - TIME_W - BREAK_W) / max(len(days_present), 1)

    col_widths_tt = [TIME_W] + [DAY_W]*len(DAYS_BEFORE) + [BREAK_W] + [DAY_W]*len(DAYS_AFTER)

    header_row = [Paragraph("<b>Time</b>", ccb)]
    for d in DAYS_BEFORE: header_row.append(Paragraph(f"<b>{d[:3]}</b>", ccb))
    header_row.append(Paragraph("<b></b>", ccb))
    for d in DAYS_AFTER:  header_row.append(Paragraph(f"<b>{d[:3]}</b>", ccb))

    tt_data = [header_row]
    cell_bg = {}

    for ri, (st, et) in enumerate(FIXED_TIME_SLOTS, start=1):
        is_break = (st, et) == BREAK_SLOT
        row = [Paragraph(f"<b>{st}</b><br/><b>{et}</b>", ccb)]
        all_day_cols = DAYS_BEFORE + ["__BREAK__"] + DAYS_AFTER

        for day in all_day_cols:
            ci = len(row)
            if day == "__BREAK__":
                row.append(Paragraph("<b>Break</b>" if is_break else "", brk_s))
                cell_bg[(ri, ci)] = BREAK_COLOR
                continue
            if is_break:
                row.append(Paragraph("", cc))
                cell_bg[(ri, ci)] = BREAK_COLOR
                continue
            key = (day, st, et)
            cell_entries = entry_map.get(key, [])
            if cell_entries:
                lines = []
                for e in cell_entries:
                    code = e.subject.code if e.subject else "?"
                    room = e.room.room_number if e.room else ""
                    sec  = e.section or ""
                    if sec and room:
                        lines.append(f"<b>{code}</b><br/>G{sec} - {room}")
                    elif room:
                        lines.append(f"<b>{code}</b><br/>{room}")
                    else:
                        lines.append(f"<b>{code}</b>")
                row.append(Paragraph("<br/>".join(lines), cc))
                main = cell_entries[0].subject.code if cell_entries[0].subject else None
                if main: cell_bg[(ri, ci)] = get_color(main, color_map)
            else:
                row.append(Paragraph("", cc))
        tt_data.append(row)

    tt = Table(tt_data, colWidths=col_widths_tt, repeatRows=1)
    tt_cmds = [
        ("BACKGROUND",(0,0),(-1,0),BLUE_HEADER),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("BACKGROUND",(0,1),(0,-1),HEADER_GREY),
        ("FONTNAME",(0,1),(0,-1),"Helvetica-Bold"),
        ("GRID",(0,0),(-1,-1),0.5,BORDER_COLOR),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("FONTSIZE",(0,0),(-1,-1),7.5),
        ("TOPPADDING",(0,0),(-1,-1),3),
        ("BOTTOMPADDING",(0,0),(-1,-1),3),
        ("LEFTPADDING",(0,0),(-1,-1),2),
        ("RIGHTPADDING",(0,0),(-1,-1),2),
        ("ROWHEIGHT",(0,1),(-1,-1),0.95*cm),
    ]
    for (r,c), bg in cell_bg.items():
        tt_cmds.append(("BACKGROUND",(c,r),(c,r),bg))
    tt.setStyle(TableStyle(tt_cmds))

    # ── 4. Theory + Lab legend side by side ──────────────────────────
    th_data = [[Paragraph("<b>Theory</b>", clb), Paragraph("<b>Faculty</b>", clb)]]
    lab_data_rows = []
    for code, info in subject_info.items():
        th_data.append([Paragraph(f"{code} \u2013 {info['name']}", cl), Paragraph(info['coord'], cl)])
        if "lab" in info['name'].lower():
            lab_data_rows.append([Paragraph(f"<b>{code}</b>", cl), Paragraph(info['coord'], cl)])

    if not lab_data_rows:
        for code, info in subject_info.items():
            lab_data_rows.append([Paragraph(f"<b>{code}</b>", cl), Paragraph(info['coord'], cl)])

    lab_data = [[Paragraph("<b>Lab</b>", clb), Paragraph("<b>Faculty</b>", clb)]] + lab_data_rows

    TH1, TH2 = 5.0*cm, 4.2*cm
    th_tbl = Table(th_data, colWidths=[TH1, TH2])
    th_cmds = [
        ("BACKGROUND",(0,0),(-1,0),HEADER_GREY),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("GRID",(0,0),(-1,-1),0.4,BORDER_COLOR),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2),
        ("LEFTPADDING",(0,0),(-1,-1),4),("FONTSIZE",(0,0),(-1,-1),7.5),
    ]
    for i, code in enumerate(subject_info.keys(), 1):
        th_cmds.append(("BACKGROUND",(0,i),(0,i), get_color(code, color_map)))
    th_tbl.setStyle(TableStyle(th_cmds))

    LA1, LA2 = 2.0*cm, 6.0*cm
    lab_tbl = Table(lab_data, colWidths=[LA1, LA2])
    lab_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),HEADER_GREY),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("GRID",(0,0),(-1,-1),0.4,BORDER_COLOR),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2),
        ("LEFTPADDING",(0,0),(-1,-1),4),("FONTSIZE",(0,0),(-1,-1),7.5),
    ]))

    legend = Table([[th_tbl,"",lab_tbl]], colWidths=[TH1+TH2, 0.8*cm, LA1+LA2])
    legend.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))

    elements = [hdr, Spacer(1,0.2*cm), t1, t2, Spacer(1,0.12*cm), tt, Spacer(1,0.25*cm), legend]
    doc.build(elements)
    buffer.seek(0)
    return buffer