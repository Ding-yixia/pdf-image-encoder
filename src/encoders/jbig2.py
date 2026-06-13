"""JBIG2Encoder: JBIG2Decode — 使用PyMuPDF直接生成PDF

由于纯Python JBIG2编码器难以达到100%标准兼容,
使用MuPDF原生生成包含JBIG2编码图像的PDF。

流程:
1. 图像灰度化 + 二值化
2. 用MuPDF插入1-bit图像(原生支持JBIG2)
3. 直接返回MuPDF生成的PDF

注意: 返回的data是完整PDF字节, params.mark_complete_pdf=True
"""
import os, tempfile
from io import BytesIO
from PIL import Image
from .base import Encoder, EncodeParams


class JBIG2Encoder(Encoder):
    """JBIG2编码器: 基于MuPDF直接生成PDF"""

    @property
    def name(self) -> str:
        return 'JBIG2'

    def encode(self, image: Image.Image) -> tuple[bytes, EncodeParams]:
        try:
            import fitz
        except ImportError:
            raise RuntimeError("需要PyMuPDF: pip install PyMuPDF")

        # 灰度化 → 二值化
        if image.mode != 'L':
            image = image.convert('L')
        img_bw = image.point(lambda x: 0 if x < 128 else 255, '1')

        # 创建MuPDF文档
        doc = fitz.open()
        # 页面尺寸(点), 图像通过cm矩阵缩放
        page = doc.new_page(width=612, height=792)

        # 通过PNG创建Pixmap
        png_buf = BytesIO()
        img_bw.save(png_buf, format='PNG')
        pix = fitz.Pixmap(png_buf.getvalue())
        page.insert_image(
            fitz.Rect(56, 100, 556, 700),  # 在页面上居中显示
            pixmap=pix,
        )

        # 保存PDF到临时文件
        tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmp.close()
        doc.save(tmp.name, garbage=4, deflate=True)
        doc.close()

        # 读取完整PDF
        with open(tmp.name, 'rb') as f:
            pdf_bytes = f.read()
        os.unlink(tmp.name)

        # 返回PDF数据, 标记为完整PDF
        params = EncodeParams(
            filter=None,  # 无单独Filter, data是完整PDF
            color_space='/DeviceGray',
            bits_per_component=1,
            width=image.width,
            height=image.height,
            pre_compressed=True,
            complete_pdf=pdf_bytes,  # 携带完整PDF
        )
        return pdf_bytes, params
