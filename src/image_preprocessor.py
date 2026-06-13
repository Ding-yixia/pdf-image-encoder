"""图像预处理模块: 缩放, 颜色空间转换, 质量优化"""
import logging
from pathlib import Path

from PIL import Image

log = logging.getLogger(__name__)


class ImagePreprocessor:
    """图像预处理器: 统一缩放和格式标准化"""

    def __init__(self, max_size: int = 300, jpeg_quality: int = 90):
        """
        Args:
            max_size: 最大边长(px), None=不缩放
            jpeg_quality: 中间JPEG保存质量
        """
        self.max_size = max_size
        self.jpeg_quality = jpeg_quality

    def process(self, image_path: Path, mode: str = 'RGB') -> Image.Image:
        """
        加载并预处理图像。

        处理步骤:
        1. 加载图像
        2. 缩放到max_size (保持宽高比)
        3. 确保指定模式

        Args:
            image_path: 图像文件路径
            mode: 目标模式, 'RGB' 或 'RGBA'

        Returns:
            PIL Image
        """
        img = Image.open(image_path)
        orig_size = img.size
        log.debug(f'  加载: {image_path.name} ({orig_size[0]}x{orig_size[1]})')

        # 缩放
        if self.max_size and (img.width > self.max_size or img.height > self.max_size):
            img.thumbnail((self.max_size, self.max_size), Image.LANCZOS)
            log.debug(f'  缩放至: {img.size[0]}x{img.size[1]}')

        # 转换为目标模式
        if img.mode != mode:
            img = img.convert(mode)

        return img
