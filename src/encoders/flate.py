"""FlateEncoder: FlateDecode (zlib/Deflate) — 预压缩RGB数据"""
import zlib
from PIL import Image
from .base import Encoder, EncodeParams


class FlateEncoder(Encoder):
    @property
    def name(self) -> str:
        return 'Flate'

    def encode(self, image: Image.Image) -> tuple[bytes, EncodeParams]:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        raw = image.tobytes()
        # 必须预压缩: pikepdf save(compress_streams=False) 不会自动压缩
        data = zlib.compress(raw)
        params = EncodeParams(
            filter='/FlateDecode',
            color_space='/DeviceRGB',
            bits_per_component=8,
            width=image.width,
            height=image.height,
            pre_compressed=True,
        )
        return data, params
