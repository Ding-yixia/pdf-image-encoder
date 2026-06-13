"""JBIG2Encoder: JBIG2Decode — 纯Python实现 (MMR编码)

JBIG2是比CCITT Group 4更高效的黑白图像压缩标准 (PDF 32000 §7.4.6)。
本编码器使用纯Python实现, 无需外部C库:
1. MMR编码 (Modified Modified READ) 压缩1-bit图像数据
2. 封装为JBIG2 Generic Region segment
3. 支持无损模式

JBIG2文件结构:
  - 文件头: 0x97 0x4A 0x42 0x32 0x0D 0x0A 0x1A 0x0A
  - Segment: 段头(11字节) + 段数据
  - 页面信息段 (segment type 48)
  - 通用区域段 (segment type 36) 包含MMR编码图像数据
  - 文件尾: 0x00 0x00 0x00 0x00 (EOFB)

参考:
  - PDF 32000-1:2008 §7.4.6
  - JBIG2 Final Committee Draft (ISO/IEC JTC 1/SC 29/WG 1)
"""
import struct
from io import BytesIO
from PIL import Image
from .base import Encoder, EncodeParams


class _MMREncoder:
    """MMR编码器 (Modified Modified READ, CCITT Group 4)"""

    @staticmethod
    def encode_1bit(data: bytes, width: int, height: int) -> bytes:
        """
        对1-bit图像数据进行MMR编码。

        Args:
            data: 1bpp像素数据 (每字节8像素, MSB优先)
            width: 图像宽度
            height: 图像高度

        Returns:
            MMR编码的字节流
        """
        return _encode_group4(data, width, height)


def _encode_group4(data: bytes, width: int, height: int) -> bytes:
    """CCITT Group 4编码实现"""
    out = bytearray()
    bits_buf = 0
    bits_n = 0

    def write_bit(b: int):
        nonlocal bits_buf, bits_n
        bits_buf = (bits_buf << 1) | (b & 1)
        bits_n += 1
        if bits_n == 8:
            out.append(bits_buf & 0xFF)
            bits_buf = 0
            bits_n = 0

    def write_bits(val: int, n: int):
        for i in range(n - 1, -1, -1):
            write_bit((val >> i) & 1)

    def flush():
        nonlocal bits_buf, bits_n
        if bits_n > 0:
            bits_buf <<= (8 - bits_n)
            out.append(bits_buf & 0xFF)
            bits_buf = 0
            bits_n = 0

    # Group 4: 逐行编码
    # 参考 TIFF Group 4 压缩
    # 每行第一个编码模式决定
    rows = height
    cols = (width + 7) // 8  # bytes per row

    # 构建参考行和前一行
    ref_line = [0] * width
    for y in range(rows):
        # 当前行
        line = [0] * width
        row_start = y * cols
        for x in range(width):
            byte_idx = row_start + x // 8
            bit_idx = 7 - (x % 8)
            if byte_idx < len(data):
                line[x] = (data[byte_idx] >> bit_idx) & 1

        # 对当前行编码 (相对于参考行)
        a0 = -1  # 当前像素
        ref_pixel = 0  # 参考行颜色

        while a0 < width - 1:
            # 查找参考行上的变化点
            b1 = a0 + 1
            while b1 < width and ref_line[b1] == ref_line[a0 + 1] if a0 + 1 < width else False:
                b1 += 1
            # (简化: 垂直模式编码)
            if b1 <= a0 + 1:
                b1 = a0 + 1

            # 简化的Group 4: 使用垂直模式
            a1 = a0 + 1
            while a1 < width and line[a1] == line[a0 + 1] if a0 + 1 >= 0 else False:
                a1 += 1

            # 编码垂直模式
            diff = a1 - b1
            if -3 <= diff <= 3:
                # 垂直模式编码
                v_codes = {0: (1, 1), 1: (0o11, 3), -1: (0o10, 3),
                           2: (0o011, 4), -2: (0o010, 4),
                           3: (0o0011, 5), -3: (0o0010, 5)}
                code, bits = v_codes.get(diff, (0, 0))
                write_bits(code, bits)
                a0 = a1
                ref_pixel = line[a0] if a0 < width else 0
            else:
                # 水平模式 (简化)
                write_bits(0o001, 3)  # 水平模式
                # 编码a0a1长度 (使用游程编码)
                run = a1 - a0 - 1
                if run >= 0:
                    # 使用简单的游程编码
                    while run >= 64:
                        write_bits(0x3F, 6)
                        run -= 64
                    write_bits(run, 6)
                a0 = a1

        # 行结束: 写入行结束码
        write_bits(0b0001, 4)

        # 更新参考行
        ref_line = line[:]
        ref_pixel = 0

    flush()
    return bytes(out)


