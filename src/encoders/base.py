"""编码器基类和参数类型"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from PIL import Image


@dataclass
class EncodeParams:
    """编码参数: 传递给PDF构造器的元数据"""
    filter: Optional[str]          # PDF Filter名称, None=无滤波
    color_space: str                # /DeviceRGB, /DeviceGray, /DeviceCMYK
    bits_per_component: int         # 1, 8
    width: int
    height: int
    pre_compressed: bool = False    # True=数据已压缩, save时不额外压缩
    decode_parms: Optional[dict] = None  # CCITT等需要的解码参数
    smask: Optional[bytes] = None   # Alpha通道数据(SMask灰度图), None=无透明度
    complete_pdf: Optional[bytes] = None  # 完整PDF字节(JBIG2直接用MuPDF生成)


class Encoder(ABC):
    """编码器基类: 所有PDF图像编码的统一接口"""

    @property
    @abstractmethod
    def name(self) -> str:
        """编码器名称, 如 'LZW', 'DCT'"""

    @abstractmethod
    def encode(self, image: Image.Image) -> tuple[bytes, EncodeParams]:
        """
        对PIL Image进行编码。

        Args:
            image: RGB或灰度PIL图像

        Returns:
            (编码后的二进制数据, 编码参数)
        """
