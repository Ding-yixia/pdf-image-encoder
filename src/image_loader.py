"""图像输入模块: 扫描文件夹, 过滤图像文件"""
import logging
from pathlib import Path

log = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}


def scan_images(input_dir: Path, max_count: int = 0) -> list[Path]:
    """
    扫描指定目录中的图像文件。

    Args:
        input_dir: 输入目录
        max_count: 最大返回数(0=全部)

    Returns:
        排序后的图像文件路径列表
    """
    if not input_dir.exists():
        log.error(f'输入目录不存在: {input_dir}')
        return []

    images = []
    for ext in SUPPORTED_EXTENSIONS:
        images.extend(input_dir.glob(f'*{ext}'))
        images.extend(input_dir.glob(f'*{ext.upper()}'))

    images = sorted(set(images))  # 去重+排序

    if not images:
        log.warning(f'在 {input_dir} 中未找到支持的图像文件')
        log.info(f'支持的扩展名: {", ".join(SUPPORTED_EXTENSIONS)}')
        return []

    if 0 < max_count < len(images):
        images = images[:max_count]

    log.info(f'扫描到 {len(images)} 个图像文件')
    return images
