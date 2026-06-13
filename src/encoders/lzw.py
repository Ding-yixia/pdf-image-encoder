"""LZWEncoder: LZWDecode — 使用imagecodecs库

PDF标准不支持通过pikepdf直接写入LZW编码的图像,
因为pikepdf在save()时会自动将/LZWDecode替换为/FlateDecode。
因此本编码器通过手动构造PDF字节来实现。

依赖: pip install imagecodecs
"""
from PIL import Image
from .base import Encoder, EncodeParams


class LZWEncoder(Encoder):
    """LZW编码器包装: 使用imagecodecs库的C实现"""

    @property
    def name(self) -> str:
        return 'LZW'

    def encode(self, image: Image.Image) -> tuple[bytes, EncodeParams]:
        try:
            from imagecodecs import lzw_encode
        except ImportError:
            raise RuntimeError(
                "LZWEncoder需要imagecodecs库: pip install imagecodecs")

        if image.mode != 'RGB':
            image = image.convert('RGB')
        raw = image.tobytes()
        data = lzw_encode(raw)
        params = EncodeParams(
            filter='/LZWDecode',
            color_space='/DeviceRGB',
            bits_per_component=8,
            width=image.width,
            height=image.height,
            pre_compressed=True,  # LZW已压缩
        )
        return data, params
