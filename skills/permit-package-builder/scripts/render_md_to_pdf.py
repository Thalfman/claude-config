"""
Render permit-package markdown deliverables to professional PDFs using reportlab.

Handles a focused subset of CommonMark: headings (##/###/####), paragraphs,
bullet lists, numbered lists, pipe tables, fenced code blocks, blockquotes,
horizontal rules, bold (**), italic (*), inline code (`), and links [text](url).

Usage:
    python render_md_to_pdf.py <input.md> <output.pdf> [--cover-letter]

The --cover-letter flag adds the MasTec letterhead block at the top.
"""
from __future__ import annotations
import argparse
import html
import os
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable, ListFlowable, ListItem,
)


# --- Styles ---------------------------------------------------------------

def make_styles():
    base = getSampleStyleSheet()
    styles = {}
    styles['title'] = ParagraphStyle(
        'title', parent=base['Heading1'],
        fontName='Helvetica-Bold', fontSize=18, leading=22,
        spaceBefore=2, spaceAfter=10, textColor=colors.HexColor('#0a3d6b'),
    )
    styles['h1'] = ParagraphStyle(
        'h1', parent=base['Heading1'],
        fontName='Helvetica-Bold', fontSize=15, leading=19,
        spaceBefore=14, spaceAfter=6, textColor=colors.HexColor('#0a3d6b'),
        keepWithNext=1,
    )
    styles['h2'] = ParagraphStyle(
        'h2', parent=base['Heading2'],
        fontName='Helvetica-Bold', fontSize=12.5, leading=16,
        spaceBefore=10, spaceAfter=4, textColor=colors.HexColor('#1f558e'),
        keepWithNext=1,
    )
    styles['h3'] = ParagraphStyle(
        'h3', parent=base['Heading3'],
        fontName='Helvetica-Bold', fontSize=11, leading=14,
        spaceBefore=8, spaceAfter=3, textColor=colors.HexColor('#444444'),
        keepWithNext=1,
    )
    styles['h4'] = ParagraphStyle(
        'h4', parent=base['Heading4'],
        fontName='Helvetica-Bold', fontSize=10, leading=13,
        spaceBefore=6, spaceAfter=2, textColor=colors.HexColor('#444444'),
        keepWithNext=1,
    )
    styles['body'] = ParagraphStyle(
        'body', parent=base['BodyText'],
        fontName='Helvetica', fontSize=9.5, leading=13,
        spaceBefore=0, spaceAfter=4,
        alignment=0,  # left
    )
    styles['bullet'] = ParagraphStyle(
        'bullet', parent=base['BodyText'],
        fontName='Helvetica', fontSize=9.5, leading=13,
        leftIndent=18, bulletIndent=6, spaceBefore=0, spaceAfter=2,
    )
    styles['quote'] = ParagraphStyle(
        'quote', parent=base['BodyText'],
        fontName='Helvetica-Oblique', fontSize=9.5, leading=13,
        leftIndent=18, rightIndent=18, spaceBefore=4, spaceAfter=4,
        textColor=colors.HexColor('#444444'),
        borderColor=colors.HexColor('#999999'), borderWidth=0,
        borderPadding=2, backColor=colors.HexColor('#f4f4f4'),
    )
    styles['code'] = ParagraphStyle(
        'code', parent=base['Code'],
        fontName='Courier', fontSize=8.5, leading=11,
        leftIndent=12, rightIndent=12, spaceBefore=4, spaceAfter=4,
        backColor=colors.HexColor('#f4f4f4'),
        borderColor=colors.HexColor('#cccccc'), borderWidth=0.5,
        borderPadding=4,
    )
    styles['letterhead_company'] = ParagraphStyle(
        'lh1', parent=base['Heading1'],
        fontName='Helvetica-Bold', fontSize=18, leading=22,
        spaceAfter=2, alignment=0, textColor=colors.HexColor('#0a3d6b'),
    )
    styles['letterhead_tag'] = ParagraphStyle(
        'lh2', parent=base['BodyText'],
        fontName='Helvetica', fontSize=9, leading=11,
        spaceAfter=0, alignment=0, textColor=colors.HexColor('#666666'),
    )
    return styles


# --- Inline markdown -> reportlab markup ----------------------------------

def render_inline(text: str) -> str:
    """Convert markdown inline syntax to reportlab Paragraph markup."""
    # Escape HTML special characters first
    text = html.escape(text, quote=False)
    # Inline code: `code` -> <font face="Courier">code</font>
    text = re.sub(r'`([^`]+)`',
                  lambda m: f'<font face="Courier" size="9" color="#444444">{m.group(1)}</font>',
                  text)
    # Bold: **text** -> <b>text</b>
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    # Italic: *text* (not **)
    text = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<i>\1</i>', text)
    # Links: [text](url) -> <link href="url"><u>text</u></link>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                  lambda m: f'<link href="{m.group(2)}" color="#0a3d6b"><u>{m.group(1)}</u></link>',
                  text)
    return text


