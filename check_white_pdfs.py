"""检查所有编码器生成的PDF, 找出白屏/黑屏问题"""
import sys, os, tempfile
sys.path.insert(0, 'src')
from PIL import Image
from encoders import get_encoder, list_encoders
import pikepdf, zlib, fitz

# 测试图像
img = Image.open(r'D:\wallpapers\abstract-art-3840x2160-26359.jpg').convert('RGB')
img.thumbnail((100, 100), Image.LANCZOS)
raw = img.tobytes()

results = []
for name in list_encoders():
    enc = get_encoder(name)
    data, params = enc.encode(img)

    # 对complete_pdf直接使用
    if getattr(params, 'complete_pdf', None):
        pdf_bytes = params.complete_pdf
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        tmp.write(pdf_bytes); tmp.close()
        pdf_path = tmp.name
    else:
        pdf = pikepdf.Pdf.new()
        pdf.add_blank_page(page_size=(300, 300))
        page = pdf.pages[0]
        xobj = pdf.make_stream(data)
        xobj.Type = pikepdf.Name('/XObject')
        xobj.Subtype = pikepdf.Name('/Image')
        xobj.Width = params.width; xobj.Height = params.height
        xobj.ColorSpace = pikepdf.Name(params.color_space)
        xobj.BitsPerComponent = params.bits_per_component
        if params.filter:
            xobj.Filter = pikepdf.Name(params.filter)
        if params.decode_parms:
            dp = pikepdf.Dictionary()
            for k, v in params.decode_parms.items():
                ck = k.lstrip('/')
                if isinstance(v, bool):
                    dp['/'+ck] = pikepdf.Name('/true' if v else '/false')
                else:
                    dp['/'+ck] = v
            xobj.DecodeParms = dp
        page.Resources = pikepdf.Dictionary({
            '/XObject': pikepdf.Dictionary({'/Im0': pdf.make_indirect(xobj)})
        })
        content = f'q {params.width} 0 0 {params.height} 0 0 cm /Im0 Do Q'
        cs = pdf.make_stream(zlib.compress(content.encode()))
        cs.Filter = pikepdf.Name('/FlateDecode')
        page.Contents = cs
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        tmp.close()
        pdf.save(tmp.name, compress_streams=False)
        pdf.close()
        pdf_path = tmp.name

    # MuPDF验证渲染
    try:
        doc = fitz.open(pdf_path)
        pix = doc[0].get_pixmap()
        samples = pix.samples
        total = len(samples)
        white = sum(1 for b in samples if b > 250)
        black = sum(1 for b in samples if b < 5)
        non_white = total - white
        status = 'OK'
        if non_white < 100:
            status = 'ALL_WHITE'
        elif non_white < 5000:
            status = 'LOW_CONTENT'
        # 检查是否全是黑色(CCITT/G4在黑白页面上背景应为白)
        non_black = total - black
        if non_black < 100:
            status = 'ALL_BLACK'
        doc.close()
    except Exception as e:
        status = 'ERROR'
        non_white = 0
    
    os.unlink(pdf_path)
    results.append((name, status, non_white))
    
    # 对异常状态立即输出
    if status != 'OK':
        detail = f'non-white={non_white}/{(100*100)} for 100x100 img'
        print(f'  [!!] {name}: {status} - {detail}')

print(f'\n所有编码检测完成:')
for name, status, nw in results:
    mark = '✅' if status == 'OK' else '❌'
    print(f'  {mark} {name:<10s} {status}')
