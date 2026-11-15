"""Render the Markdown reports and literature appendix as searchable PDFs."""
import re
from html import escape
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, Preformatted

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path('/System/Library/Fonts/Supplemental')
if not (FONT_DIR / 'Arial.ttf').exists():
    FONT_DIR = Path('/usr/share/fonts/truetype/dejavu')
    font_files = ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf')
else:
    font_files = ('Arial.ttf', 'Arial Bold.ttf')
for name, filename in zip(['Body', 'BodyBold'], font_files):
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / filename)))
pdfmetrics.registerFontFamily('Body', normal='Body', bold='BodyBold', italic='Body', boldItalic='BodyBold')
styles = {
    'body': ParagraphStyle('Body', fontName='Body', fontSize=10.5, leading=15, spaceAfter=9),
    'h1': ParagraphStyle('H1', fontName='BodyBold', fontSize=24, leading=29, spaceAfter=17, textColor=colors.HexColor('#173448')),
    'h2': ParagraphStyle('H2', fontName='BodyBold', fontSize=16, leading=21, spaceAfter=13, textColor=colors.HexColor('#173448')),
    'h3': ParagraphStyle('H3', fontName='BodyBold', fontSize=12.5, leading=17, spaceBefore=7, spaceAfter=10, textColor=colors.HexColor('#173448')),
    'table': ParagraphStyle('Table', fontName='Body', fontSize=8.2, leading=11, spaceAfter=0, wordWrap='CJK'),
    'code': ParagraphStyle('Code', fontName='Body', fontSize=8, leading=11, spaceAfter=1),
}


def inline(text):
    text = escape(text)
    text = text.replace('₀', '<sub>0</sub>').replace('₁', '<sub>1</sub>')
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'`([^`]+)`', r'<font color="#126e82">\1</font>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<link href="\2" color="#126e82">\1</link>', text)
    return text


def parse(text):
    story = []
    lines = text.splitlines(); i=0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1; continue
        if line == '<!-- pagebreak -->':
            story.append(PageBreak()); i += 1; continue
        if line.startswith('```'):
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                story.append(Paragraph(escape(lines[i]).replace(' ', '&nbsp;'), styles['code'])); i += 1
            story.append(Spacer(1, 10)); i += 1; continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                cells=[c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', c) for c in cells):
                    rows.append([Paragraph(inline(c), styles['table']) for c in cells])
                i+=1
            n=len(rows[0]); width=A4[0]-100
            widths=[width*.27, width*.73] if n==2 else [width/n]*n
            table=Table(rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e1edf1')),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f8fa')]),
                ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),
                ('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#9bb1bd')),
            ]))
            story += [table,Spacer(1,12)];continue
        match=re.match(r'!\[([^\]]*)\]\(([^)]+)\)',line)
        if match:
            p=ROOT / 'docs' / match.group(2)
            img=Image(str(p)); ratio=min((A4[0]-100)/img.imageWidth, 285/img.imageHeight)
            img.drawWidth=img.imageWidth*ratio;img.drawHeight=img.imageHeight*ratio
            story += [img,Paragraph(inline(match.group(1)),styles['table']),Spacer(1,12)];i+=1;continue
        if line.startswith('#'):
            level=len(line)-len(line.lstrip('#'))
            story.append(Paragraph(inline(line[level:].strip()),styles['h'+str(min(3,level))]));i+=1;continue
        paragraph=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```','<!--','![')):
            paragraph.append(lines[i].strip());i+=1
        story.append(Paragraph(inline(' '.join(paragraph)), styles['body']))
    return story


def footer(canvas, doc):
    canvas.setStrokeColor(colors.HexColor('#d8e3e9'));canvas.line(50,40,A4[0]-50,40)
    canvas.setFont('Body',8);canvas.setFillColor(colors.HexColor('#52636f'))
    canvas.drawString(50,27,'Deskhand · Экспериментальный стенд · 2026')
    canvas.drawRightString(A4[0]-50,27,str(doc.page))


def main():
    dest=ROOT/'output/pdf';dest.mkdir(parents=True,exist_ok=True)
    for name in ['pr3','pr4']:
        text=(ROOT/f'docs/{name}-report.md').read_text()
        if name=='pr3':text+='\n'+(ROOT/'docs/literature.md').read_text()
        doc=SimpleDocTemplate(str(dest/f'{name}-deskhand.pdf'),pagesize=A4,
                             rightMargin=50,leftMargin=50,topMargin=45,bottomMargin=53,
                             title=f'{name.upper()}: экспериментальный стенд Deskhand',author='Александр Бобрусь')
        doc.build(parse(text),onFirstPage=footer,onLaterPages=footer)
        print(dest/f'{name}-deskhand.pdf')


if __name__=='__main__':main()
