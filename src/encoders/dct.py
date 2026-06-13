"""DCTEncoder: DCTDecode (JPEG)"""
from io import BytesIO
from PIL import Image
from .base import Encoder, EncodeParams


class DCTEncoder(Encoder):
    def __init__(self, quality: int = 85):
        self.quality = quality

    @property
    def name(self) -> str:
        return 'DCT'

    def encode(self, image: Image.Image) -> tuple[bytes, EncodeParams]:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        buf = BytesIO()
        image.save(buf, format='JPEG', quality=self.quality, optimize=True)
        data = buf.getvalue()
        params = EncodeParams(
            filter='/DCTDecode',
            color_space='/DeviceRGB',
            bits_per_component=8,
            width=image.width,
            height=image.height,
            pre_compressed=True,  # JPEG已压缩
        )
        return data, params
