"""AlphaEncoder: 带透明度(Alpha通道)的图像 → RGB + SMask

PDF透明实现原理:
- RGB图像作为主图像, 带 /SMask 引用
- SMask是一张灰度图像: 白色(255)=不透明, 黑色(0)=完全透明
- PDF阅读器将SMask与RGB图像合成渲染

本编码器:
1. 输入RGBA图像 → 分离为RGB(主) + Alpha(SMask)
2. 两张图像各自编码(LZW压缩)放入同一个PDF
3. PDF中主图像引用SMask
"""
from PIL import Image
from .base import Encoder, EncodeParams


class AlphaEncoder(Encoder):
    """透明度图像编码器: 将RGBA拆为 RGB Image + SMask"""

    @property
    def name(self) -> str:
        return 'Alpha'

    def encode(self, image: Image.Image) -> tuple[bytes, EncodeParams]:
        """编码RGBA图像。返回RGB主图像数据, smask传递蒙版。"""
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        r, g, b, a = image.split()
        rgb = Image.merge('RGB', (r, g, b))

        from imagecodecs import lzw_encode
        rgb_data = lzw_encode(rgb.tobytes())
        alpha_data = lzw_encode(a.tobytes())

        params = EncodeParams(
            filter='/LZWDecode',
            color_space='/DeviceRGB',
            bits_per_component=8,
            width=image.width,
            height=image.height,
            pre_compressed=True,
            smask=alpha_data,  # SMask灰度数据(LZW)
        )
        return rgb_data, params

    def verify(self, rgb_data: bytes, alpha_data: bytes,
               width: int, height: int) -> bool:
        """验证RGB和Alpha数据解码后尺寸正确"""
        from imagecodecs import lzw_decode
        try:
            rgb_dec = lzw_decode(rgb_data)
            alpha_dec = lzw_decode(alpha_data)
            expected_rgb = width * height * 3
            expected_a = width * height
            return len(rgb_dec) == expected_rgb and len(alpha_dec) == expected_a
        except Exception:
            return False
