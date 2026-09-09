#!/usr/bin/env python3
"""Generate Pest Control 99 CRM Accounts User Guide PDF for accountant sharing."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parents[1] / "PestControl99_CRM_Accounts_Guide.pdf"

GREEN = colors.HexColor("#0F6B4C")
GREEN_DARK = colors.HexColor("#0A4D38")
GREEN_SOFT = colors.HexColor("#E8F5F0")
AMBER = colors.HexColor("#B45309")
AMBER_SOFT = colors.HexColor("#FEF3C7")
GRAY = colors.HexColor("#374151")
LIGHT = colors.HexColor("#F3F4F6")
BORDER = colors.HexColor("#D1D5DB")


def styles():
    base = getSampleStyleSheet()
    return {
        "cover_brand": ParagraphStyle(
            "cover_brand",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=colors.white,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=12,
            textColor=colors.white,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.HexColor("#D1FAE5"),
            alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=GREEN_DARK,
            spaceBefore=14,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=GREEN,
            spaceBefore=10,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=GRAY,
            alignment=TA_JUSTIFY,
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=GRAY,
            leftIndent=4,
        ),
        "step": ParagraphStyle(
            "step",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=GRAY,
        ),
        "note": ParagraphStyle(
            "note",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12,
            textColor=AMBER,
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=colors.HexColor("#6B7280"),
            alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=GRAY,
        ),
        "table_head": ParagraphStyle(
            "table_head",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            textColor=colors.white,
        ),
    }


def bullets(items, style):
    return ListFlowable(
        [ListItem(Paragraph(i, style), leftIndent=8, bulletColor=GREEN) for i in items],
        bulletType="bullet",
        start="•",
        leftIndent=12,
        bulletFontSize=9,
        spaceBefore=2,
        spaceAfter=6,
    )


def steps(items, style):
    return ListFlowable(
        [ListItem(Paragraph(i, style), leftIndent=8, bulletColor=GREEN) for i in items],
        bulletType="1",
        leftIndent=14,
        bulletFontSize=9,
        spaceBefore=2,
        spaceAfter=6,
    )


def section_banner(title: str, subtitle: str, s) -> list:
    data = [[Paragraph(f"<b>{title}</b><br/><font size='8'>{subtitle}</font>", ParagraphStyle(
        "ban",
        fontName="Helvetica",
        fontSize=11,
        textColor=colors.white,
        leading=14,
    ))]]
    t = Table(data, colWidths=[180 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREEN),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return [Spacer(1, 6), t, Spacer(1, 8)]


def callout(text: str, s) -> Table:
    data = [[Paragraph(text, s["note"])]]
    t = Table(data, colWidths=[180 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AMBER_SOFT),
        ("BOX", (0, 0), (-1, -1), 0.5, AMBER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(GREEN)
    canvas.rect(0, A4[1] - 12 * mm, A4[0], 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(15 * mm, A4[1] - 7.5 * mm, "Pest Control 99  |  CRM Accounts User Guide")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(A4[0] - 15 * mm, A4[1] - 7.5 * mm, "For Accountant / Accounts Team")

    canvas.setFillColor(LIGHT)
    canvas.rect(0, 0, A4[0], 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(15 * mm, 5 * mm, "Confidential — Internal use only")
    canvas.drawRightString(A4[0] - 15 * mm, 5 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build():
    s = styles()
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title="Pest Control 99 — CRM Accounts User Guide",
        author="Pest Control 99",
    )
    story = []

    # Cover card
    cover = Table(
        [[
            Paragraph("PEST CONTROL 99", s["cover_brand"]),
            Paragraph("CRM Accounts Module — User Guide", s["cover_sub"]),
            Paragraph("How to use Dashboard, Inventory, Expenses,<br/>Booking Profit, Alerts &amp; Reports", s["cover_sub"]),
            Spacer(1, 6),
            Paragraph("For Accountant &amp; Accounts Team", s["cover_meta"]),
            Paragraph("CRM: https://pestcontrol-crm-frontend.vercel.app/accounts", s["cover_meta"]),
        ]],
        colWidths=[180 * mm],
    )
    # Flatten - Table needs rows
    cover = Table(
        [
            [Paragraph("PEST CONTROL 99", s["cover_brand"])],
            [Paragraph("CRM Accounts Module — User Guide", s["cover_sub"])],
            [Paragraph(
                "How to use Dashboard, Inventory, Expenses, Booking Profit, Alerts &amp; Reports",
                s["cover_sub"],
            )],
            [Spacer(1, 4)],
            [Paragraph("For Accountant &amp; Accounts Team", s["cover_meta"])],
            [Paragraph("Open: https://pestcontrol-crm-frontend.vercel.app/accounts", s["cover_meta"])],
        ],
        colWidths=[180 * mm],
    )
    cover.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREEN_DARK),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (0, 0), 16),
        ("BOTTOMPADDING", (0, -1), (0, -1), 16),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(cover)
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. What is Accounts?", s["h1"]))
    story.append(Paragraph(
        "Accounts module company ka paisa, chemical stock, expenses aur har booking ka profit "
        "track karta hai. Yeh <b>Technician Ledger</b> se alag hai — Ledger technician payment "
        "settle karne ke liye hai; Accounts company profit &amp; stock ke liye hai.",
        s["body"],
    ))

    menu_data = [
        [Paragraph("Menu", s["table_head"]), Paragraph("Path", s["table_head"]), Paragraph("Kaam", s["table_head"])],
        [Paragraph("Accounts", s["table_cell"]), Paragraph("/accounts", s["table_cell"]), Paragraph("Daily / monthly dashboard", s["table_cell"])],
        [Paragraph("Inventory", s["table_cell"]), Paragraph("/accounts/inventory", s["table_cell"]), Paragraph("Chemical stock, purchase, transfer", s["table_cell"])],
        [Paragraph("Expenses", s["table_cell"]), Paragraph("/accounts/expenses", s["table_cell"]), Paragraph("Office / marketing / tech expenses", s["table_cell"])],
        [Paragraph("Booking Profit", s["table_cell"]), Paragraph("/accounts/booking-profit", s["table_cell"]), Paragraph("Har booking ka profit", s["table_cell"])],
        [Paragraph("Accounts Alerts", s["table_cell"]), Paragraph("/accounts/alerts", s["table_cell"]), Paragraph("Low stock, expiry, warnings", s["table_cell"])],
        [Paragraph("Accounts Reports", s["table_cell"]), Paragraph("/accounts/reports", s["table_cell"]), Paragraph("CSV / PDF reports", s["table_cell"])],
    ]
    menu = Table(menu_data, colWidths=[40 * mm, 55 * mm, 85 * mm])
    menu.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GREEN_SOFT]),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(menu)

    # Dashboard
    story.extend(section_banner("2. Accounts Dashboard", "Har subah pehle yahan check karein", s))
    story.append(Paragraph("Yahan aapko dikhega:", s["body"]))
    story.append(bullets([
        "<b>Today:</b> Collection/Sales, Expenses, Gross Profit, Company Net, Chemical Used, Avg Cost/Booking",
        "<b>This Month:</b> Sales, Expenses, Gross/Company Net, Inventory Value, Avg Profit/Booking",
        "Low stock count, Unread alerts, Month booking count",
    ], s["bullet"]))
    story.append(callout(
        "Note: Gross Profit = Visit revenue − Chemical − Tech expenses − Tech 40% − Overhead.  "
        "Company Net = Company 60% − Chemical − Tech expenses − Overhead.",
        s,
    ))

    # Inventory
    story.extend(section_banner("3. Inventory &amp; Stock", "Chemical kharidna, stock dekhna, transfer", s))
    story.append(Paragraph("<b>Pehli baar setup</b>", s["h2"]))
    story.append(steps([
        "Chemical name add karein (jaise Termite Chemical, Gel, Spray) — unit ml",
        "Zarurat ho to Equipment add karein",
        "<b>+ Add supplier</b> se supplier banaayein",
        "<b>Purchase entry:</b> Branch → Chemical → Qty → Cost/unit → optional Supplier → <b>Record purchase</b>",
    ], s["step"]))
    story.append(Paragraph("<b>Roz ka kaam</b>", s["h2"]))
    story.append(bullets([
        "Nayi purchase aayi → Purchase entry",
        "Stock kam / galat dikhe → Adjust (+/− qty)",
        "Ek branch se doosri branch → Transfer",
        "Stock dekhna → Stock balance table",
        "Low stock / Expiry lists isi page pe neeche milengi",
        "Movement history se har in/out entry check kar sakte ho",
    ], s["bullet"]))
    story.append(callout(
        "Important: Purchase sahi amount aur qty ke saath na ki to chemical cost aur booking profit galat aayega.",
        s,
    ))

    # Expenses
    story.extend(section_banner("4. Expense Management", "Har kharcha yahan entry karein", s))
    story.append(Paragraph("<b>Naya expense kaise add karein</b>", s["h2"]))
    story.append(steps([
        "Branch select karein (Mumbai / Pune / etc.)",
        "Category select karein — Office / Marketing / Technician / Purchase",
        "Amount daalein",
        "Vendor name likhein",
        "Agar booking se related hai to <b>Booking ID</b> daalein (optional)",
        "Bill photo / PDF attach karein (recommended)",
        "<b>Save expense</b> dabayein",
    ], s["step"]))
    story.append(Paragraph(
        "Neeche wali table me saari saved expenses date, branch, category, vendor, amount aur booking ke saath dikhti hain.",
        s["body"],
    ))

    # Booking profit
    story.extend(section_banner("5. Booking Profit", "Har completed booking ka profit", s))
    story.append(Paragraph("Table me har booking ke liye dikhta hai:", s["body"]))
    story.append(bullets([
        "Visit ₹ (service value)",
        "Chemical cost, Expenses, Tech cost (40%), Overhead",
        "<b>Gross profit</b> aur <b>Company net profit</b>",
        "Margin %",
    ], s["bullet"]))
    story.append(Paragraph("<b>Chemical usage miss ho to</b>", s["h2"]))
    story.append(steps([
        "Booking / Job ID daalein",
        "Chemical select karein",
        "Qty (ml) daalein",
        "<b>Save usage</b> — profit auto recalculate hoga",
    ], s["step"]))
    story.append(Paragraph(
        "Month end pe ek baar <b>Allocate monthly overhead</b> button dabayein taaki office overhead bookings me split ho jaye.",
        s["body"],
    ))

    # Alerts
    story.extend(section_banner("6. Accounts Alerts", "Warnings ko ignore mat karein", s))
    story.append(Paragraph("Yahan aati hain:", s["body"]))
    story.append(bullets([
        "Low stock alerts",
        "Expiry / near-expiry chemicals",
        "High expense warnings",
        "Supplier payment related alerts",
    ], s["bullet"]))
    story.append(steps([
        "<b>Run alerts now</b> dabayein (list refresh)",
        "Har alert padhein — branch aur severity dekhein",
        "Kaam ho jaye to <b>Resolve</b> dabayein",
    ], s["step"]))

    # Reports
    story.extend(section_banner("7. Accounts Reports", "Excel CSV aur Print/PDF", s))
    story.append(Paragraph("Available reports:", s["body"]))
    story.append(bullets([
        "Booking Profit Report",
        "Inventory Report",
        "Stock Movement Report",
        "Expense Report",
        "Monthly Branch P&amp;L",
    ], s["bullet"]))
    story.append(Paragraph(
        "<b>CSV</b> = Excel me open karke CA / records ke liye save karein.  "
        "<b>Print / PDF</b> = browser print dialog se PDF bana sakte ho.",
        s["body"],
    ))

    # Routines
    story.append(Paragraph("8. Daily &amp; Month-end Routine", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=GREEN, spaceAfter=8))

    routine = [
        [Paragraph("<b>Daily (har din)</b>", s["table_head"]), Paragraph("<b>Month end</b>", s["table_head"])],
        [
            Paragraph(
                "1. Dashboard check<br/>"
                "2. Nayi purchase entry<br/>"
                "3. Naye expenses save<br/>"
                "4. Alerts check + resolve<br/>"
                "5. Booking profit me odd figures check",
                s["table_cell"],
            ),
            Paragraph(
                "1. Saari purchase + expenses complete<br/>"
                "2. Booking Profit → Allocate monthly overhead<br/>"
                "3. Dashboard → Rebuild P&amp;L (agar refresh chahiye)<br/>"
                "4. Reports se CSV download + folder me save<br/>"
                "5. Branch-wise P&amp;L review",
                s["table_cell"],
            ),
        ],
    ]
    rt = Table(routine, colWidths=[90 * mm, 90 * mm])
    rt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("BACKGROUND", (0, 1), (-1, 1), GREEN_SOFT),
        ("BOX", (0, 0), (-1, -1), 0.6, GREEN),
        ("LINEBEFORE", (1, 0), (1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(rt)

    story.append(Spacer(1, 12))
    story.append(Paragraph("9. Common Mistakes (Avoid)", s["h1"]))
    story.append(bullets([
        "Purchase bina cost/unit ke save karna",
        "Expense booking se related ho lekin Booking ID na daalna",
        "Chemical usage booking pe miss karna → profit zyada dikhega",
        "Technician Ledger ko Accounts samajhna — dono alag modules hain",
        "Alerts ignore karna (stock khatam / expiry)",
    ], s["bullet"]))

    story.append(Spacer(1, 10))
    end = Table(
        [[Paragraph(
            "<b>Support:</b> Koi doubt ho to CRM ka screenshot bhejein — Accounts team guide kar degi.<br/>"
            "<b>CRM Accounts:</b> https://pestcontrol-crm-frontend.vercel.app/accounts",
            ParagraphStyle("end", fontName="Helvetica", fontSize=9, textColor=GREEN_DARK, leading=13, alignment=TA_CENTER),
        )]],
        colWidths=[180 * mm],
    )
    end.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREEN_SOFT),
        ("BOX", (0, 0), (-1, -1), 1, GREEN),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(end)

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
