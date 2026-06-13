"""PDF构造器: 统一接口, 内部根据编码类型选择不同构造策略

策略说明:
- A策略 (pikepdf): 适用于DCT/Flate/JPX/CCITT等pikepdf原生支持的编码
- B策略 (手动构造): 适用于LZW/RLE/Raw等pikepdf不支持或会自动转换的编码

手动构造B策略的PDF结构:
  %PDF-1.4
  1 0 obj  (图像XObject: /Filter /LZWDecode)
  2 0 obj  (页面内容流)
  3 0 obj  (页面字典)
  4 0 obj  (页面树)
  5 0 obj  (Catalog)
  xref
  trailer
  startxref
  %%EOF
"""
import zlib
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from src.encoders.base import EncodeParams
from src.pdf.objects import PdfStream, PdfObject
from src.pdf.xref import XRefTable, make_trailer

log = logging.getLogger(__name__)

# 需要手动构造B策略的编码
MANUAL_ENCODINGS = {'/LZWDecode', '/RunLengthDecode'}


@dataclass
class PdfBuildResult:
    """PDF构造结果"""
    path: Path
    size_bytes: int
    method: str          # 'pikepdf' or 'manual'


class PdfBuilder:
    """PDF构造器: 支持pikepdf和手动两种构造策略"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        image_data: bytes,
        params: EncodeParams,
        image_name: str,
        encoder_name: str,
    ) -> PdfBuildResult:
        """
        创建包含指定编码图像的PDF。

        Args:
            image_data: 编码后的图像数据
            params: 编码参数
            image_name: 源图像名称(用于PDF文件名)
            encoder_name: 编码器名称

        Returns:
            PdfBuildResult
        """
        safe_name = image_name[:30]
        pdf_name = f'{safe_name}_{encoder_name}.pdf'
        pdf_path = self.output_dir / encoder_name / pdf_name
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        # 特殊处理: complete_pdf (JBIG2等MuPDF生成的完整PDF)
        complete_pdf = getattr(params, 'complete_pdf', None)
        if complete_pdf:
            pdf_path.write_bytes(complete_pdf)
            log.debug(f'  [complete_pdf] {pdf_path.name}')
            return PdfBuildResult(path=pdf_path, size_bytes=pdf_path.stat().st_size,
                                  method='mupdf')

        if params.filter in MANUAL_ENCODINGS or params.filter is None:
            return self._build_manual(image_data, params, pdf_path)
        else:
            return self._build_pikepdf(image_data, params, pdf_path)

    def _build_pikepdf(
        self, image_data: bytes, params: EncodeParams, pdf_path: Path
    ) -> PdfBuildResult:
        """A策略: 使用pikepdf生成"""
        import pikepdf

        pdf = pikepdf.Pdf.new()
        pdf.add_blank_page(page_size=(612, 792))
        page = pdf.pages[0]

        # 构造图像XObject (先make_stream, 再设置属性)
        xobj = pdf.make_stream(image_data)
        xobj.Type = pikepdf.Name('/XObject')
        xobj.Subtype = pikepdf.Name('/Image')
        xobj.Width = params.width
        xobj.Height = params.height
        xobj.ColorSpace = pikepdf.Name(params.color_space)
        xobj.BitsPerComponent = params.bits_per_component
        if params.filter:
            xobj.Filter = pikepdf.Name(params.filter)
        if params.decode_parms:
            dp = pikepdf.Dictionary()
            for k, v in params.decode_parms.items():
                dp['/' + k.lstrip('/')] = v
            xobj.DecodeParms = dp

        # Alpha/透明度: 添加SMask
        smask_data = params.__dict__.get('smask')
        smask_obj = None
        if smask_data:
            smask_obj = pdf.make_stream(smask_data)
            smask_obj.Type = pikepdf.Name('/XObject')
            smask_obj.Subtype = pikepdf.Name('/Image')
            smask_obj.Width = params.width
            smask_obj.Height = params.height
            smask_obj.ColorSpace = pikepdf.Name('/DeviceGray')
            smask_obj.BitsPerComponent = 8
            smask_obj.Filter = pikepdf.Name(params.filter) if params.filter else None
            xobj.SMask = pdf.make_indirect(smask_obj)

        # 放置到页面
        aspect = params.width / params.height
        disp_w = min(500, 700 * aspect)
        disp_h = disp_w / aspect
        if disp_h > 700:
            disp_h = 700
            disp_w = disp_h * aspect
        cx, cy = (612 - disp_w) / 2, (792 - disp_h) / 2

        page.Resources = pikepdf.Dictionary({
            '/XObject': pikepdf.Dictionary({
                '/Im0': pdf.make_indirect(xobj)
            })
        })
        content = f'q {disp_w:.2f} 0 0 {disp_h:.2f} {cx:.2f} {cy:.2f} cm /Im0 Do Q'
        content_stream = pdf.make_stream(zlib.compress(content.encode('latin-1')))
        content_stream.Filter = pikepdf.Name('/FlateDecode')
        page.Contents = content_stream

        pdf.save(pdf_path, compress_streams=False)
        pdf.close()

        log.debug(f'  [pikepdf] 已生成: {pdf_path.name}')
        return PdfBuildResult(path=pdf_path, size_bytes=pdf_path.stat().st_size,
                              method='pikepdf')

    def _build_manual(
        self, image_data: bytes, params: EncodeParams, pdf_path: Path
    ) -> PdfBuildResult:
        """B策略: 手动构造PDF字节 (避免pikepdf替换Filter)"""
        w, h = params.width, params.height

        # 计算显示尺寸
        aspect = w / h
        disp_w = min(500, 700 * aspect)
        disp_h = disp_w / aspect
        if disp_h > 700:
            disp_h = 700
            disp_w = disp_h * aspect
        cx, cy = (612 - disp_w) / 2, (792 - disp_h) / 2

        smask_data = params.__dict__.get('smask')

        # --- 分配对象编号 (SMask存在时插入为obj 2, 后续对象顺延) ---
        OBJ_IMG = 1          # 图像XObject
        OBJ_SMASK = 2 if smask_data else None   # SMask (可选, 插入为obj 2)
        OBJ_CONTENT = 3 if smask_data else 2    # 页面内容流
        OBJ_PAGE = 4 if smask_data else 3       # 页面字典
        OBJ_PAGES = 5 if smask_data else 4      # 页面树
        OBJ_CATALOG = 6 if smask_data else 5    # Catalog

        # 构造各个PDF对象
        xref = XRefTable()
        pdf_bytes = bytearray(b'%PDF-1.4\n')

        # --- obj 1: 图像XObject ---
        img_dict = {
            '/Type': '/XObject',
            '/Subtype': '/Image',
            '/Width': w,
            '/Height': h,
            '/ColorSpace': params.color_space,
            '/BitsPerComponent': params.bits_per_component,
            '/Length': len(image_data),
        }
        if params.filter:
            img_dict['/Filter'] = params.filter
        if params.decode_parms:
            img_dict['/DecodeParms'] = _dict_to_pdf(params.decode_parms)
        if smask_data:
            img_dict['/SMask'] = f'{OBJ_SMASK} 0 R'

        xref.add_entry(len(pdf_bytes))
        stream = PdfStream(OBJ_IMG, image_data, img_dict)
        pdf_bytes.extend(stream.serialize())

        # --- obj 2: SMask (仅Alpha编码) ---
        if smask_data:
            smask_dict = {
                '/Type': '/XObject',
                '/Subtype': '/Image',
                '/Width': w,
                '/Height': h,
                '/ColorSpace': '/DeviceGray',
                '/BitsPerComponent': 8,
                '/Length': len(smask_data),
            }
            if params.filter:
                smask_dict['/Filter'] = params.filter
            xref.add_entry(len(pdf_bytes))
            s_stream = PdfStream(OBJ_SMASK, smask_data, smask_dict)
            pdf_bytes.extend(s_stream.serialize())

        # --- 页面内容流 (Flate压缩) ---
        content = f'q {disp_w:.2f} 0 0 {disp_h:.2f} {cx:.2f} {cy:.2f} cm /Im0 Do Q'
        comp = zlib.compress(content.encode('latin-1'))
        content_dict = {'/Length': len(comp), '/Filter': '/FlateDecode'}
        xref.add_entry(len(pdf_bytes))
        content_stream = PdfStream(OBJ_CONTENT, comp, content_dict)
        pdf_bytes.extend(content_stream.serialize())

        # --- 页面字典 (必须是普通字典, 不能是Stream) ---
        page_dict_raw = (
            f'<< /Type /Page /Parent {OBJ_PAGES} 0 R'
            f' /MediaBox [0 0 612 792]'
            f' /Contents {OBJ_CONTENT} 0 R'
            f' /Resources << /XObject << /Im0 {OBJ_IMG} 0 R >> >>'
            f' >>'
        )
        xref.add_entry(len(pdf_bytes))
        page_obj = PdfObject(OBJ_PAGE, page_dict_raw)
        pdf_bytes.extend(page_obj.serialize())

        # --- 页面树 ---
        xref.add_entry(len(pdf_bytes))
        pages = f'<< /Type /Pages /Kids [{OBJ_PAGE} 0 R] /Count 1 >>'
        pdf_bytes.extend(f'{OBJ_PAGES} 0 obj\n{pages}\nendobj\n'.encode('latin-1'))

        # --- Catalog ---
        xref.add_entry(len(pdf_bytes))
        catalog = f'<< /Type /Catalog /Pages {OBJ_PAGES} 0 R >>'
        pdf_bytes.extend(f'{OBJ_CATALOG} 0 obj\n{catalog}\nendobj\n'.encode('latin-1'))

        # --- xref + trailer ---
        xref_offset = len(pdf_bytes)
        pdf_bytes.extend(xref.serialize())
        pdf_bytes.extend(b'\n')
        pdf_bytes.extend(make_trailer(xref.size, OBJ_CATALOG).encode('latin-1'))
        pdf_bytes.extend(b'\n')
        pdf_bytes.extend(f'startxref\n{xref_offset}\n%%EOF\n'.encode('latin-1'))

        # 写入文件
        pdf_path.write_bytes(bytes(pdf_bytes))
        log.debug(f'  [manual] 已生成: {pdf_path.name} (xref={xref_offset})')
        return PdfBuildResult(path=pdf_path, size_bytes=pdf_path.stat().st_size,
                              method='manual')


def _dict_to_pdf(d: dict) -> str:
    """将Python字典转为PDF字典字符串 << /K v >>"""
    items = ' '.join(f'/{k} {_pdf_val(v)}' for k, v in d.items())
    return f'<< {items} >>'


def _pdf_val(v):
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return f'{v}'
    return str(v)
