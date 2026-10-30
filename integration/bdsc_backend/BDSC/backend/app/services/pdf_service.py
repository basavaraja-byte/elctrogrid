"""PDF Invoice and Service Receipt Generator for ElectroGrid / DispatchGrid."""

import os
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

INVOICE_STORAGE_DIR = Path("static/invoices")


def format_duration(minutes: int) -> str:
    """Format minutes into human-readable duration e.g. '1 hour 20 minutes'."""
    hrs = minutes // 60
    mins = minutes % 60
    parts = []
    if hrs > 0:
        parts.append(f"{hrs} hour{'s' if hrs != 1 else ''}")
    if mins > 0 or hrs == 0:
        parts.append(f"{mins} minute{'s' if mins != 1 else ''}")
    return " ".join(parts)


def generate_invoice_pdf(
    *,
    invoice_number: str,
    invoice_date: datetime,
    customer_name: str,
    job_reference: str,
    technician_name: str,
    service_description: str,
    duration_minutes: int,
    base_amount_inr: int,
    additional_blocks: int,
    additional_amount_inr: int,
    labour_total_inr: int,
    payment_method: str,
    payment_status: str,
    payment_reference: str,
    damaged_components: list[dict] | None = None,
) -> str:
    """Generate a high-quality, professional PDF service receipt and return relative URL path."""
    INVOICE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{invoice_number}.pdf"
    file_path = INVOICE_STORAGE_DIR / filename

    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    brand_style = ParagraphStyle(
        "BrandHeader",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1E3A8A"),  # Deep Navy Blue
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#2563EB"),
    )
    receipt_meta_style = ParagraphStyle(
        "ReceiptMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#334155"),
    )
    section_title_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0F172A"),
    )
    cell_label_style = ParagraphStyle(
        "CellLabel",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569"),
    )
    cell_bold_style = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0F172A"),
    )
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        alignment=1,  # Center
        textColor=colors.HexColor("#2563EB"),
    )

    story = []

    # 1. Header Banner
    header_data = [
        [
            Paragraph("<b>ELECTROGRID ELECTRICAL OPS</b>", brand_style),
            Paragraph(f"<b>RECEIPT: {invoice_number}</b><br/>Date: {invoice_date.strftime('%d %b %Y')}", receipt_meta_style),
        ],
        [
            Paragraph("OFFICIAL SERVICE PAYMENT RECEIPT", subtitle_style),
            Paragraph("Status: <font color='#059669'><b>PAID &amp; CLOSED</b></font>", receipt_meta_style),
        ],
    ]
    header_table = Table(header_data, colWidths=[4.0 * inch, 3.2 * inch])
    header_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(header_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2563EB"), spaceAfter=15))

    # 2. Customer & Job Summary Box
    summary_data = [
        [
            Paragraph("<b>CUSTOMER</b>", cell_label_style),
            Paragraph(customer_name, cell_bold_style),
            Paragraph("<b>TECHNICIAN</b>", cell_label_style),
            Paragraph(technician_name, cell_bold_style),
        ],
        [
            Paragraph("<b>JOB REFERENCE</b>", cell_label_style),
            Paragraph(job_reference, cell_bold_style),
            Paragraph("<b>WORK DURATION</b>", cell_label_style),
            Paragraph(format_duration(duration_minutes), cell_bold_style),
        ],
        [
            Paragraph("<b>SERVICE</b>", cell_label_style),
            Paragraph(service_description or "Electrical Field Inspection & Repair", cell_bold_style),
            Paragraph("<b>PAYMENT REF</b>", cell_label_style),
            Paragraph(payment_reference, cell_bold_style),
        ],
    ]
    summary_table = Table(summary_data, colWidths=[1.4 * inch, 2.3 * inch, 1.4 * inch, 2.1 * inch])
    summary_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(summary_table)
    story.append(Spacer(1, 15))

    # 3. Bill Breakdown Table
    story.append(Paragraph("TIME-BASED LABOUR CHARGES", section_title_style))
    story.append(Spacer(1, 6))

    bill_rows = [
        [
            Paragraph("<b>Service Description / Slab</b>", cell_bold_style),
            Paragraph("<b>Basis</b>", cell_bold_style),
            Paragraph("<b>Rate</b>", cell_bold_style),
            Paragraph("<b>Amount (INR)</b>", cell_bold_style),
        ],
        [
            Paragraph("Base Service Labour", cell_label_style),
            Paragraph("First 60 minutes", cell_label_style),
            Paragraph("₹500.00 flat", cell_label_style),
            Paragraph(f"₹{base_amount_inr:.2f}", cell_bold_style),
        ],
    ]

    if additional_blocks > 0:
        bill_rows.append([
            Paragraph("Additional Time Blocks", cell_label_style),
            Paragraph(f"{additional_blocks} block(s) @ 30 mins each", cell_label_style),
            Paragraph("₹100.00 / block", cell_label_style),
            Paragraph(f"₹{additional_amount_inr:.2f}", cell_bold_style),
        ])

    bill_rows.append([
        Paragraph("<b>TOTAL LABOUR CHARGES</b>", cell_bold_style),
        Paragraph("", cell_label_style),
        Paragraph("", cell_label_style),
        Paragraph(f"<b>₹{labour_total_inr:.2f}</b>", cell_bold_style),
    ])

    bill_table = Table(bill_rows, colWidths=[2.8 * inch, 2.0 * inch, 1.2 * inch, 1.2 * inch])
    bill_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#2563EB")),
            ("LINEBELOW", (0, -1), (-1, -1), 1.5, colors.HexColor("#0F172A")),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(bill_table)
    story.append(Spacer(1, 15))

    # 4. Damaged Components / Replacement Parts (Separate Section)
    story.append(Paragraph("DAMAGED COMPONENTS / REPLACEMENT PARTS (CUSTOMER PRICING)", section_title_style))
    story.append(Spacer(1, 6))

    if damaged_components and len(damaged_components) > 0:
        parts_rows = [
            [
                Paragraph("<b>Component Name</b>", cell_bold_style),
                Paragraph("<b>Identified Damage / Issue</b>", cell_bold_style),
                Paragraph("<b>Qty</b>", cell_bold_style),
                Paragraph("<b>Pricing Status</b>", cell_bold_style),
            ]
        ]
        for part in damaged_components:
            name = part.get("component_name") or part.get("name") or "Electrical Component"
            desc = part.get("damage_description") or part.get("description") or "Physical or electrical fault"
            qty = str(part.get("quantity") or 1)
            status_txt = part.get("price_status") or "Price to be confirmed"
            parts_rows.append([
                Paragraph(name, cell_bold_style),
                Paragraph(desc, cell_label_style),
                Paragraph(qty, cell_label_style),
                Paragraph(f"<font color='#D97706'><b>{status_txt}</b></font>", cell_label_style),
            ])
    else:
        parts_rows = [
            [
                Paragraph("<b>Component Name</b>", cell_bold_style),
                Paragraph("<b>Identified Damage / Issue</b>", cell_bold_style),
                Paragraph("<b>Qty</b>", cell_bold_style),
                Paragraph("<b>Pricing Status</b>", cell_bold_style),
            ],
            [
                Paragraph("None Reported", cell_label_style),
                Paragraph("All installed equipment verified intact and operational", cell_label_style),
                Paragraph("-", cell_label_style),
                Paragraph("N/A", cell_label_style),
            ],
        ]

    parts_table = Table(parts_rows, colWidths=[2.2 * inch, 2.6 * inch, 0.8 * inch, 1.6 * inch])
    parts_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FEF3C7")),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#D97706")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(parts_table)
    story.append(Spacer(1, 15))

    # 5. Payment Settlement Box
    settle_rows = [
        [
            Paragraph("<b>SETTLEMENT SUMMARY</b>", cell_bold_style),
            Paragraph(f"Total Amount Paid: <font size='12' color='#059669'><b>₹{labour_total_inr:.2f}</b></font>", cell_bold_style),
        ],
        [
            Paragraph(f"Payment Method: <b>{payment_method.upper()}</b>", cell_label_style),
            Paragraph(f"Payment Status: <font color='#059669'><b>{payment_status.upper()}</b></font>", cell_bold_style),
        ],
        [
            Paragraph(f"Transaction Ref: <b>{payment_reference}</b>", cell_label_style),
            Paragraph("Job Status: <font color='#1E40AF'><b>COMPLETED &amp; CLOSED</b></font>", cell_bold_style),
        ],
    ]
    settle_table = Table(settle_rows, colWidths=[3.6 * inch, 3.6 * inch])
    settle_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
            ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#22C55E")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(settle_table)
    story.append(Spacer(1, 20))

    # 6. Footer Note
    story.append(Paragraph("Thank you for choosing ElectroGrid / DispatchGrid Field Services!", footer_style))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "<font size='8' color='#64748B'>Computer-generated official receipt. Valid for all accounting and warranty purposes.</font>",
            ParagraphStyle("SubFooter", parent=styles["Normal"], alignment=1),
        )
    )

    doc.build(story)
    return f"/invoices/{filename}"

