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
    # [백엔드 데이터 형식 검사 구역] - 프론트엔드 우회 시 작동하는 최후의 보루
    # =================================================================
    email = form_data.get('Mail', '').strip()
    mobile = form_data.get('Mobile', '').strip()
    biz_reg_num = form_data.get('Business Registration Number', '').strip()
    corp_reg_num = form_data.get('Corporate Registration Number', '').strip()
    
    # 엣지 케이스: 필수값이 빠져있을 경우 차단
    company_name = form_data.get('company name', '').strip()
    rep_name = form_data.get('Representative Name', '').strip()
    if not company_name or not rep_name:
        return "오류: 기업명과 대표자 성명은 필수 입력 항목입니다.", 400

    if email and not re.match(r'^[a-zA-Z0-9+-_.]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
        return "오류: 올바른 이메일 형식이 아닙니다.", 400
    if mobile and not re.match(r'^01[016789]-\d{3,4}-\d{4}$', mobile):
        return "오류: 올바른 휴대전화 번호 형식이 아닙니다. 하이픈(-)을 포함해주세요.", 400
    if biz_reg_num and not re.match(r'^\d{3}-\d{2}-\d{5}$', biz_reg_num):
        return "오류: 올바른 사업자등록번호 형식이 아닙니다. 하이픈(-)을 포함해주세요.", 400
    if corp_reg_num and not re.match(r'^\d{6}-\d{7}$', corp_reg_num):
        return "오류: 올바른 법인등록번호 형식이 아닙니다. 하이픈(-)을 포함해주세요.", 400

    # =================================================================

    def get_checkbox_val(data, field_name):
        return 'V' if data.get(field_name) is not None else ''
        
    # 라디오 버튼(개인정보 동의) 데이터 처리 엣지케이스 대응
    agreement = form_data.get('Collection_Agreement')
    agree_val = 'V' if agreement == 'Agree' else ''
    disagree_val = 'V' if agreement == 'Disagree' else ''

    # 딕셔너리 구성 (검증된 데이터 및 기본값 0 반영)
    pdf_data = {
        "company name": company_name,
        "Representative Name": rep_name,
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
        
        "Purpose": form_data.get('Purpose', ''),

        "1st year": form_data.get('1st year', ''),
        "1st month": form_data.get('1st month', ''),
        "1st day": form_data.get('1st day', ''),
        "2nd year": form_data.get('2nd year', ''),
        "2nd month": form_data.get('2nd month', ''),
        "2nd day": form_data.get('2nd day', ''),

        # 엣지 케이스: 빈 값으로 제출 시 강제로 '0' 매핑하여 에러 방지
        "H100 Number": form_data.get('H100 Number', '').strip() or '0',
        "GPU 2 slice": form_data.get('GPU 2 slice', '').strip() or '0',
        "GPU 3 slice": form_data.get('GPU 3 slice', '').strip() or '0',
        "GPU 4 slice": form_data.get('GPU 4 slice', '').strip() or '0',

        # 처리된 라디오 버튼 변수 적용
        "Agree_Collection": agree_val,
        "Disgree_Collection": disagree_val,

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
                        
                        text_width = pdfmetrics.stringWidth(val, "Pretendard", base_font_size)
                        
                        if text_width > available_width and text_width > 0:
                            scale_factor = available_width / text_width
                            adjusted_font_size = max(5, int(base_font_size * scale_factor))
                        else:
                            adjusted_font_size = base_font_size
                            
                        c.setFont("Pretendard", adjusted_font_size)
                        
                        y_baseline = height - y1 + (box_height / 2) - (adjusted_font_size / 3)
                        c.drawString(x0 + 2, y_baseline, val)

                elif field.field_type in [fitz.PDF_WIDGET_TYPE_CHECKBOX, fitz.PDF_WIDGET_TYPE_RADIOBUTTON]:
                    if val == 'V':
                        c.setFont("Pretendard", 11)
                        
                        center_x = x0 + (box_width / 2)
                        center_y = height - y1 + (box_height / 2) - 3.5  
                        
                        c.drawCentredString(center_x, center_y, "V")
                        
            page.delete_widget(field)
                
        c.save()
        packet.seek(0)
        
        overlay_doc = fitz.open("pdf", packet.getvalue())
        page.show_pdf_page(page.rect, overlay_doc, 0)

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
