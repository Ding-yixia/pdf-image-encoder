"""透明度挖空效果: 在图像中心生成随机不规则透明区域

用于增强 PDF SMask 的透明视觉效果。

算法:
1. 在图像中心区域生成随机种子点
2. 通过多次叠加随机椭圆形+噪声产生不规则有机形状
3. 高斯模糊实现平滑边缘过渡
4. 阈值化确保挖空区域完全透明
"""

import random
import logging
import numpy as np
from PIL import Image, ImageFilter

log = logging.getLogger(__name__)


class TransparencyCutout:
    """图像中心随机挖空透明度效果

    对输入的 RGB/RGBA 图像在中心区域生成不规则透明孔洞,
    保持非挖空区域的原始透明度不变。
    """

    def __init__(self, seed: int | None = None):
        """
        Args:
            seed: 随机种子, None=每次不同
        """
        self.rng = random.Random(seed)

    def apply(
        self,
        image: Image.Image,
        cutout_ratio: float = 0.35,
        feather_radius: int | None = None,
    ) -> Image.Image:
        """在图像中心创建随机不规则透明挖空区域。

        Args:
            image: PIL Image (RGB或RGBA)
            cutout_ratio: 挖空区域占图像的比例 (0.1~0.5)
            feather_radius: 边缘羽化半径, None=自动计算

        Returns:
            RGBA模式的图像, 中心有不规则透明区域
        """
        w, h = image.size

        # 确保RGBA
        if image.mode == 'RGBA':
            rgba = image.copy()
        elif image.mode == 'RGB':
            rgba = image.convert('RGBA')
        else:
            rgba = image.convert('RGBA')

        # 生成随机不规则挖空蒙版
        mask = self._generate_organic_mask(w, h, cutout_ratio, feather_radius)

        # 叠加蒙版: mask=0处完全透明, mask=255处保持原始透明度
        r, g, b, a = rgba.split()
        alpha_arr = np.array(a, dtype=np.float32)
        mask_arr = np.array(mask, dtype=np.float32)

        # 取最小值: 既保留原始透明区域, 又添加挖空透明区域
        new_alpha = np.minimum(alpha_arr, mask_arr).astype(np.uint8)
        new_a = Image.fromarray(new_alpha, mode='L')

        result = Image.merge('RGBA', (r, g, b, new_a))
        log.debug(
            f'  挖空效果: {w}x{h}, cutout_ratio={cutout_ratio}, '
            f'透明像素={int(np.sum(new_alpha < 255))}'
        )
        return result

    def _generate_organic_mask(
        self,
        w: int,
        h: int,
        cutout_ratio: float,
        feather_radius: int | None,
    ) -> Image.Image:
        """生成中心不规则挖空蒙版。

        白色(255)=不透明, 黑色(0)=完全透明(挖空)。
        """
        # 计算中心区域边界 (图像中央约50%区域)
        cx, cy = w // 2, h // 2
        region_w = int(w * 0.6)
        region_h = int(h * 0.6)
        x0 = cx - region_w // 2
        y0 = cy - region_h // 2
        x1 = x0 + region_w
        y1 = y0 + region_h

        # 在中心区域创建随机种子图层
        # 使用多个随机噪声圆叠加产生不规则形状
        blob_count = self.rng.randint(4, 9)
        canvas = np.zeros((h, w), dtype=np.float32)
        base_radius = min(w, h) * cutout_ratio * 0.4

        for _ in range(blob_count):
            # 随机位置 (偏向中心)
            bx = self.rng.randint(
                int(w * 0.25), int(w * 0.75)
            )
            by = self.rng.randint(
                int(h * 0.25), int(h * 0.75)
            )
            # 随机椭圆大小和形状
            rx = base_radius * self.rng.uniform(0.5, 1.5)
            ry = base_radius * self.rng.uniform(0.5, 1.5)
            # 随机旋转
            angle = self.rng.uniform(0, 360)
            # 随机不透明度
            opacity = self.rng.uniform(0.4, 0.9)

            blob = self._make_ellipse(w, h, bx, by, rx, ry, angle)
            # 边缘添加随机扰动
            canvas += blob * opacity

        # 裁剪到 [0, 1]
        canvas = np.clip(canvas, 0, 1)

        # 添加 Perlin-like 噪声让边缘更自然
        noise = self._generate_noise(w, h, scale=min(w, h) * 0.05)
        canvas = np.clip(canvas + noise * 0.15, 0, 1)

        # 高斯模糊 → 平滑过渡
        if feather_radius is None:
            feather_radius = max(int(min(w, h) * 0.03), 3)
        blur_radius = max(feather_radius, 3)

        canvas_img = Image.fromarray((canvas * 255).astype(np.uint8), mode='L')
        canvas_img = canvas_img.filter(
            ImageFilter.GaussianBlur(radius=blur_radius)
        )

        # 阈值化: 挖空区域变为纯黑(0), 非挖空区域保持纯白(255)
        # 阈值在中间值让边缘自然过渡
        threshold = 180
        mask = canvas_img.point(lambda p: 0 if p < threshold else 255)

        # 最终轻微模糊让边缘更自然
        mask = mask.filter(ImageFilter.GaussianBlur(radius=2))

        return mask

    def _make_ellipse(
        self, w: int, h: int,
        cx: float, cy: float,
        rx: float, ry: float,
        angle: float,
    ) -> np.ndarray:
        """生成旋转椭圆渐变层。"""
        y, x = np.ogrid[:h, :w]
        theta = np.radians(angle)
        cos_a, sin_a = np.cos(theta), np.sin(theta)

        dx = x - cx
        dy = y - cy
        x_rot = dx * cos_a + dy * sin_a
        y_rot = -dx * sin_a + dy * cos_a

        dist = (x_rot / rx) ** 2 + (y_rot / ry) ** 2
        # 平滑衰减
        blob = np.exp(-dist * 0.5)
        return blob.astype(np.float32)

    def _generate_noise(
        self, w: int, h: int, scale: float = 10.0
    ) -> np.ndarray:
        """生成简单噪声场 (近似Perlin效果)。"""
        # 低分辨率随机场 → PIL放大上采样 → 平滑
        small_w = max(int(w / scale), 2)
        small_h = max(int(h / scale), 2)

        small = np.random.uniform(0, 255, (small_h, small_w)).astype(np.uint8)
        small_img = Image.fromarray(small, mode='L')
        noise_img = small_img.resize((w, h), Image.BILINEAR)
        noise = np.array(noise_img, dtype=np.float32)

        # 归一化到 [-1, 1]
        noise = noise / 127.5 - 1.0
        return noise.astype(np.float32)


def apply_cutout(image: Image.Image, **kwargs) -> Image.Image:
    """快捷函数: 对图像应用随机挖空效果。"""
    effect = TransparencyCutout()
    return effect.apply(image, **kwargs)
