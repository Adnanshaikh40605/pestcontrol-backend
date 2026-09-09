#!/usr/bin/env python3
"""Generate short team PDF: 3 options to shorten New Booking form."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parents[1] / "PestControl99_Booking_Form_Shorten_Options.pdf"

GREEN = colors.HexColor("#0F6B4C")
GREEN_SOFT = colors.HexColor("#E8F5F0")
BLUE = colors.HexColor("#1D4ED8")
BLUE_SOFT = colors.HexColor("#EFF6FF")
AMBER = colors.HexColor("#B45309")
AMBER_SOFT = colors.HexColor("#FEF3C7")
GRAY = colors.HexColor("#374151")
LIGHT = colors.HexColor("#F3F4F6")
BORDER = colors.HexColor("#D1D5DB")
DARK = colors.HexColor("#111827")


def styles():
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "brand",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=GREEN,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "title": ParagraphStyle(
            "title",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=DARK,
            alignment=TA_CENTER,
            spaceAfter=6,
            leading=22,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=GRAY,
            alignment=TA_CENTER,
            spaceAfter=14,
            leading=14,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=DARK,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=GRAY,
            leading=14,
            spaceAfter=6,
        ),
        "option_title": ParagraphStyle(
            "option_title",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=DARK,
            spaceAfter=4,
        ),
        "option_body": ParagraphStyle(
            "option_body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            textColor=GRAY,
            leading=13,
            spaceAfter=3,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            textColor=GRAY,
            leading=13,
            leftIndent=10,
            spaceAfter=2,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=GRAY,
            leading=12,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=colors.white,
            leading=12,
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=GRAY,
            alignment=TA_CENTER,
        ),
        "callout": ParagraphStyle(
            "callout",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            textColor=DARK,
            leading=13,
        ),
    }


def option_box(s, number: str, title: str, summary: str, points: list[str], best_for: str, bg, accent):
    header = Paragraph(f"<font color='#{accent.hexval()[2:]}'>{number}</font>  {title}", s["option_title"])
    lines = [Paragraph(summary, s["option_body"])]
    for p in points:
        lines.append(Paragraph(f"• {p}", s["bullet"]))
    lines.append(Paragraph(f"<b>Best for:</b> {best_for}", s["option_body"]))
    inner = [header, Spacer(1, 2)] + lines
    data = [[inner]]
    t = Table(data, colWidths=[170 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), 1, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return t


def build():
    s = styles()
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Pest Control 99 — Shorten New Booking Form",
        author="Pest Control 99",
    )
    story = []

    story.append(Paragraph("PEST CONTROL 99 — CRM", s["brand"]))
    story.append(Paragraph("How to Shorten the New Booking Form", s["title"]))
    story.append(
        Paragraph(
            "Team note: the current form is long because client, location, payment, "
            "revenue model, services, reminder, and notes are all on one page. "
            "Below are <b>3 options</b> to make booking creation shorter and easier.",
            s["subtitle"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=10))

    story.append(Paragraph("Why the form feels long today", s["h2"]))
    story.append(
        Paragraph(
            "Staff must scroll through many fields for a normal home booking. "
            "Most daily bookings only need: <b>mobile → name → address → service → "
            "BHK → date/time → reference → Create</b>. Extra fields (payment, revenue "
            "40/60, reminder) can stay hidden or move to a second step.",
            s["body"],
        )
    )

    story.append(Spacer(1, 6))
    story.append(Paragraph("Three options for the team", s["h2"]))

    story.append(
        option_box(
            s,
            "OPTION 1",
            "3-Step Form (Wizard)",
            "Instead of one long page, booking is split into 3 small screens.",
            [
                "Step 1 — Client: mobile, name, address",
                "Step 2 — Service & date: pest, BHK, date, time, reference",
                "Step 3 — Optional: reminder, notes (can skip)",
                "Staff see less at once → feels faster and easier",
            ],
            "Teams that create many bookings every day and want a modern, clear flow.",
            BLUE_SOFT,
            BLUE,
        )
    )
    story.append(Spacer(1, 8))

    story.append(
        option_box(
            s,
            "OPTION 2",
            "Same Page, Hide Extra Sections",
            "Keep one page, but hide rarely used parts under “Show more”.",
            [
                "Always open: client, service, date, time, reference, Create",
                "Collapsed by default: Revenue Model (40/60), payment status/mode, reminder, extra notes",
                "Fastest to build — same page, less scrolling, minimal retraining",
            ],
            "Quick fix this week with low change for the team.",
            GREEN_SOFT,
            GREEN,
        )
    )
    story.append(Spacer(1, 8))

    story.append(
        option_box(
            s,
            "OPTION 3",
            "Quick Book + Advanced Book",
            "Two buttons when creating a booking — simple vs full form.",
            [
                "Quick Book (~8 fields): mobile, service, BHK, address, date, time, reference",
                "Advanced Book: full form for society, hotel, multi-pest, AMC, special cases",
                "Most staff use Quick Book; managers use Advanced when needed",
            ],
            "Mixed team — call centre / front desk + managers.",
            AMBER_SOFT,
            AMBER,
        )
    )

    story.append(Spacer(1, 12))
    story.append(Paragraph("Simple comparison", s["h2"]))

    header = [
        Paragraph("Option", s["table_header"]),
        Paragraph("Idea", s["table_header"]),
        Paragraph("Best for", s["table_header"]),
    ]
    rows = [
        header,
        [
            Paragraph("<b>1 — Wizard</b>", s["table_cell"]),
            Paragraph("3 short steps", s["table_cell"]),
            Paragraph("Less confusion, modern feel", s["table_cell"]),
        ],
        [
            Paragraph("<b>2 — Collapse</b>", s["table_cell"]),
            Paragraph("Hide extra sections", s["table_cell"]),
            Paragraph("Quick fix, minimal change", s["table_cell"]),
        ],
        [
            Paragraph("<b>3 — Quick + Advanced</b>", s["table_cell"]),
            Paragraph("Simple vs full form", s["table_cell"]),
            Paragraph("Call centre + managers", s["table_cell"]),
        ],
    ]
    table = Table(rows, colWidths=[42 * mm, 55 * mm, 73 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("BACKGROUND", (0, 1), (-1, 1), LIGHT),
                ("BACKGROUND", (0, 3), (-1, 3), LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(table)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Suggestion", s["h2"]))
    callout_data = [[
        Paragraph(
            "<b>Recommended path:</b> Start with <b>Option 2</b> this week "
            "(hide revenue / payment / reminder). Later add <b>Option 3</b> "
            "(Quick Book) or <b>Option 1</b> (wizard) if the team still wants it shorter.",
            s["callout"],
        )
    ]]
    callout = Table(callout_data, colWidths=[170 * mm])
    callout.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), GREEN_SOFT),
                ("BOX", (0, 0), (-1, -1), 1, GREEN),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(callout)

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))
    story.append(
        Paragraph(
            "Internal note for Pest Control 99 team • New Booking form (CRM) • Discuss and pick one option",
            s["footer"],
        )
    )

    doc.build(story)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
