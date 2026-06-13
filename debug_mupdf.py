"""Debug MuPDF JBIG2 output"""
import fitz, tempfile, os, re
from PIL import Image
from io import BytesIO

img = Image.open(r'D:\wallpapers\abstract-art-3840x2160-26359.jpg').convert('RGB')
img.thumbnail((100, 100), Image.LANCZOS)
img_bw = img.convert('L').point(lambda x: 0 if x < 128 else 255, '1')

doc = fitz.open()
page = doc.new_page(width=img_bw.width, height=img_bw.height)
png_buf = BytesIO()
img_bw.save(png_buf, format='PNG')
pix = fitz.Pixmap(png_buf.getvalue())
page.insert_image(fitz.Rect(0, 0, img_bw.width, img_bw.height), pixmap=pix)

tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
tmp.close()
doc.save(tmp.name, garbage=4, deflate=False)
doc.close()

with open(tmp.name, 'rb') as f:
    pdf_bytes = f.read()
text = pdf_bytes.decode('latin-1')

print('Full PDF text:')
print(text)
print('\n---')
print(f'File size: {len(pdf_bytes)} bytes')
os.unlink(tmp.name)