# --- Block parser ---------------------------------------------------------

def parse_markdown(md: str):
    """Yield (block_type, payload) tuples."""
    lines = md.replace('\r\n', '\n').split('\n')
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.rstrip()

        # Skip blank
        if not stripped:
            i += 1
            continue

        # HTML comment block (often template comments) — skip until end
        if stripped.startswith('<!--'):
            while i < n and '-->' not in lines[i]:
                i += 1
            i += 1
            continue

        # Horizontal rule
        if re.match(r'^-{3,}\s*$', stripped) or re.match(r'^\*{3,}\s*$', stripped):
            yield ('hr', None)
            i += 1
            continue

        # Headings
        m = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if m:
            yield ('h' + str(len(m.group(1))), m.group(2))
            i += 1
            continue

        # Fenced code block
        if stripped.startswith('```'):
            i += 1
            buf = []
            while i < n and not lines[i].rstrip().startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            yield ('code', '\n'.join(buf))
            continue

        # Block quote
        if stripped.startswith('>'):
            buf = []
            while i < n and lines[i].lstrip().startswith('>'):
                buf.append(re.sub(r'^\s*>\s?', '', lines[i]))
                i += 1
            yield ('quote', '\n'.join(buf).strip())
            continue

        # Pipe table
        if '|' in stripped:
            # Detect: this row + next row is separator
            if i + 1 < n and re.match(r'^\s*\|?\s*[:\-|\s]+\|?\s*$', lines[i+1]) and '|' in lines[i+1]:
                rows = [stripped]
                i += 1
                # skip separator row
                i += 1
                while i < n and '|' in lines[i] and lines[i].strip():
                    rows.append(lines[i].rstrip())
                    i += 1
                yield ('table', rows)
                continue

        # Bullet list
        if re.match(r'^\s*[-*+]\s+', stripped):
            items = []
            while i < n and re.match(r'^\s*[-*+]\s+', lines[i].rstrip()):
                items.append(re.sub(r'^\s*[-*+]\s+', '', lines[i].rstrip()))
                i += 1
            yield ('bullet_list', items)
            continue

        # Numbered list
        if re.match(r'^\s*\d+\.\s+', stripped):
            items = []
            while i < n and re.match(r'^\s*\d+\.\s+', lines[i].rstrip()):
                items.append(re.sub(r'^\s*\d+\.\s+', '', lines[i].rstrip()))
                i += 1
            yield ('number_list', items)
            continue

        # Paragraph: collect until blank line or special block start.
        # Preserve newlines as hard line breaks (rendered <br/>), so letter
        # address blocks and signature blocks keep their formatting.
        buf = [stripped]
        i += 1
        while i < n:
            nxt = lines[i].rstrip()
            if not nxt:
                break
            if re.match(r'^#{1,6}\s', nxt): break
            if nxt.startswith('```'): break
            if nxt.startswith('>'): break
            if re.match(r'^\s*[-*+]\s+', nxt): break
            if re.match(r'^\s*\d+\.\s+', nxt): break
            if re.match(r'^-{3,}\s*$', nxt): break
            # Detect table start: this and next line both have | and next is separator
            if '|' in nxt and i + 1 < n and re.match(r'^\s*\|?\s*[:\-|\s]+\|?\s*$', lines[i+1]) and '|' in lines[i+1]:
                break
            buf.append(nxt)
            i += 1
        # Join with literal '<br/>' so the paragraph renderer can apply
        # render_inline() and still produce hard line breaks.
        yield ('paragraph', '\n'.join(buf))


# --- Render to flowables --------------------------------------------------

def parse_table_row(row: str):
    """Split a pipe row into cells, stripping outer pipes and whitespace."""
    s = row.strip()
    if s.startswith('|'): s = s[1:]
    if s.endswith('|'): s = s[:-1]
    return [c.strip() for c in s.split('|')]


