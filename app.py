from flask import Flask, render_template, request, send_file
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

app = Flask(__name__)
TEMPLATE_PATH = "test_1_0.pdf"

# # 1. ReportLab용 한글 폰트 사전 등록 (윈도우 맑은 고딕 기준)
# FONT_PATH = "C:/Windows/Fonts/malgun.ttf"
# pdfmetrics.registerFont(TTFont("Malgun", FONT_PATH))

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "malgun.ttf")

@app.route('/')
@app.route('/apply')
def apply_form():
    prefill_data = {
        'company': request.args.get('company', ''),
        'name': request.args.get('name', ''),
        'email': request.args.get('email', '')
    }
    return render_template('index.html', prefill=prefill_data)



@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    form_data = request.form
    # checkbox 반응 반영하기 위한 method 정의하기 
    def get_checkbox_val(data, field_name):
        return 'V' if data.get(field_name) is not None else ''
    # 딕셔너리 구성 (기존과 동일)
    pdf_data = {
        "company name": form_data.get('company name', ''),
        "Representative Name": form_data.get('Representative Name', ''),
        "Address": form_data.get('Address', ''),
        "Business Registration Number": form_data.get('Business Registration Number', ''),
        "Corporate Registration Number": form_data.get('Corporate Registration Number', ''),
        "Business Type/Activity": form_data.get('Business Type/Activity', ''),
        "Name / Position": form_data.get('Name / Position', ''),
        "Mobile": form_data.get('Mobile', ''),
        "Tel": form_data.get('Tel', ''),
        "Mail": form_data.get('Mail', ''),

        # --- 산업 분야 (체크박스) ---
        "Traffic": get_checkbox_val(form_data, 'Traffic'),
        "Life": get_checkbox_val(form_data, 'Life'),
        "Manufacture": get_checkbox_val(form_data, 'Manufacture'),
        "Mobility_future": get_checkbox_val(form_data, 'Mobility_future'),
        "Military": get_checkbox_val(form_data, 'Military'),
        "Environment": get_checkbox_val(form_data, 'Environment'),
        "Agriculture": get_checkbox_val(form_data, 'Agriculture'),
        "ETC": get_checkbox_val(form_data, 'ETC'),
        
        # --- 활용 목적 ---
        "Purpose": form_data.get('Purpose', ''),

        # --- 서비스 이용기간 ---
        "1st year": form_data.get('1st year', ''),
        "1st month": form_data.get('1st month', ''),
        "1st day": form_data.get('1st day', ''),
        "2nd year": form_data.get('2nd year', ''),
        "2nd month": form_data.get('2nd month', ''),
        "2nd day": form_data.get('2nd day', ''),

        # --- 신청할 GPU 리스트 (체크박스) ---
        "H100 Number": form_data.get('H100 Number', ' '),
        "GPU 2 slice": form_data.get('GPU 2 slice', ' '),
        "GPU 3 slice": form_data.get('GPU 3 slice', ' '),
        "GPU 4 slice": form_data.get('GPU 4 slice', ' '),

        # --- 개인정보 수집 동의여부 (체크박스) ---
        "Agree_Collection": get_checkbox_val(form_data, 'Agree_Collection'),
        "Disgree_Collection": get_checkbox_val(form_data, 'Disgree_Collection'),

        # --- 하단 서명란 ---
        "Register Year": form_data.get('Register Year', ''),
        "Register Month": form_data.get('Register Month', ''), # 주의: PDF 폼 필드명이 'Register Month'가 맞는지 확인 필요
        "Register Day": form_data.get('Register Day', ''),
        "Application Business Name": form_data.get('Application Business Name', ''),
        "Corporate Representative Name": form_data.get('Corporate Representative Name', '')
    }

    # 원본 템플릿 열기
    doc = fitz.open(TEMPLATE_PATH)
    
    for page in doc:
        widgets = list(page.widgets())
        if not widgets:
            continue
            
        # ReportLab을 이용해 투명한 배경에 텍스트를 그릴 도화지 생성
        packet = io.BytesIO()
        width, height = page.rect.width, page.rect.height
        c = canvas.Canvas(packet, pagesize=(width, height))
        c.setFont("Malgun", 11) # 폰트 크기 지정
        
        for field in widgets:
            field_name = field.field_name
            
            if field_name in pdf_data and pdf_data[field_name]:
                # strip()을 추가해 ' ' 처럼 공백만 들어온 경우도 빈칸으로 처리
                val = str(pdf_data[field_name]).strip() 
                x0, y0, x1, y1 = field.rect
                
                box_width = x1 - x0
                box_height = y1 - y0
                
                if field.field_type == fitz.PDF_WIDGET_TYPE_TEXT:
                    # 값이 '0'이거나 빈칸이면 텍스트를 그리지 않음
                    if val != '0' and val != '': 
                        # 1. 폰트 자동 조절 로직
                        base_font_size = 11
                        padding = 8  # 좌우 여백 확보
                        available_width = box_width - padding
                        # 현재 폰트 크기에서의 텍스트 길이 계산
                        text_width = pdfmetrics.stringWidth(val, "Malgun", base_font_size)
                        # 텍스트가 박스보다 길면 비율에 맞춰 폰트 사이즈 축소   
                        if text_width > available_width and text_width > 0:
                            scale_factor = available_width / text_width
                            adjusted_font_size = max(5, int(base_font_size * scale_factor)) # 최소 5pt 보장
                        else:
                            adjusted_font_size = base_font_size

                        # 계산된 폰트 크기 적용 및 그리기
                        c.setFont("Malgun", adjusted_font_size)
                        
                        # Y축 중앙 정렬을 위한 베이스라인 미세 조정
                        y_baseline = height - y1 + (box_height - adjusted_font_size) / 2 + 1
                        c.drawString(x0 + 4, y_baseline, val)
                    
                # [체크박스/라디오버튼 처리]
                elif field.field_type in [fitz.PDF_WIDGET_TYPE_CHECKBOX, fitz.PDF_WIDGET_TYPE_RADIOBUTTON]:
                    # if val == '1': # 함수에서 체크된 값을 '1'로 치환했음
                    # '1'이 아닌 'V'인지 확인해야 함
                    if val == 'V':
                        c.setFont("Malgun", 11)
                        # 박스 정중앙 부근에 V 표시가 그려지도록 좌표 보정
                        c.drawString(x0 + 2, height - y1 + 2, "V")
                        
            # 렌더링 끝난 폼 필드 원본에서 삭제
            page.delete_widget(field)
                
        c.save()
        packet.seek(0)
        
        # ReportLab으로 만든 텍스트 레이어를 원본 PDF 위에 병합 (Overlay)
        overlay_doc = fitz.open("pdf", packet)
        page.show_pdf_page(page.rect, overlay_doc, 0)

    # 최종 결과물 반환
    output_pdf = io.BytesIO()
    doc.save(output_pdf)
    output_pdf.seek(0)
    doc.close()

    return send_file(
        output_pdf, 
        # 'companyname' -> 'company name' 으로 띄어쓰기 수정
        download_name=f"GPU가상자원이용신청서_{pdf_data.get('company name', '미상')}.pdf", 
        as_attachment=True
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
