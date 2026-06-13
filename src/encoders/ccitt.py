"""CCITTEncoder: CCITTFaxDecode (Group 4) — 二值图像专用

流程: 灰度化 → 二值化 → TIFF CCITT Group4编码 → 提取CCITT流
"""
from io import BytesIO
from PIL import Image
from .base import Encoder, EncodeParams


class CCITTEncoder(Encoder):
    @property
    def name(self) -> str:
        return 'CCITT'

    def encode(self, image: Image.Image) -> tuple[bytes, EncodeParams]:
        # 转灰度 → 二值化 (阈值128)
        if image.mode != 'L':
            image = image.convert('L')
        img_bw = image.point(lambda x: 0 if x < 128 else 255, '1')

        # 通过TIFF保存获取CCITT Group4编码数据
        buf = BytesIO()
        img_bw.save(buf, format='TIFF', compression='group4')
        tiff_data = buf.getvalue()

        # 从TIFF字节中提取CCITT strip数据
        raw_ccitt = _extract_ccitt_strip(tiff_data)

        params = EncodeParams(
            filter='/CCITTFaxDecode',
            color_space='/DeviceGray',
            bits_per_component=1,
            width=image.width,
            height=image.height,
            pre_compressed=True,
            decode_parms={
                '/K': -1,
                '/Columns': image.width,
                '/Rows': image.height,
                '/BlackIs1': False,
            },
        )
        return raw_ccitt, params


def _extract_ccitt_strip(tiff_data: bytes) -> bytes:
    """从TIFF字节中提取CCITT Group 4的strip数据(精确长度)。"""
    buf = BytesIO(tiff_data)
    with Image.open(buf) as tiff:
        # 优先: 通过StripOffsets+StripByteCounts获取精确数据
        try:
            tag_offsets = tiff.tag_v2[273]
            tag_counts = tiff.tag_v2.get(279)
            if isinstance(tag_offsets, (tuple, list)) and len(tag_offsets) > 0:
                offset = tag_offsets[0]
                cnt = tag_counts[0] if isinstance(tag_counts, (tuple, list)) and tag_counts else len(tiff_data) - offset
                return tiff_data[offset:offset + cnt]
        except (KeyError, IndexError):
            pass

        # 次优: 通过tile偏移量
        if hasattr(tiff, 'tile') and tiff.tile:
            for tile in tiff.tile:
                if tile[0] in ('ccitt', 'group4', 't42'):
                    offset = tile[2]
                    try:
                        cnt = tiff.tag_v2[279]
                        if isinstance(cnt, (tuple, list)):
                            return tiff_data[offset:offset + cnt[0]]
                    except KeyError:
                        pass
                    return tiff_data[offset:]

        # fallback
        return tiff.tobytes()