def make_table(rows, styles, page_width):
    cells = [parse_table_row(r) for r in rows]
    if not cells: return None
    n_cols = max(len(r) for r in cells)
    # pad rows
    cells = [r + [''] * (n_cols - len(r)) for r in cells]
    # Wrap cell content in Paragraph
    cell_style = ParagraphStyle('cell', parent=styles['body'], fontSize=8.5, leading=11, spaceBefore=0, spaceAfter=0)
    header_style = ParagraphStyle('cell_h', parent=cell_style, fontName='Helvetica-Bold', textColor=colors.white)
    data = []
    for ri, row in enumerate(cells):
        st = header_style if ri == 0 else cell_style
        data.append([Paragraph(render_inline(c), st) for c in row])
    # Equal column widths
    col_w = page_width / n_cols
    t = Table(data, colWidths=[col_w] * n_cols, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f558e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f4f6fa')]),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return t


def md_to_flowables(md: str, styles, page_width: float, cover_letter: bool = False):
    flow = []
    if cover_letter:
        # MasTec letterhead block
        flow.append(Paragraph('MasTec Communications Group', styles['letterhead_company']))
        flow.append(Paragraph('1800 Johnson Street, Elkhart, IN 46514 &nbsp;|&nbsp; outside-plant network construction',
                              styles['letterhead_tag']))
        flow.append(HRFlowable(width='100%', thickness=1.5, color=colors.HexColor('#0a3d6b'),
                               spaceBefore=2, spaceAfter=10))
    for kind, payload in parse_markdown(md):
        if kind == 'hr':
            flow.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#cccccc'),
                                   spaceBefore=4, spaceAfter=4))
        elif kind in ('h1', 'h2', 'h3', 'h4'):
            flow.append(Paragraph(render_inline(payload), styles[kind]))
        elif kind == 'paragraph':
            # Strip the "[MasTec letterhead — header block]" placeholder line
            if '[MasTec' in payload and 'letterhead' in payload.lower() and cover_letter:
                continue
            # Render newlines as hard breaks
            inline = render_inline(payload).replace('\n', '<br/>')
            flow.append(Paragraph(inline, styles['body']))
        elif kind == 'quote':
            flow.append(Paragraph(render_inline(payload), styles['quote']))
        elif kind == 'code':
            # Render code preserving newlines
            esc = html.escape(payload).replace('\n', '<br/>')
            flow.append(Paragraph(esc, styles['code']))
        elif kind == 'bullet_list':
            items = [ListItem(Paragraph(render_inline(it), styles['body']),
                              leftIndent=12, value='disc') for it in payload]
            flow.append(ListFlowable(items, bulletType='bullet', start='disc',
                                     leftIndent=18, bulletFontSize=9))
        elif kind == 'number_list':
            items = [ListItem(Paragraph(render_inline(it), styles['body']),
                              leftIndent=12) for it in payload]
            flow.append(ListFlowable(items, bulletType='1', start=1,
                                     leftIndent=18, bulletFontSize=9))
        elif kind == 'table':
            t = make_table(payload, styles, page_width)
            if t is not None:
                flow.append(Spacer(0, 4))
                flow.append(t)
                flow.append(Spacer(0, 6))
    return flow


# --- Page footer ----------------------------------------------------------

def make_footer(jb_number: str, entity: str, doc_title: str):
    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(colors.HexColor('#888888'))
        line = f'{jb_number} | {entity} | {doc_title}'
        canvas.drawString(0.6 * inch, 0.4 * inch, line)
        canvas.drawRightString(LETTER[0] - 0.6 * inch, 0.4 * inch,
                               f'Page {doc.page}')
        canvas.restoreState()
    return _footer


# --- Main -----------------------------------------------------------------

def render(input_md: Path, output_pdf: Path, cover_letter: bool = False,
           jb_number: str = '', entity: str = '', doc_title: str = ''):
    # Try utf-8 first (the standard for skill outputs); fall back to cp1252
    # for files written by Windows tools (notepad, Word save-as) that use
    # the system codepage.
    try:
        md = input_md.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        md = input_md.read_text(encoding='cp1252')
    styles = make_styles()
    margin = 0.75 * inch
    page_w = LETTER[0] - 2 * margin
    flow = md_to_flowables(md, styles, page_w, cover_letter=cover_letter)
    doc = SimpleDocTemplate(
        str(output_pdf), pagesize=LETTER,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin + 0.15 * inch,
        title=doc_title or input_md.stem, author='MasTec Communications Group',
    )
    footer = make_footer(jb_number or 'JB0002479252', entity or '', doc_title or input_md.stem)
    doc.build(flow, onFirstPage=footer, onLaterPages=footer)


def parse_args():
    p = argparse.ArgumentParser(description='Render markdown to PDF for permit packages')
    p.add_argument('input_md', type=Path)
    p.add_argument('output_pdf', type=Path)
    p.add_argument('--cover-letter', action='store_true')
    p.add_argument('--jb', default='JB0002479252')
    p.add_argument('--entity', default='')
    p.add_argument('--title', default='')
    return p.parse_args()


def main():
    args = parse_args()
    render(args.input_md, args.output_pdf,
           cover_letter=args.cover_letter,
           jb_number=args.jb, entity=args.entity, doc_title=args.title)
    print(f'Rendered: {args.output_pdf}')


if __name__ == '__main__':
    main()
