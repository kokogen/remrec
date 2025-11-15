from dbox import list_folder, download_file, upload_file, delete_path, is_access_token_valid, refresh_dropbox_token, delete_file_if_exists, ACCESS_TOKEN
from recognition import image_to_base64, recognize

from pdf2image import convert_from_path
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import os

BUF_DIR = './buf/'
DEST_DIR = '/tmp/'
FONT_NAME = 'Arial' #'DejaVuSans.ttf'

def save_txt_file(fname, txt):
    with open(fname, 'w', encoding='utf-8') as file:
        file.write(txt)

def delete_file(file_path):
    try:
        os.remove(file_path)
        print(f"Файл {file_path} удалён.")
    except FileNotFoundError:
        print(f"Файл {file_path} не найден.")
    except PermissionError:
        print(f"Нет доступа к удалению файла {file_path}.")
    except Exception as e:
        print(f"Ошибка при удалении файла: {e}")

def txt_to_pdf_cyrillic(txt_path, pdf_path, font_path='DejaVuSans.ttf', margin_left=20*mm, margin_right=20*mm):
    if not os.path.isfile(font_path):
        raise FileNotFoundError(f"Шрифт {font_path} не найден. Скачайте DejaVuSans.ttf и укажите правильный путь.")

    pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))

    c = canvas.Canvas(pdf_path, pagesize=LETTER)
    width, height = LETTER

    c.setFont('DejaVuSans', 12)

    # Вычисляем доступную ширину с учётом полей
    usable_width = width - margin_left - margin_right

    with open(txt_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    y = height - 40  # старт по вертикали

    for line in lines:
        line = line.rstrip('\n')
        if y < 40:  # новая страница
            c.showPage()
            c.setFont('DejaVuSans', 12)
            y = height - 40
        # Чтобы ограничить ширину и переносить строки, можно использовать wrap (но для простоты выводим строку)
        c.drawString(margin_left, y, line)
        y -= 15

    c.save()

def txt_to_pdf_with_wrapped_text(txt_path, pdf_path, font_path='DejaVuSans.ttf',
                                 margin_left=20 * mm, margin_right=20 * mm,
                                 margin_top=20 * mm, margin_bottom=20 * mm):
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase import pdfmetrics

    # Проверка и регистрация шрифта
    if not os.path.isfile(font_path):
        raise FileNotFoundError(f"Шрифт {font_path} не найден. Скачайте DejaVuSans.ttf и укажите правильный путь.")
    pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))

    # Создаем документ с нужными полями
    doc = SimpleDocTemplate(pdf_path,
                            pagesize=LETTER,
                            leftMargin=margin_left,
                            rightMargin=margin_right,
                            topMargin=margin_top,
                            bottomMargin=margin_bottom)

    # Получаем базовые стили и создаем стиль с нашим шрифтом
    styles = getSampleStyleSheet()
    styleN = styles['Normal']
    styleN.fontName = 'DejaVuSans'
    styleN.fontSize = 12
    styleN.leading = 15  # высота строки

    # Читаем весь текст и создаем параграфы с переносами
    with open(txt_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Разбиваем на абзацы по двойному переносу строки, чтобы сохранить структуру
    paragraphs = text.split('\n\n')

    flowables = []
    for para in paragraphs:
        # Убираем лишние пробелы и переносы
        clean_para = para.strip().replace('\n', ' ')
        if clean_para:
            flowables.append(Paragraph(clean_para, styleN))
            flowables.append(Spacer(1, 12))  # Отступ между абзацами

    # Строим PDF
    doc.build(flowables)
    print(f"PDF создан с переносом строк: {pdf_path}")

def txt_to_pdf_line_by_line(txt_path, pdf_path, font_path='DejaVuSans.ttf',
                          margin_left=20 * mm, margin_right=20 * mm,
                          margin_top=20 * mm, margin_bottom=20 * mm):
    # Проверка и регистрация шрифта
    if not os.path.isfile(font_path):
        raise FileNotFoundError(f"Шрифт {font_path} не найден. Скачайте DejaVuSans.ttf и укажите правильный путь.")
    pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))

    # Настройки документа с полями
    doc = SimpleDocTemplate(pdf_path,
                            pagesize=LETTER,
                            leftMargin=margin_left,
                            rightMargin=margin_right,
                            topMargin=margin_top,
                            bottomMargin=margin_bottom)

    # Стиль для каждой строки
    style = ParagraphStyle(
        name='LineStyle',
        fontName='DejaVuSans',
        fontSize=12,
        leading=15,
        spaceAfter=0,
        spaceBefore=0,
    )

    flowables = []

    with open(txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            clean_line = line.strip('\n').strip('\r')
            # Даже если строка пустая, добавляем пустой параграф для переноса
            flowables.append(Paragraph(clean_line if clean_line else '\n', style))

    doc.build(flowables)
    print(f"PDF создан с переносом строк и новой строкой для каждой строки текста: {pdf_path}")


def process_file(input_path, output_path):
    if input_path.lower().endswith(".pdf"):
        
        pages = convert_from_path(input_path, dpi=300)

        recognized_texts = []
        for i, page in enumerate(pages):
            img_b64 = image_to_base64(page)
            text = recognize(img_b64)
            text = f"Страница {i+1}:\n{text}\n"
            recognized_texts.append(text)

        full_text = "\n".join(recognized_texts)
        save_txt_file(output_path+'.txt', full_text)
    else:
        with open(input_path, "rb") as f:
            img_b64 = image_to_base64(f.read())
        text = recognize(img_b64)
        save_txt_file(output_path+'.txt', text)
    
    txt_to_pdf_line_by_line(output_path+'.txt', output_path)
    delete_file(output_path+'.txt')

def main():
    if not is_access_token_valid():
        print("Токен устарел, сейчас буду запрашивать новый...")
        ACCESS_TOKEN = refresh_dropbox_token()

    entries = list_folder()
    for entry in entries:
        if entry['tag'] == 'file':
            if entry['name'].lower().endswith(".pdf"):
                fname_db = '/'+entry['name']
                fname = BUF_DIR + entry['name']
                download_file(fname_db, fname)
                process_file(fname, fname+'-txt.pdf')

                delete_file_if_exists(DEST_DIR+entry['name']+'-txt.pdf')
                upload_file(fname+'-txt.pdf', DEST_DIR+entry['name']+'-txt.pdf')
                delete_path(fname_db)
                delete_file(fname)
                delete_file(fname+'-txt.pdf')

if __name__ == "__main__":
    main()