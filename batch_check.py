"""批量检查多张图像的所有编码"""
import sys, os, tempfile, random
sys.path.insert(0, 'src')
from PIL import Image
from pathlib import Path
from encoders import get_encoder, list_encoders
import pikepdf, zlib, fitz

# 选10张不同的测试图像
wallpapers = sorted(Path(r'D:\wallpapers').glob('*.jpg'))
random.seed(42)
selected = random.sample(wallpapers, min(10, len(wallpapers)))

print(f'测试 {len(selected)} 张图像 x {len(list_encoders())} 种编码')
print()

all_ok = True
for img_path in selected:
    img = Image.open(img_path).convert('RGB')
    img.thumbnail((200, 200), Image.LANCZOS)
    print(f'  [{img_path.stem[:30]:30s}] {img.size[0]}x{img.size[1]}')
    
    for name in list_encoders():
        enc = get_encoder(name)
        try:
            data, params = enc.encode(img)
        except Exception as e:
            print(f'      {name}: ENCODE_ERROR {str(e)[:40]}')
            all_ok = False
            continue

        try:
            if getattr(params, 'complete_pdf', None):
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                tmp.write(params.complete_pdf); tmp.close()
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
                if params.filter: xobj.Filter = pikepdf.Name(params.filter)
                if params.decode_parms:
                    dp = pikepdf.Dictionary()
                    for k, v in params.decode_parms.items():
                        ck = k.lstrip('/')
                        dp['/'+ck] = v  # 直接传值, pikepdf处理类型
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
                pdf.save(tmp.name, compress_streams=False); pdf.close()
                pdf_path = tmp.name

            # MuPDF渲染检查
            doc = fitz.open(pdf_path)
            pix = doc[0].get_pixmap()
            samples = pix.samples
            white = sum(1 for b in samples if b > 250)
            black = sum(1 for b in samples if b < 5)
            total = len(samples)
            doc.close()
            os.unlink(pdf_path)
            
            non_white = total - white
            non_black = total - black
            
            # 期望: 100x100图像≈10000非白像素
            exp_pixels = params.width * params.height
            if non_white < exp_pixels * 0.3:
                print(f'      {name}: ALL_WHITE (non-white={non_white}/{exp_pixels})')
                all_ok = False
            elif non_black < exp_pixels * 0.3:
                print(f'      {name}: ALL_BLACK (non-black={non_black}/{exp_pixels})')
                all_ok = False
        except Exception as e:
            print(f'      {name}: RENDER_ERROR {str(e)[:60]}')
            all_ok = False

print(f'\n{"✅ 全部通过!" if all_ok else "❌ 存在失败!"}')
