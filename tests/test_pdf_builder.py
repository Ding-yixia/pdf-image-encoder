"""验证手动构造PDF和pikepdf构造PDF的正确性"""
import sys
import os
import zlib
import io
import tempfile
from pathlib import Path

# 确保能找到 src
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import pikepdf

from src.encoders import get_encoder, list_encoders
from src.pdf.builder import PdfBuilder
from src.pdf.xref import XRefTable
from src.encoders.base import EncodeParams


def create_test_image(width=100, height=80, mode='RGB'):
    """创建测试图像"""
    img = Image.new(mode, (width, height))
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            if mode == 'RGBA':
                pixels[x, y] = (x * 2 % 256, y * 3 % 256, (x + y) % 256,
                                255 if (x + y) % 3 != 0 else 0)
            elif mode == 'RGB':
                pixels[x, y] = (x * 2 % 256, y * 3 % 256, (x + y) % 256)
            else:
                pixels[x, y] = (x + y) % 256
    return img


def open_pdf_from_path(path):
    """从文件字节打开PDF，避免Windows文件锁定"""
    return pikepdf.open(io.BytesIO(path.read_bytes()))


def test_xref_entry_length():
    """测试: XRef条目恰好20字节"""
    print('[TEST] XRef条目长度...')
    xref = XRefTable()
    xref.add_entry(100)
    xref.add_entry(2500)
    raw = xref.serialize()

    # 拆分: header + entries
    lines = raw.split(b'\n')
    # lines[0] = b'xref'
    # lines[1] = b'0 3'
    # lines[2] = b'0000000000 65535 f ' (entry 0)
    # lines[3] = b'0000000100 00000 n ' (entry 1)
    # lines[4] = b'0000002500 00000 n ' (entry 2)
    # lines[5] = b'' (trailing)

    entry_lines = lines[2:5]  # 3 entries
    for i, line in enumerate(entry_lines):
        # Each entry line + '\n' = 20 bytes
        actual_len = len(line) + 1  # +1 for the \n separator
        assert actual_len == 20, (
            f'XRef entry {i} length = {actual_len}, expected 20. '
            f'Content: {line!r}'
        )

    print('  PASS: 所有XRef条目恰好20字节')


def test_xref_entry_offsets():
    """测试: XRef条目偏移量正确"""
    print('[TEST] XRef条目偏移量...')
    xref = XRefTable()
    xref.add_entry(42)
    xref.add_entry(12345)
    raw = xref.serialize()
    text = raw.decode('ascii')
    assert '0000000042 00000 n' in text, f'偏移42未找到: {text}'
    assert '0000012345 00000 n' in text, f'偏移12345未找到: {text}'
    print('  PASS: XRef偏移量格式正确')


def test_manual_pdf_no_smask():
    """测试: 手动构建PDF(无SMask)可被pikepdf正确打开"""
    print('[TEST] 手动构建PDF (无SMask)...')
    img = create_test_image(100, 80)
    raw_rgb = img.tobytes()

    with tempfile.TemporaryDirectory() as tmpdir:
        builder = PdfBuilder(Path(tmpdir))

        # 使用Raw编码 (filter=None → manual path)
        encoder = get_encoder('Raw')
        encoded_data, params = encoder.encode(img)

        result = builder.build(encoded_data, params, 'test', 'Raw')
        assert result.path.exists(), f'PDF未生成: {result.path}'
        assert result.size_bytes > 0, 'PDF为空'
        assert result.method == 'manual', f'方法错误: {result.method}'

        # 验证PDF可被pikepdf打开
        pdf = open_pdf_from_path(result.path)
        assert len(pdf.pages) == 1, f'页数错误: {len(pdf.pages)}'

        page = pdf.pages[0]
        assert '/Resources' in page, '页面无Resources'
        xobjects = page.Resources['/XObject']
        assert '/Im0' in xobjects, '无图像XObject'

        im = xobjects['/Im0']
        assert int(im.Width) == 100, f'宽度错误: {im.Width}'
        assert int(im.Height) == 80, f'高度错误: {im.Height}'

        # 验证图像数据
        decoded = im.read_bytes()
        assert len(decoded) == len(raw_rgb), (
            f'数据大小不匹配: decoded={len(decoded)}, expected={len(raw_rgb)}'
        )
        assert decoded == raw_rgb, '图像数据不匹配'
        pdf.close()

    print('  PASS: 无SMask手动PDF结构正确，数据完整')


