"""CCITTEncoder: CCITTFaxDecode (Group 4) — 二值图像专用"""
from io import BytesIO
from PIL import Image
from .base import Encoder, EncodeParams


class CCITTEncoder(Encoder):
    @property
    def name(self) -> str:
        return 'CCITT'

    def encode(self, image: Image.Image) -> tuple[bytes, EncodeParams]:
        # 转灰度 → 二值化
        if image.mode != 'L':
            image = image.convert('L')
        img_bw = image.point(lambda x: 0 if x < 128 else 255, '1')

        # 通过TIFF保存获取CCITT Group4数据
        buf = BytesIO()
        img_bw.save(buf, format='TIFF', compression='group4')
        tiff_data = buf.getvalue()

        # 从TIFF中提取图像strip数据
        buf.seek(0)
        with Image.open(buf) as tiff:
            if hasattr(tiff, 'tile') and tiff.tile:
                for tile in tiff.tile:
                    if tile[0] == 'ccitt':
                        offset = tile[2]
                        with open(buf.name, 'rb') as f:
                            f.seek(offset)
                            raw_ccitt = f.read()
                        break
                else:
                    raw_ccitt = tiff.tobytes()
            else:
                raw_ccitt = tiff.tobytes()

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
