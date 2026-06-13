"""FlateEncoder: FlateDecode (zlib/Deflate)"""
from PIL import Image
from .base import Encoder, EncodeParams


class FlateEncoder(Encoder):
    @property
    def name(self) -> str:
        return 'Flate'

    def encode(self, image: Image.Image) -> tuple[bytes, EncodeParams]:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        data = image.tobytes()  # 原始数据, pikepdf会在save时+Filter压缩
        params = EncodeParams(
            filter='/FlateDecode',
            color_space='/DeviceRGB',
            bits_per_component=8,
            width=image.width,
            height=image.height,
            pre_compressed=False,
        )
        return data, params
