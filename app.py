from flask import Flask, render_template, request, send_file
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
import re  # 정규표현식(형식 검사용) 모듈 추가

app = Flask(__name__)
TEMPLATE_PATH = "test_1_0.pdf"

# [폰트 설정] 프리텐다드 볼드 폰트 경로 등록 및 불러오기
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "Pretendard-Bold.ttf")
pdfmetrics.registerFont(TTFont("Pretendard", FONT_PATH))

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

    # =================================================================
    # [데이터 형식 검사 (Validation) 구역]
    # 유저가 입력한 필수 민감 정보들의 규격을 검증하여 에러를 사전에 차단합니다.
    # =================================================================
    email = form_data.get('Mail', '').strip()
    mobile = form_data.get('Mobile', '').strip()
    biz_reg_num = form_data.get('Business Registration Number', '').strip()
    corp_reg_num = form_data.get('Corporate Registration Number', '').strip()

    # 1. 이메일 형식 검사
    if email and not re.match(r'^[a-zA-Z0-9+-_.]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
        return "오류: 올바른 이메일 형식이 아닙니다. (예: user@example.com)", 400

    # 2. 휴대전화 형식 검사 (하이픈 필수 포함)
    if mobile and not re.match(r'^01[016789]-\d{3,4}-\d{4}$', mobile):
        return "오류: 올바른 휴대전화 번호 형식이 아닙니다. 하이픈(-)을 포함해주세요. (예: 010-1234-5678)", 400

    # 3. 사업자등록번호 형식 검사 (3자리-2자리-5자리)
    if biz_reg_num and not re.match(r'^\d{3}-\d{2}-\d{5}$', biz_reg_num):
        return "오류: 올바른 사업자등록번호 형식이 아닙니다. 하이픈(-)을 포함해주세요. (예: 123-45-67890)", 400
    
    # 4. 법인등록번호 형식 검사 (6자리-7자리)
    if corp_reg_num and not re.match(r'^\d{6}-\d{7}$', corp_reg_num):
        return "오류: 올바른 법인등록번호 형식이 아닙니다. 하이픈(-)을 포함해주세요. (예: 123456-1234567)", 400
    # =================================================================

    def get_checkbox_val(data, field_name):
        return 'V' if data.get(field_name) is not None else ''
        
    # 딕셔너리 구성 (검증된 데이터 반영)
    pdf_data = {
        "company name": form_data.get('company name', ''),
        "Representative Name": form_data.get('Representative Name', ''),
        "Address": form_data.get('Address', ''),
        "Business Registration Number": biz_reg_num,
        "Corporate Registration Number": corp_reg_num,
        "Business Type/Activity": form_data.get('Business Type/Activity', ''),
        "Name / Position": form_data.get('Name / Position', ''),
        "Mobile": mobile,
        "Tel": form_data.get('Tel', ''),
        "Mail": email,

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
        "Register Month": form_data.get('Register Month', ''),
        "Register Day": form_data.get('Register Day', ''),
        "Application Business Name": form_data.get('Application Business Name', ''),
        "Corporate Representative Name": form_data.get('Corporate Representative Name', '')
    }

    doc = fitz.open(TEMPLATE_PATH)
    
    for page in doc:
        widgets = list(page.widgets())
        if not widgets:
            continue
            
        packet = io.BytesIO()
        width, height = page.rect.width, page.rect.height
        c = canvas.Canvas(packet, pagesize=(width, height))
        
        for field in widgets:
            field_name = field.field_name
            
            if field_name in pdf_data and pdf_data[field_name]:
                val = str(pdf_data[field_name]).strip() 
                x0, y0, x1, y1 = field.rect
                
                box_width = x1 - x0
                box_height = y1 - y0
                
                if field.field_type == fitz.PDF_WIDGET_TYPE_TEXT:
                    if val != '0' and val != '': 
                        base_font_size = 11
                        padding = 4  
                        available_width = box_width - padding
                        
                        # 크기 계산 시 Pretendard 적용
                        text_width = pdfmetrics.stringWidth(val, "Pretendard", base_font_size)
                        
                        if text_width > available_width and text_width > 0:
                            scale_factor = available_width / text_width
                            adjusted_font_size = max(5, int(base_font_size * scale_factor))
                        else:
                            adjusted_font_size = base_font_size
                            
                        c.setFont("Pretendard", adjusted_font_size)
                        
                        # [텍스트 Y축 중앙 정렬]
                        y_baseline = height - y1 + (box_height / 2) - (adjusted_font_size / 3)
                        c.drawString(x0 + 2, y_baseline, val)

                elif field.field_type in [fitz.PDF_WIDGET_TYPE_CHECKBOX, fitz.PDF_WIDGET_TYPE_RADIOBUTTON]:
                    if val == 'V':
                        c.setFont("Pretendard", 11)
                        
                        # [체크박스 정중앙 정밀 좌표 계산]
                        center_x = x0 + (box_width / 2)
                        center_y = height - y1 + (box_height / 2) - 3.5  
                        
                        c.drawCentredString(center_x, center_y, "V")
                        
            # 렌더링 끝난 폼 필드는 원본 문서에서 정적으로 삭제 (박제)
            page.delete_widget(field)
                
        c.save()
        packet.seek(0)
        
        # [핵심 수정] 최신 PyMuPDF 호환을 위해 packet 객체 대신 packet.getvalue() 바이트 전달 (500 에러 해결)
        overlay_doc = fitz.open("pdf", packet.getvalue())
        page.show_pdf_page(page.rect, overlay_doc, 0)

    # 최종 결과물 반환
    output_pdf = io.BytesIO()
    doc.save(output_pdf)
    output_pdf.seek(0)
    doc.close()

    return send_file(
        output_pdf, 
        download_name=f"GPU가상자원이용신청서_{pdf_data.get('company name', '미상')}.pdf", 
        as_attachment=True
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
