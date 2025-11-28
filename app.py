from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from PIL import Image
import os
import io
import zipfile
import re
from pdf2image import convert_from_bytes

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Flash 메시지를 위해 필요 (실제 운영 시 변경 필요)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp', 'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 최대 파일 크기: 16MB

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# 허용된 파일 확장자 확인
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# 안전한 파일 이름 생성 (비ASCII 문자 허용)
def safe_filename(filename):
    # NULL 바이트 제거
    filename = filename.replace('\x00', '')
    # 경로 구분자 제거
    filename = filename.replace('/', '').replace('\\', '')
    # 제어 문자 제거
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    return filename

# 확장자에 따른 MIME 타입 매핑
MIMETYPES = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'bmp': 'image/bmp',
    'tiff': 'image/tiff',
    'webp': 'image/webp',
    'pdf': 'application/pdf',
}

def process_pdf_to_image(file, original_filename, target_format='png'):
    images = []
    try:
        pdf_bytes = file.read()
        pages = convert_from_bytes(pdf_bytes)
        for i, page in enumerate(pages):
            img_io = io.BytesIO()
            # 사용자가 선택한 포맷으로 저장 (기본값 PNG)
            save_format = target_format.upper() if target_format else 'PNG'
            if save_format == 'JPG': save_format = 'JPEG'
            
            page.save(img_io, format=save_format)
            img_io.seek(0)
            
            filename_without_ext = '.'.join(original_filename.split('.')[:-1])
            ext = target_format.lower() if target_format else 'png'
            new_filename = f"{filename_without_ext}_page_{i + 1}.{ext}"
            images.append((new_filename, img_io))
    except Exception as e:
        print(f"PDF 변환 오류: {e}")
        raise e
    return images

def process_image_conversion(file, original_filename, width, height, convert_to):
    try:
        img = Image.open(file.stream)
        
        # 크기 조절
        if width or height:
            w, h = img.size
            width_val = int(width) if width else None
            height_val = int(height) if height else None

            if width_val and height_val:
                img = img.resize((width_val, height_val))
            elif width_val:
                ratio = width_val / w
                height_val = int(h * ratio)
                img = img.resize((width_val, height_val))
            elif height_val:
                ratio = height_val / h
                width_val = int(w * ratio)
                img = img.resize((width_val, height_val))

        # 확장자 변환 설정
        if convert_to:
            target_ext = convert_to.lower()
        else:
            target_ext = img.format.lower() if img.format else 'png'
            if target_ext == 'jpeg':
                target_ext = 'jpg'

        # 이미지 모드 변경 (JPG는 투명도 지원 안함)
        if target_ext in ['jpg', 'jpeg', 'bmp'] and img.mode in ['RGBA', 'LA']:
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode == 'P': # Palette 모드 처리
            img = img.convert('RGB')

        img_io = io.BytesIO()
        save_format = target_ext.upper()
        if save_format == 'JPG': save_format = 'JPEG'
        
        img.save(img_io, format=save_format)
        img_io.seek(0)

        filename_without_ext = '.'.join(original_filename.split('.')[:-1])
        new_filename = f"{filename_without_ext}.{target_ext}"
        return (new_filename, img_io)
    except Exception as e:
        print(f"이미지 처리 오류: {e}")
        raise e

@app.route('/', methods=['GET', 'POST'])
def upload_files():
    if request.method == 'POST':
        files = request.files.getlist('files')
        width = request.form.get('width')
        height = request.form.get('height')
        convert_to = request.form.get('convert_to')
        convert_direction = request.form.get('convert_direction')

        if not files or files[0].filename == '':
            flash('파일을 선택해주세요.')
            return redirect(request.url)

        processed_files = []
        errors = []

        # Image to PDF는 모든 이미지를 하나로 합치는 로직이므로 별도 처리
        if convert_direction == 'image_to_pdf':
            pil_images = []
            for file in files:
                if file and allowed_file(file.filename):
                    try:
                        img = Image.open(file.stream)
                        img = img.convert('RGB')
                        pil_images.append(img)
                    except Exception as e:
                        errors.append(f"{file.filename}: {str(e)}")
            
            if not pil_images:
                flash('변환할 수 있는 이미지가 없습니다.')
                return redirect(request.url)

            try:
                pdf_io = io.BytesIO()
                pil_images[0].save(pdf_io, format='PDF', save_all=True, append_images=pil_images[1:])
                pdf_io.seek(0)
                
                response = send_file(
                    pdf_io,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name='converted.pdf')
                return response
            except Exception as e:
                flash(f'PDF 생성 중 오류 발생: {str(e)}')
                return redirect(request.url)

        # 그 외 (PDF -> Image, Image Conversion)
        for file in files:
            if file and allowed_file(file.filename):
                original_filename = safe_filename(file.filename)
                ext = original_filename.rsplit('.', 1)[1].lower()

                try:
                    if convert_direction == 'pdf_to_image' and ext == 'pdf':
                        # PDF -> Image (convert_to 옵션 사용)
                        images = process_pdf_to_image(file, original_filename, convert_to)
                        processed_files.extend(images)
                    
                    elif convert_direction == 'image_conversion':
                        # Image -> Image
                        result = process_image_conversion(file, original_filename, width, height, convert_to)
                        processed_files.append(result)
                except Exception as e:
                    errors.append(f"{file.filename}: {str(e)}")

        if errors:
            for error in errors:
                flash(f'오류 발생: {error}')
        
        if not processed_files:
            if not errors: # 에러도 없고 파일도 없으면 (필터링됨)
                flash('처리할 수 있는 파일이 없습니다.')
            return redirect(request.url)

        # 결과 반환 (단일 파일 또는 ZIP)
        if len(processed_files) == 1:
            filename, file_io = processed_files[0]
            ext = filename.rsplit('.', 1)[1].lower()
            mime = MIMETYPES.get(ext, 'application/octet-stream')
            
            return send_file(
                file_io,
                mimetype=mime,
                as_attachment=True,
                download_name=filename)
        else:
            zip_io = io.BytesIO()
            with zipfile.ZipFile(zip_io, mode='w') as zipf:
                for filename, file_io in processed_files:
                    zipf.writestr(filename, file_io.getvalue())
            zip_io.seek(0)
            
            return send_file(
                zip_io,
                mimetype='application/zip',
                as_attachment=True,
                download_name='converted_files.zip')

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
