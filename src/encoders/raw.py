"""RawEncoder: 无压缩原始RGB数据"""
from PIL import Image
from .base import Encoder, EncodeParams


class RawEncoder(Encoder):
    @property
    def name(self) -> str:
        return 'Raw'

    def encode(self, image: Image.Image) -> tuple[bytes, EncodeParams]:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        data = image.tobytes()
        params = EncodeParams(
            filter=None,           # 无滤波
            color_space='/DeviceRGB',
            bits_per_component=8,
            width=image.width,
            height=image.height,
            pre_compressed=False,  # 原始数据, save时会压缩
        )
        return data, params