def test_manual_pdf_lzw():
    """测试: LZW编码手动构建PDF"""
    print('[TEST] LZW手动构建PDF...')
    img = create_test_image(100, 80)

    with tempfile.TemporaryDirectory() as tmpdir:
        builder = PdfBuilder(Path(tmpdir))
        encoder = get_encoder('LZW')
        encoded_data, params = encoder.encode(img)

        result = builder.build(encoded_data, params, 'test', 'LZW')
        assert result.path.exists(), f'PDF未生成'
        assert result.method == 'manual', f'方法错误: {result.method}'

        # 验证PDF结构
        pdf = open_pdf_from_path(result.path)
        page = pdf.pages[0]
        im = page.Resources['/XObject']['/Im0']
        assert int(im.Width) == 100
        assert int(im.Height) == 80
        assert str(im.Filter) == '/LZWDecode', f'Filter错误: {im.Filter}'

        # pikepdf会解码LZW，验证解码后数据
        decoded = im.read_bytes()
        expected_size = 100 * 80 * 3  # RGB
        assert len(decoded) == expected_size, (
            f'LZW解码大小不匹配: {len(decoded)} vs {expected_size}'
        )
        pdf.close()

    print('  PASS: LZW手动PDF结构正确')


def test_manual_pdf_rle():
    """测试: RLE编码手动构建PDF"""
    print('[TEST] RLE手动构建PDF...')
    img = create_test_image(100, 80)

    with tempfile.TemporaryDirectory() as tmpdir:
        builder = PdfBuilder(Path(tmpdir))
        encoder = get_encoder('RLE')
        encoded_data, params = encoder.encode(img)

        result = builder.build(encoded_data, params, 'test', 'RLE')
        assert result.path.exists()
        assert result.method == 'manual'

        pdf = open_pdf_from_path(result.path)
        page = pdf.pages[0]
        im = page.Resources['/XObject']['/Im0']
        assert str(im.Filter) == '/RunLengthDecode', f'Filter错误: {im.Filter}'
        assert int(im.Width) == 100
        assert int(im.Height) == 80
        # pikepdf不支持解码RunLengthDecode, 验证原始stream数据长度
        raw_stream = im.read_raw_bytes()
        assert len(raw_stream) == len(encoded_data), (
            f'原始数据长度不匹配: {len(raw_stream)} vs {len(encoded_data)}'
        )
        pdf.close()

    print('  PASS: RLE手动PDF结构正确')


def test_manual_pdf_with_smask():
    """测试: Alpha编码(SMask)手动构建PDF"""
    print('[TEST] Alpha编码(SMask)手动构建PDF...')
    img = create_test_image(100, 80, mode='RGBA')

    with tempfile.TemporaryDirectory() as tmpdir:
        builder = PdfBuilder(Path(tmpdir))
        encoder = get_encoder('Alpha')
        encoded_data, params = encoder.encode(img)

        assert params.smask is not None, 'SMask数据为空'

        result = builder.build(encoded_data, params, 'test', 'Alpha')
        assert result.path.exists(), f'PDF未生成'
        assert result.method == 'manual'

        # 验证PDF结构
        pdf = open_pdf_from_path(result.path)
        assert len(pdf.pages) == 1, f'页数错误: {len(pdf.pages)}'

        page = pdf.pages[0]
        assert '/Resources' in page, '页面无Resources'
        xobjects = page.Resources['/XObject']
        assert '/Im0' in xobjects, '无图像XObject'

        im = xobjects['/Im0']
        assert int(im.Width) == 100, f'宽度错误: {im.Width}'
        assert int(im.Height) == 80, f'高度错误: {im.Height}'
        assert str(im.ColorSpace) == '/DeviceRGB', f'颜色空间错误: {im.ColorSpace}'

        # 验证SMask存在
        assert '/SMask' in im, 'SMask不存在'
        smask = im.SMask
        assert int(smask.Width) == 100, f'SMask宽度错误: {smask.Width}'
        assert int(smask.Height) == 80, f'SMask高度错误: {smask.Height}'
        assert str(smask.ColorSpace) == '/DeviceGray', (
            f'SMask颜色空间错误: {smask.ColorSpace}'
        )

        # 验证主图像可解码
        decoded_rgb = im.read_bytes()
        assert len(decoded_rgb) == 100 * 80 * 3, (
            f'RGB数据大小错误: {len(decoded_rgb)}'
        )

        # 验证SMask可解码
        decoded_alpha = smask.read_bytes()
        assert len(decoded_alpha) == 100 * 80, (
            f'Alpha数据大小错误: {len(decoded_alpha)}'
        )

        pdf.close()

    print('  PASS: Alpha(SMask)手动PDF结构正确，对象编号无冲突')


