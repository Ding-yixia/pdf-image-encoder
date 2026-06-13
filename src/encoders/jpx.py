"""JPXEncoder: JPXDecode (JPEG2000)"""
from io import BytesIO
from PIL import Image
from .base import Encoder, EncodeParams


class JPXEncoder(Encoder):
    def __init__(self, quality: float = 0.5):
        self.quality = quality  # 0.0-1.0

    @property
    def name(self) -> str:
        return 'JPX'

    def encode(self, image: Image.Image) -> tuple[bytes, EncodeParams]:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        buf = BytesIO()
        try:
            image.save(buf, format='JPEG2000', quality_mode='rates',
                       quality=self.quality)
        except Exception:
            buf = BytesIO()
            image.save(buf, format='JPEG2000')
        data = buf.getvalue()
        params = EncodeParams(
            filter='/JPXDecode',
            color_space='/DeviceRGB',
            bits_per_component=8,
            width=image.width,
            height=image.height,
            pre_compressed=True,
        )
        return data, params
