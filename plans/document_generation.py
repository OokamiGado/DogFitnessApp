
"""
plans/document_generation.py

Generowanie dokumentow PDF i DOCX na podstawie TrainingPlan:
  - "Plan szczegolowy" (pelna wersja: Cel/Wykonanie/Ilosc/Uwagi per cwiczenie)
  - "Fiszka treningowa" (skrocona wersja tabelaryczna: Cwiczenie | Jak wykonac | Ilosc)

Uzywa BrandingProfile.get_default() (lub przekazanego profilu) do
personalizacji wygladu: logo, kolor belek sekcji, kolor tekstu,
czcionka, tekst stopki.

Fonty TTF (pelne wsparcie polskich znakow diakrytycznych) sa rejestrowane
przez wspolny modul dogfitness.pdf_fonts - UZYWANY TAKZE przez
clients/views.py:dog_pdf, dzieki czemu wszystkie dokumenty PDF w calej
aplikacji maja identyczna, poprawna obsluge polskich znakow (bez
duplikowania logiki rejestracji fontow w kazdym miejscu).
"""

import os
from datetime import date
from io import BytesIO

from django.conf import settings

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
)

from docx import Document as DocxDocument
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from dogfitness.pdf_fonts import get_pdf_fonts as _get_pdf_fonts


def _hex_to_rgbcolor(hex_str):
    hex_str = hex_str.lstrip('#')
    return RGBColor(int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))


def _hex_to_reportlab_color(hex_str):
    return colors.HexColor(hex_str)


def _dog_header_text(dog):
    parts = []
    if dog.breed:
        parts.append(dog.breed)
    age = dog.get_age_display()
    if age:
        parts.append(age)
    sex = dog.get_sex_display() if dog.sex else None
    if sex:
        parts.append(sex)
    return dog.name.upper(), "  *  ".join(parts)


def _set_docx_cell_background(cell, hex_color):
    hex_color = hex_color.lstrip('#')
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tc_pr.append(shd)


def generate_detailed_pdf(plan, branding):
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
    )

    font_family = branding.font_family if branding else 'Helvetica'
    font_name, font_bold = _get_pdf_fonts(font_family)
    primary_color = _hex_to_reportlab_color(branding.primary_color if branding else '#D9D9D9')
    text_color = _hex_to_reportlab_color(branding.text_color if branding else '#000000')

    styles = getSampleStyleSheet()
    style_normal = ParagraphStyle('normal_pl', parent=styles['Normal'], fontName=font_name, fontSize=10, leading=13)
    style_bold = ParagraphStyle('bold_pl', parent=style_normal, fontName=font_bold, fontSize=11, leading=14)
    style_section = ParagraphStyle(
        'section_pl', parent=style_normal, fontName=font_bold, fontSize=12,
        textColor=text_color, leading=16,
    )
    style_subtitle = ParagraphStyle('subtitle_pl', parent=style_normal, fontSize=9, textColor=colors.HexColor('#595959'))

    elements = []

    name_upper, subtitle = _dog_header_text(plan.dog)

    logo_cell = ""
    if branding and branding.logo and os.path.exists(branding.logo.path):
        try:
            logo_cell = RLImage(branding.logo.path, width=25 * mm, height=25 * mm, kind='proportional')
        except Exception:
            logo_cell = ""

    title_html = f"<b>{name_upper}</b><br/><font size=9 color='#595959'>{subtitle}</font><br/><b>SZCZEGOLOWY PLAN CWICZEN FITNESS</b>"
    date_html = f"<font size=8 color='#595959'>Data:</font><br/><b>{date.today().strftime('%d.%m.%Y')}</b>"

    header_table = Table(
        [[logo_cell, Paragraph(title_html, style_normal), Paragraph(date_html, style_normal)]],
        colWidths=[30 * mm, 110 * mm, 34 * mm],
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 6 * mm))

    def section_bar(text):
        t = Table([[Paragraph(f"<b>{text}</b>", style_section)]], colWidths=[174 * mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), primary_color),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ]))
        return t

    if plan.training_goal:
        elements.append(section_bar("CEL TRENINGU"))
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph(plan.training_goal.replace(chr(10), '<br/>'), style_normal))
        elements.append(Spacer(1, 5 * mm))

    if plan.safety_rules:
        elements.append(section_bar("WAZNE ZASADY I BEZPIECZENSTWO"))
        elements.append(Spacer(1, 2 * mm))
        for line in plan.safety_rules.split(chr(10)):
            if line.strip():
                elements.append(Paragraph(f"&bull; {line.strip()}", style_normal))
        elements.append(Spacer(1, 5 * mm))

    for exercise_set in plan.exercise_sets.all():
        freq = exercise_set.get_frequency_display_text()
        label = exercise_set.name
        if freq:
            label += f"  --  wykonuj {freq}"
        elements.append(section_bar(label))
        elements.append(Spacer(1, 3 * mm))

        for idx, pe in enumerate(exercise_set.plan_exercises.all(), start=1):
            block = []
            block.append(Paragraph(f"<b>{idx}. {pe.exercise.name}</b>", style_bold))
            if pe.goal_text:
                block.append(Paragraph(f"<b>Cel:</b> {pe.goal_text}", style_normal))
            if pe.execution_text:
                block.append(Paragraph(f"<b>Wykonanie:</b> {pe.execution_text}", style_normal))
            if pe.reps_text:
                block.append(Paragraph(f"<b>Powtorzenia:</b> {pe.reps_text}", style_normal))
            if pe.notes_text:
                block.append(Paragraph(f"<b>Uwagi:</b> {pe.notes_text}", style_normal))
            block.append(Spacer(1, 4 * mm))
            elements.append(KeepTogether(block))

        elements.append(Spacer(1, 3 * mm))

    if branding and branding.footer_text:
        elements.append(Spacer(1, 4 * mm))
        elements.append(Paragraph(f"<i>{branding.footer_text}</i>", style_subtitle))

    doc.build(elements)
    buf.seek(0)
    return buf


