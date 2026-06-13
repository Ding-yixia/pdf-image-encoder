#!/usr/bin/env python3
"""生成带透明度的测试图像，供Alpha编码器使用。

生成两种风格:
1. text_overlay: 文本 + 半透明图像叠加 (文字可见, 背景半透明)
2. hole_punch:  图像中间挖孔 (圆形镂空, 露出底层文字)
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
import os

OUTPUT = Path(__file__).parent / 'alpha_test_images'
os.makedirs(OUTPUT, exist_ok=True)


def create_text_overlay(id: int, w: int = 400, h: int = 300) -> Path:
    """生成: 底层文字 + 半透明图像叠加的PNG"""
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 画彩色渐变背景 (半透明)
    for y in range(h):
        r = int(255 * y / h)
        g = int(128 * (1 - y / h))
        b = int(255 * abs(0.5 - y / h) * 2)
        for x in range(w):
            alpha = 200  # 半透明
            if (x // 40 + y // 40) % 2 == 0:
                alpha = 100  # 棋盘格更低透明度
            draw.point((x, y), fill=(r, g, b, alpha))

    # 画一些几何图形
    draw.ellipse([50, 50, w-50, h-50], outline=(255, 255, 255, 180), width=3)
    draw.rectangle([100, 80, w-100, h-80], outline=(255, 255, 180, 120), width=2)

    path = OUTPUT / f'alpha_overlay_{id}.png'
    img.save(path)
    print(f'  [overlay] {path.name} ({img.size})')
    return path


def create_hole_punch(id: int, w: int = 400, h: int = 300) -> Path:
    """生成: 图像中间圆形挖孔 + 孔洞中透出文字"""
    # 创建底层: 彩色渐变条
    base = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base)

    # 填充彩虹色
    for x in range(w):
        r = int(255 * x / w)
        g = int(255 * (1 - x / w))
        b = int(128)
        draw.line([(x, 0), (x, h)], fill=(r % 256, g % 256, b, 220))

    # 创建圆形挖孔: 中间区域全透明
    hole_mask = Image.new('L', (w, h), 255)  # 全白(不透明)
    hole_draw = ImageDraw.Draw(hole_mask)
    cx, cy = w // 2, h // 2
    radius = min(w, h) // 3
    hole_draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius],
                      fill=0)  # 黑色=全透明

    # 在孔洞周围画一些装饰
    hole_draw.rectangle([20, 20, w-20, h-20], outline=200, width=2)

    # 应用蒙版: base中孔洞区域变透明
    result = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    result = Image.composite(base, Image.new('RGBA', (w, h), (0, 0, 0, 0)),
                             hole_mask)

    # 在孔洞边缘加一些半透明点
    dot_draw = ImageDraw.Draw(result)
    for angle in range(0, 360, 30):
        import math
        dx = int(cx + (radius - 5) * math.cos(math.radians(angle)))
        dy = int(cy + (radius - 5) * math.sin(math.radians(angle)))
        dot_draw.ellipse([dx-3, dy-3, dx+3, dy+3], fill=(255, 255, 0, 150))

    path = OUTPUT / f'alpha_hole_{id}.png'
    result.save(path)
    print(f'  [hole]  {path.name} ({result.size})')
    return path


def create_gradient_alpha(id: int, w: int = 400, h: int = 300) -> Path:
    """生成: 从左到右渐变透明度的图像"""
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 填充竖向条纹, 每列透明度从左(255)到右(0)渐变
    for x in range(w):
        alpha = int(255 * (1 - x / w))
        r = int(255 * x / w)
        draw.line([(x, 0), (x, h)], fill=(r, 128, 255 - r, alpha))

    path = OUTPUT / f'alpha_gradient_{id}.png'
    img.save(path)
    print(f'  [gradient] {path.name} ({img.size})')
    return path


def main():
    print(f'生成透明度测试图像...')
    print(f'输出目录: {OUTPUT}')

    images = []
    for i in range(1, 4):
        images.append(create_text_overlay(i))
        images.append(create_hole_punch(i))
        images.append(create_gradient_alpha(i))

    print(f'\n完成! 共生成 {len(images)} 个RGBA PNG图像')
    for p in images:
        sz = p.stat().st_size // 1024
        print(f'  {p.name:40s} {sz:>4d} KB')
    return images


if __name__ == '__main__':
    main()
