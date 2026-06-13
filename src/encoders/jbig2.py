"""JBIG2Encoder: JBIG2Decode — 基于Flate的1-bit编码

灰度化 → 二值化 → 1-bit像素数据 → FlateDecode压缩 → PDF嵌入
"""
import zlib
from PIL import Image
from .base import Encoder, EncodeParams


class JBIG2Encoder(Encoder):
    """JBIG2编码器: 1-bit二值图像, Flate压缩"""

    @property
    def name(self) -> str:
        return 'JBIG2'

    def encode(self, image: Image.Image) -> tuple[bytes, EncodeParams]:
        # 灰度化 → 二值化 (阈值128)
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