def generate_fiszka_pdf(plan, branding):
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
    )

    font_family = branding.font_family if branding else 'Helvetica'
    font_name, font_bold = _get_pdf_fonts(font_family)
    primary_color = _hex_to_reportlab_color(branding.primary_color if branding else '#D9D9D9')
    text_color = _hex_to_reportlab_color(branding.text_color if branding else '#000000')

    styles = getSampleStyleSheet()
    style_normal = ParagraphStyle('normal_pl2', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=12)
    style_header_cell = ParagraphStyle('header_cell', parent=style_normal, fontName=font_bold, fontSize=9)
    style_section = ParagraphStyle(
        'section_pl2', parent=style_normal, fontName=font_bold, fontSize=12,
        textColor=text_color, leading=16,
    )
    style_subtitle = ParagraphStyle('subtitle_pl2', parent=style_normal, fontSize=9, textColor=colors.HexColor('#595959'))

    elements = []

    name_upper, subtitle = _dog_header_text(plan.dog)

    logo_cell = ""
    if branding and branding.logo and os.path.exists(branding.logo.path):
        try:
            logo_cell = RLImage(branding.logo.path, width=25 * mm, height=25 * mm, kind='proportional')
        except Exception:
            logo_cell = ""

    title_html = f"<b>{name_upper}</b><br/><font size=9 color='#595959'>{subtitle}</font><br/><b>PLAN CWICZEN FITNESS</b>"
    date_html = f"<font size=8 color='#595959'>Data:</font><br/><b>{date.today().strftime('%d.%m.%Y')}</b>"

    header_table = Table(
        [[logo_cell, Paragraph(title_html, style_normal), Paragraph(date_html, style_normal)]],
        colWidths=[30 * mm, 110 * mm, 34 * mm],
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 6 * mm))

    def section_bar(text):
        t = Table([[Paragraph(f"<b>{text}</b>", style_section)]], colWidths=[174 * mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), primary_color),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ]))
        return t

    for exercise_set in plan.exercise_sets.all():
        freq = exercise_set.get_frequency_display_text()
        label = exercise_set.name
        if freq:
            label += f"  --  wykonuj {freq}"
        elements.append(section_bar(label))
        elements.append(Spacer(1, 3 * mm))

        rows = [[
            Paragraph("<b>Cwiczenie</b>", style_header_cell),
            Paragraph("<b>Jak wykonac</b>", style_header_cell),
            Paragraph("<b>Ilosc</b>", style_header_cell),
        ]]
        for idx, pe in enumerate(exercise_set.plan_exercises.all(), start=1):
            rows.append([
                Paragraph(f"{idx}. {pe.exercise.name}", style_normal),
                Paragraph(pe.execution_text or '', style_normal),
                Paragraph(pe.reps_text or '', style_normal),
            ])

        table = Table(rows, colWidths=[54 * mm, 90 * mm, 30 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BBBBBB')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EFEFEF')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 5 * mm))

    if branding and branding.footer_text:
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph(f"<i>{branding.footer_text}</i>", style_subtitle))

    doc.build(elements)
    buf.seek(0)
    return buf


