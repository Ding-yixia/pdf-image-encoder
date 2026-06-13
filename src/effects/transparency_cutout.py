"""透明度挖孔效果: 在图像中心散落若干小圆孔/三角孔/多边形孔

用于增强 PDF SMask 的透明视觉效果。

算法:
1. 在图像中心区域随机散布 N 个孔位
2. 每个孔随机选择形状: 圆形 / 三角形 / 多边形(4~8边)
3. 每个孔大小随机, 位置微偏移, 轻微旋转避免呆板
4. 小半径高斯模糊让边缘自然过渡
5. 阈值化确保孔内完全透明, 孔外保持不透明
"""

import random
import logging
import math
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

log = logging.getLogger(__name__)


class TransparencyCutout:
    """图像中心随机多孔挖空透明度效果

    在图像中心区域散布若干独立的小孔(圆形/三角形/多边形),
    每个孔完全透明, 孔之间互不连通(或少量重叠),
    保持非孔区域的原始透明度不变。
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
        hole_count: int | None = None,
        hole_min_ratio: float = 0.03,
        hole_max_ratio: float = 0.12,
        feather_radius: int = 3,
    ) -> Image.Image:
        """在图像中心区域散布多个小孔。

        Args:
            image: PIL Image (RGB或RGBA)
            hole_count: 孔数量, None=自动(8~20)
            hole_min_ratio: 单个孔最小半径占图像短边的比例
            hole_max_ratio: 单个孔最大半径占图像短边的比例
            feather_radius: 孔边缘羽化半径(px), 建议 2~5

        Returns:
            RGBA模式的图像, 中心区域散布若干透明孔
        """
        w, h = image.size
        short_side = min(w, h)

        # 确保RGBA
        if image.mode == 'RGBA':
            rgba = image.copy()
        elif image.mode == 'RGB':
            rgba = image.convert('RGBA')
        else:
            rgba = image.convert('RGBA')

        # 自动孔数
        if hole_count is None:
            hole_count = self.rng.randint(8, 20)

        # 生成多孔蒙版
        mask = self._generate_multi_hole_mask(
            w, h, hole_count, hole_min_ratio, hole_max_ratio, feather_radius
        )

        # 叠加蒙版
        r, g, b, a = rgba.split()
        alpha_arr = np.array(a, dtype=np.float32)
        mask_arr = np.array(mask, dtype=np.float32)

        # 取最小值: 孔区域变透明, 保留原始透明区域
        new_alpha = np.minimum(alpha_arr, mask_arr).astype(np.uint8)
        new_a = Image.fromarray(new_alpha, mode='L')

        result = Image.merge('RGBA', (r, g, b, new_a))
        transparent_px = int(np.sum(new_alpha < 255))
        log.debug(
            f'  挖孔效果: {w}x{h}, {hole_count}孔, '
            f'透明像素={transparent_px} '
            f'({transparent_px / new_alpha.size * 100:.1f}%)'
        )
        return result

    def _generate_multi_hole_mask(
        self,
        w: int,
        h: int,
        hole_count: int,
        min_ratio: float,
        max_ratio: float,
        feather: int,
    ) -> Image.Image:
        """生成多孔蒙版。

        白色(255)=不透明, 黑色(0)=孔(透明)。
        """
        short_side = min(w, h)
        min_r = int(short_side * min_ratio)
        max_r = int(short_side * max_ratio)

        # 全白画布
        mask = Image.new('L', (w, h), 255)
        draw = ImageDraw.Draw(mask)

        # 中心区域内随机散布孔
        # 约束在中心 60% 区域内, 避免挖到边缘
        cx, cy = w // 2, h // 2
        spread_w = int(w * 0.55)
        spread_h = int(h * 0.55)

        for i in range(hole_count):
            # 随机孔心位置 (中心区域)
            px = self.rng.randint(cx - spread_w // 2, cx + spread_w // 2)
            py = self.rng.randint(cy - spread_h // 2, cy + spread_h // 2)

            # 随机半径
            radius = self.rng.randint(min_r, max_r)

            # 随机形状
            shape_type = self.rng.choice(['circle', 'triangle', 'polygon'])
            rotation = self.rng.uniform(0, 360)

            if shape_type == 'circle':
                self._draw_circle(draw, px, py, radius)
            elif shape_type == 'triangle':
                self._draw_polygon(draw, px, py, radius, 3, rotation)
            else:
                sides = self.rng.randint(4, 8)
                self._draw_polygon(draw, px, py, radius, sides, rotation)

        # 高斯模糊让边缘自然
        mask = mask.filter(ImageFilter.GaussianBlur(radius=feather))

        # 阈值化: 孔内部纯黑, 外部纯白
        # 阈值 128 取中位, 让羽化区域半透明
        mask = mask.point(lambda p: 0 if p < 128 else 255)

        # 极轻微模糊让锯齿平滑
        mask = mask.filter(ImageFilter.GaussianBlur(radius=1))

        return mask

    def _draw_circle(
        self, draw: ImageDraw.Draw, cx: int, cy: int, r: int
    ) -> None:
        """在蒙版上绘制黑色圆形孔。"""
        bbox = (cx - r, cy - r, cx + r, cy + r)
        draw.ellipse(bbox, fill=0)

    def _draw_polygon(
        self,
        draw: ImageDraw.Draw,
        cx: int, cy: int,
        radius: int,
        sides: int,
        rotation: float,
    ) -> None:
        """在蒙版上绘制黑色正多边形孔。"""
        vertices = []
        angle_offset = math.radians(rotation)
        start_angle = angle_offset - math.pi / 2  # 从顶部开始

        for i in range(sides):
            angle = start_angle + 2 * math.pi * i / sides
            vx = cx + radius * math.cos(angle)
            vy = cy + radius * math.sin(angle)
            vertices.append((vx, vy))

        draw.polygon(vertices, fill=0)


def apply_cutout(image: Image.Image, **kwargs) -> Image.Image:
    """快捷函数: 对图像应用随机多孔挖空效果。"""
    effect = TransparencyCutout()
    return effect.apply(image, **kwargs)
