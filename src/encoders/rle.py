"""RLEEncoder: RunLengthDecode — PDF游程编码 (§7.4.5)"""
from PIL import Image
from .base import Encoder, EncodeParams


class _RLE:
    """RunLength编码器实现"""

    @staticmethod
    def encode(data: bytes) -> bytes:
        out = bytearray()
        i = 0
        while i < len(data):
            # 查找重复序列 (≥3)
            run = 1
            while i + run < len(data) and data[i + run] == data[i] and run < 128:
                run += 1

            if run >= 3:
                out.append(257 - run)  # length byte
                out.append(data[i])
                i += run
            else:
                # 非重复: 收集直到重复或满128
                start = i
                j = i + 1
                while j < min(i + 128, len(data)):
                    r2 = 1
                    while j + r2 < len(data) and data[j + r2] == data[j] and r2 < 128:
                        r2 += 1
                    if r2 >= 3:
                        break
                    j += 1
                lit_len = j - start
                out.append(lit_len - 1)
                out.extend(data[start:j])
                i = j

        out.append(0x80)  # EOD
        return bytes(out)


class RLEEncoder(Encoder):
    @property
    def name(self) -> str:
        return 'RLE'

    def encode(self, image: Image.Image) -> tuple[bytes, EncodeParams]:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        raw = image.tobytes()
        data = _RLE.encode(raw)
        params = EncodeParams(
            filter='/RunLengthDecode',
            color_space='/DeviceRGB',
            bits_per_component=8,
            width=image.width,
            height=image.height,
            pre_compressed=True,
        )
        return data, params