def generate_detailed_docx(plan, branding):
    doc = DocxDocument()
    font_name = branding.font_family if branding else 'Helvetica'
    docx_font = {'Helvetica': 'Arial', 'Times-Roman': 'Times New Roman', 'Courier': 'Courier New'}.get(font_name, 'Arial')

    style = doc.styles['Normal']
    style.font.name = docx_font
    style.font.size = Pt(10)

    primary_hex = branding.primary_color if branding else '#D9D9D9'
    text_rgb = _hex_to_rgbcolor(branding.text_color if branding else '#000000')

    name_upper, subtitle = _dog_header_text(plan.dog)

    header_table = doc.add_table(rows=1, cols=3)
    header_table.autofit = True
    cells = header_table.rows[0].cells

    if branding and branding.logo and os.path.exists(branding.logo.path):
        try:
            cells[0].paragraphs[0].add_run().add_picture(branding.logo.path, width=Cm(2.5))
        except Exception:
            pass

    p1 = cells[1].paragraphs[0]
    run1 = p1.add_run(name_upper)
    run1.bold = True
    run1.font.size = Pt(16)
    p1.add_run('\n' + subtitle).font.size = Pt(9)
    run_title = p1.add_run('\nSZCZEGOLOWY PLAN CWICZEN FITNESS')
    run_title.bold = True
    run_title.font.size = Pt(12)

    p2 = cells[2].paragraphs[0]
    p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p2.add_run('Data:\n').font.size = Pt(8)
    run_date = p2.add_run(date.today().strftime('%d.%m.%Y'))
    run_date.bold = True

    doc.add_paragraph()

    def add_section_bar(text):
        t = doc.add_table(rows=1, cols=1)
        cell = t.rows[0].cells[0]
        cell.text = text
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.color.rgb = text_rgb
        _set_docx_cell_background(cell, primary_hex)
        return t

    if plan.training_goal:
        add_section_bar("CEL TRENINGU")
        doc.add_paragraph(plan.training_goal)

    if plan.safety_rules:
        add_section_bar("WAZNE ZASADY I BEZPIECZENSTWO")
        for line in plan.safety_rules.split('\n'):
            if line.strip():
                doc.add_paragraph(line.strip(), style='List Bullet')

    for exercise_set in plan.exercise_sets.all():
        freq = exercise_set.get_frequency_display_text()
        label = exercise_set.name
        if freq:
            label += f"  --  wykonuj {freq}"
        add_section_bar(label)

        for idx, pe in enumerate(exercise_set.plan_exercises.all(), start=1):
            p = doc.add_paragraph()
            p.add_run(f"{idx}. {pe.exercise.name}").bold = True
            if pe.goal_text:
                para = doc.add_paragraph()
                para.add_run("Cel: ").bold = True
                para.add_run(pe.goal_text)
            if pe.execution_text:
                para = doc.add_paragraph()
                para.add_run("Wykonanie: ").bold = True
                para.add_run(pe.execution_text)
            if pe.reps_text:
                para = doc.add_paragraph()
                para.add_run("Powtorzenia: ").bold = True
                para.add_run(pe.reps_text)
            if pe.notes_text:
                para = doc.add_paragraph()
                para.add_run("Uwagi: ").bold = True
                para.add_run(pe.notes_text)

    if branding and branding.footer_text:
        doc.add_paragraph()
        footer_p = doc.add_paragraph()
        footer_run = footer_p.add_run(branding.footer_text)
        footer_run.italic = True
        footer_run.font.size = Pt(8)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def generate_fiszka_docx(plan, branding):
    doc = DocxDocument()
    font_name = branding.font_family if branding else 'Helvetica'
    docx_font = {'Helvetica': 'Arial', 'Times-Roman': 'Times New Roman', 'Courier': 'Courier New'}.get(font_name, 'Arial')

    style = doc.styles['Normal']
    style.font.name = docx_font
    style.font.size = Pt(10)

    primary_hex = branding.primary_color if branding else '#D9D9D9'
    text_rgb = _hex_to_rgbcolor(branding.text_color if branding else '#000000')

    name_upper, subtitle = _dog_header_text(plan.dog)

    header_table = doc.add_table(rows=1, cols=3)
    cells = header_table.rows[0].cells

    if branding and branding.logo and os.path.exists(branding.logo.path):
        try:
            cells[0].paragraphs[0].add_run().add_picture(branding.logo.path, width=Cm(2.5))
        except Exception:
            pass

    p1 = cells[1].paragraphs[0]
    run1 = p1.add_run(name_upper)
    run1.bold = True
    run1.font.size = Pt(16)
    p1.add_run('\n' + subtitle).font.size = Pt(9)
    run_title = p1.add_run('\nPLAN CWICZEN FITNESS')
    run_title.bold = True
    run_title.font.size = Pt(12)

    p2 = cells[2].paragraphs[0]
    p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p2.add_run('Data:\n').font.size = Pt(8)
    run_date = p2.add_run(date.today().strftime('%d.%m.%Y'))
    run_date.bold = True

    doc.add_paragraph()

    def add_section_bar(text):
        t = doc.add_table(rows=1, cols=1)
        cell = t.rows[0].cells[0]
        cell.text = text
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.color.rgb = text_rgb
        _set_docx_cell_background(cell, primary_hex)

    for exercise_set in plan.exercise_sets.all():
        freq = exercise_set.get_frequency_display_text()
        label = exercise_set.name
        if freq:
            label += f"  --  wykonuj {freq}"
        add_section_bar(label)

        table = doc.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        hdr = table.rows[0].cells
        hdr[0].text = 'Cwiczenie'
        hdr[1].text = 'Jak wykonac'
        hdr[2].text = 'Ilosc'
        for c in hdr:
            c.paragraphs[0].runs[0].bold = True

        for idx, pe in enumerate(exercise_set.plan_exercises.all(), start=1):
            row = table.add_row().cells
            row[0].text = f"{idx}. {pe.exercise.name}"
            row[1].text = pe.execution_text or ''
            row[2].text = pe.reps_text or ''

        doc.add_paragraph()

    if branding and branding.footer_text:
        footer_p = doc.add_paragraph()
        footer_run = footer_p.add_run(branding.footer_text)
        footer_run.italic = True
        footer_run.font.size = Pt(8)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