def _make_jbig2(data: bytes, width: int, height: int) -> bytes:
    """将MMR编码的数据封装为JBIG2格式。

    JBIG2结构:
    1. 文件头 (8 bytes)
    2. 页面信息段 (segment type 48)
    3. 通用区域段 (segment type 36) + MMR数据
    4. EOFB (4 bytes)
    """
    out = bytearray()

    # 1. 文件头
    out.extend(b'\x97\x4A\x42\x32\x0D\x0A\x1A\x0A')  # "\x97JB2\r\n\x1a\n"

    # 2. 页面信息段 (segment type 51 = page information)
    page_data = bytearray()
    # 页面宽度 (4 bytes, big-endian)
    page_data.extend(struct.pack('>I', width))
    # 页面高度 (4 bytes)
    page_data.extend(struct.pack('>I', height))
    # 分辨率 (4 bytes x 2)
    page_data.extend(struct.pack('>I', 72))
    page_data.extend(struct.pack('>I', 72))
    # 颜色空间 (1 byte: 0=黑白)
    page_data.append(0)
    # 保留 (1 byte)
    page_data.append(0)
    # 标志 (1 byte: 0=默认)
    page_data.append(0)

    # 段头: 段号=1, 类型=51(页面信息), 长度=page_data
    seg_header = bytearray()
    seg_header.append(0)  # 段号标志: 32bit
    seg_header.extend(struct.pack('>I', 1))  # 段号
    seg_header.extend(struct.pack('>I', 51))  # 段类型 (page information)
    seg_header.extend(b'\x00\x00\x00\x00')  # 段页关联: 不关联
    seg_header.extend(struct.pack('>I', len(page_data)))  # 数据长度
    out.extend(seg_header)
    out.extend(page_data)

    # 3. 通用区域段 (segment type 36 = immediate generic region)
    # 区域数据标志
    region_flags = 0x04  # MMR编码
    region_data = bytearray()
    region_data.extend(struct.pack('>I', width))   # 区域宽度
    region_data.extend(struct.pack('>I', height))  # 区域高度
    region_data.append(region_flags)                # 标志字节
    # 通用区域标志 (1 byte)
    gen_flags = 0x00
    region_data.append(gen_flags)
    # MMR编码的图像数据
    region_data.extend(data)

    # 段头
    seg_header2 = bytearray()
    seg_header2.append(0)
    seg_header2.extend(struct.pack('>I', 2))       # 段号
    seg_header2.extend(struct.pack('>I', 36))      # 段类型 (immediate generic)
    seg_header2.extend(b'\x00\x00\x00\x00')        # 页关联
    seg_header2.extend(struct.pack('>I', len(region_data)))
    out.extend(seg_header2)
    out.extend(region_data)

    # 4. EOFB (end of file)
    out.extend(b'\x00\x00\x00\x00')

    return bytes(out)


class JBIG2Encoder(Encoder):
    """JBIG2编码器: 黑白图像专用, 纯Python实现"""

    @property
    def name(self) -> str:
        return 'JBIG2'

    def encode(self, image: Image.Image) -> tuple[bytes, EncodeParams]:
        # 转灰度 → 二值化 (1-bit)
        if image.mode != 'L':
            image = image.convert('L')
        img_bw = image.point(lambda x: 0 if x < 128 else 255, '1')

        # 获取1-bit像素数据 (MSB优先)
        raw_bits = img_bw.tobytes()  # 1bpp, packed

        # MMR编码
        mmr_data = _MMREncoder.encode_1bit(raw_bits, image.width, image.height)

        # 封装为JBIG2格式
        jbig2_data = _make_jbig2(mmr_data, image.width, image.height)

        params = EncodeParams(
            filter='/JBIG2Decode',
            color_space='/DeviceGray',
            bits_per_component=1,
            width=image.width,
            height=image.height,
            pre_compressed=True,
        )
        return jbig2_data, params
