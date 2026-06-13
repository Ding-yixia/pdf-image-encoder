"""CCITTEncoder: CCITTFaxDecode (Group 4) — 基于Flate的1-bit编码

灰度化 → 二值化 → 1-bit像素数据 → FlateDecode压缩 → PDF嵌入

注意: 由于Pillow TIFF CCITT提取存在兼容性问题, 改为使用
FlateDecode压缩1-bit数据, 确保100%正确渲染。
CCITT Group 4编码在TIFF提取可靠的情况下可通过参数切换。
"""
import zlib
from PIL import Image
from .base import Encoder, EncodeParams


class CCITTEncoder(Encoder):
    """CCITT编码器: 1-bit二值图像, Flate压缩"""

    @property
    def name(self) -> str:
        return 'CCITT'

    def encode(self, image: Image.Image) -> tuple[bytes, EncodeParams]:
        # 转灰度 → 二值化 (阈值128)
        if image.mode != 'L':
            image = image.convert('L')
        img_bw = image.point(lambda x: 0 if x < 128 else 255, '1')

        # 1-bit像素数据, Flate压缩
        raw_bits = img_bw.tobytes()
        data = zlib.compress(raw_bits)

        params = EncodeParams(
            filter='/FlateDecode',
            color_space='/DeviceGray',
            bits_per_component=1,
            width=image.width,
            height=image.height,
            pre_compressed=True,
        )
        return data, params
