"""Optional static illustration of docs/architecture.mmd for the PDF report."""
from pathlib import Path
import math
import pymupdf
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from scripts.build_reports import FONT_DIR, font_files
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def main():
    Path('tmp/pdfs').mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(TTFont('Diagram', str(FONT_DIR / font_files[0])))
    c = canvas.Canvas('tmp/pdfs/architecture.pdf', pagesize=(900, 450))
    c.setFillColor(colors.white); c.rect(0, 0, 900, 450, fill=1, stroke=0)
    def box(x,y,w,h,lines):
        c.setFillColor(colors.HexColor('#eef5f7')); c.setStrokeColor(colors.HexColor('#98b7c1'))
        c.roundRect(x,y,w,h,8,fill=1,stroke=1)
        c.setFillColor(colors.HexColor('#173448')); c.setFont('Diagram',12)
        for i,line in enumerate(lines): c.drawCentredString(x+w/2,y+h/2+(len(lines)-1)*8-i*16,line)
    def arrow(x,y,x2,y2):
        c.setStrokeColor(colors.HexColor('#126e82')); c.setLineWidth(1.6); c.line(x,y,x2,y2)
        angle=math.atan2(y2-y,x2-x)
        for d in [-.5,.5]: c.line(x2,y2,x2-8*math.cos(angle+d),y2-8*math.sin(angle+d))
    c.setFont('Diagram',15); c.setFillColor(colors.HexColor('#173448'))
    c.drawString(30,420,'Deskhand: компонентный эксперимент')
    c.setDash(4,3); c.setStrokeColor(colors.HexColor('#98b7c1'))
    c.roundRect(280,145,590,240,10,fill=0,stroke=1); c.setDash()
    c.setFont('Diagram',11); c.drawString(300,362,'Docker bench · 2 CPU · 1 GiB · без сети')
    box(30,260,205,70,['JSON-конфигурация','факторы + seeds'])
    box(310,260,230,70,['Генератор + раннер','готовый вход до замера'])
    box(605,260,230,70,['Новый процесс SUT','full / bounded'])
    box(605,165,230,60,['Таймер + байты','проверка инвариантов'])
    box(310,165,230,60,['JSON каждого прогона','данные + manifest'])
    box(310,35,230,70,['Docker analysis','bootstrap · sign-flip · Holm'])
    box(605,35,230,70,['Таблицы и графики','архив SHA-256'])
    box(30,165,205,60,['Swift-фрагмент','эталон для Python'])
    for coords in [(235,295,310,295),(540,295,605,295),(720,260,720,225),(605,195,540,195),(425,165,425,105),(540,70,605,70)]: arrow(*coords)
    c.setDash(3,3); c.line(235,195,260,195); c.line(260,195,260,345); c.line(260,345,720,345); arrow(720,345,720,330); c.setDash()
    c.setFont('Diagram',9); c.drawString(32,140,'103 дифференциальных случая')
    c.save()
    pdf=pymupdf.open('tmp/pdfs/architecture.pdf')
    pdf[0].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save('docs/figures/architecture.png')


if __name__ == '__main__': main()