def test_pikepdf_builder():
    """测试: pikepdf策略构建PDF(DCT/Flate/JPX)"""
    print('[TEST] pikepdf策略构建PDF...')
    img = create_test_image(100, 80)

    for enc_name in ['DCT', 'Flate', 'JPX']:
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = PdfBuilder(Path(tmpdir))
            encoder = get_encoder(enc_name)
            encoded_data, params = encoder.encode(img)

            result = builder.build(encoded_data, params, 'test', enc_name)
            assert result.path.exists(), f'{enc_name} PDF未生成'
            assert result.method == 'pikepdf', f'{enc_name} 方法错误'

            pdf = open_pdf_from_path(result.path)
            assert len(pdf.pages) == 1
            page = pdf.pages[0]
            im = page.Resources['/XObject']['/Im0']
            assert int(im.Width) == 100
            assert int(im.Height) == 80
            pdf.close()

    print('  PASS: pikepdf策略PDF均正确')


def test_page_object_is_dictionary_not_stream():
    """测试: 手动PDF中的页面对象是字典而非Stream"""
    print('[TEST] 页面对象类型验证...')
    img = create_test_image(50, 40)

    with tempfile.TemporaryDirectory() as tmpdir:
        builder = PdfBuilder(Path(tmpdir))
        encoder = get_encoder('Raw')
        encoded_data, params = encoder.encode(img)
        result = builder.build(encoded_data, params, 'test', 'Raw')

        # 读取原始PDF字节，验证页面对象不是stream
        raw_bytes = result.path.read_bytes()
        pdf_text = raw_bytes.decode('latin-1')

        # 页面对象应包含 "/Type /Page" 且不应在stream内
        assert '/Type /Page' in pdf_text, '页面对象缺少 /Type /Page'

        # 确保页面字典不以 "stream" 开头
        # 找到页面字典的位置
        page_idx = pdf_text.find('/Type /Page')
        assert page_idx > 0, '未找到页面对象'

        # 向前找到对象开头
        obj_start = pdf_text.rfind('obj', 0, page_idx)
        # 向后找到对象结束
        obj_end = pdf_text.find('endobj', page_idx)

        obj_content = pdf_text[obj_start:obj_end]
        assert 'stream' not in obj_content, (
            f'页面对象不应包含stream! 内容片段: {obj_content[:200]}'
        )

        # 同时pikepdf也能正确解析
        pdf = open_pdf_from_path(result.path)
        page = pdf.pages[0]
        assert '/Type' in page, '页面对象无/Type'
        assert str(page.Type) == '/Page', f'类型错误: {page.Type}'
        pdf.close()

    print('  PASS: 页面对象是字典，非Stream')


def run_all_tests():
    """运行所有测试"""
    tests = [
        test_xref_entry_length,
        test_xref_entry_offsets,
        test_manual_pdf_no_smask,
        test_manual_pdf_lzw,
        test_manual_pdf_rle,
        test_manual_pdf_with_smask,
        test_pikepdf_builder,
        test_page_object_is_dictionary_not_stream,
    ]

    passed = 0
    failed = 0
    errors = []

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((test_fn.__name__, str(e)))
            print(f'  FAIL: {e}')

    print(f'\n{"="*60}')
    print(f'测试结果: {passed} passed, {failed} failed / {len(tests)} total')
    if errors:
        print('失败详情:')
        for name, err in errors:
            print(f'  - {name}: {err}')
    print(f'{"="*60}')
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
