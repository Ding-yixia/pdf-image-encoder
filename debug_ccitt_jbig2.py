"""Debug CCITT and JBIG2 encoding"""
import sys, os
sys.path.insert(0, 'src')

from PIL import Image
from io import BytesIO
from encoders.jbig2 import JBIG2Encoder
from encoders.ccitt import CCITTEncoder

# Load test image
img = Image.open(r'D:\wallpapers\abstract-art-3840x2160-26359.jpg').convert('RGB')
img.thumbnail((100, 100), Image.LANCZOS)
print(f'Image: {img.size}, mode={img.mode}')

# CCITT test
enc_ccitt = CCITTEncoder()
data_ccitt, params_ccitt = enc_ccitt.encode(img)
print(f'\nCCITT: {len(data_ccitt)} bytes, filter={params_ccitt.filter}')
print(f'  First 10 bytes hex: {data_ccitt[:20].hex()}')

# JBIG2 test
enc_jbig2 = JBIG2Encoder()
data_jbig2, params_jbig2 = enc_jbig2.encode(img)
print(f'\nJBIG2: {len(data_jbig2)} bytes, filter={params_jbig2.filter}')
print(f'  Header: {data_jbig2[:8]}')
print(f'  First 20 bytes hex: {data_jbig2[:20].hex()}')

# Create PDFs for testing
import pikepdf, zlib

def make_test_pdf(data, params, name):
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    page = pdf.pages[0]
    xobj = pdf.make_stream(data)
    xobj.Type = pikepdf.Name('/XObject')
    xobj.Subtype = pikepdf.Name('/Image')
    xobj.Width = params.width
    xobj.Height = params.height
    xobj.ColorSpace = pikepdf.Name(params.color_space)
    xobj.BitsPerComponent = params.bits_per_component
    xobj.Filter = pikepdf.Name(params.filter)
    if params.decode_parms:
        dp = pikepdf.Dictionary()
        for k, v in params.decode_parms.items():
            dp['/' + k.lstrip('/')] = v
        xobj.DecodeParms = dp
    page.Resources = pikepdf.Dictionary({
        '/XObject': pikepdf.Dictionary({'/Im0': pdf.make_indirect(xobj)})
    })
    content = f'q 200 0 0 200 50 300 cm /Im0 Do Q'
    cs = pdf.make_stream(zlib.compress(content.encode()))
    cs.Filter = pikepdf.Name('/FlateDecode')
    page.Contents = cs
    pdf.save(f'test_{name}.pdf')
    pdf.close()
    print(f'  PDF test_{name}.pdf created')

make_test_pdf(data_ccitt, params_ccitt, 'ccitt')
make_test_pdf(data_jbig2, params_jbig2, 'jbig2')

# Verify with MuPDF
try:
    import fitz
    for name in ['ccitt', 'jbig2']:
        doc = fitz.open(f'test_{name}.pdf')
        page = doc[0]
        # Try rendering just the image
        pix = page.get_pixmap()
        non_black = sum(1 for b in pix.samples if b > 10)
        print(f'\nMuPDF verify {name}: {pix.width}x{pix.height}, non-black={non_black}/{len(pix.samples)}')
        doc.close()
except Exception as e:
    print(f'MuPDF error: {e}')
