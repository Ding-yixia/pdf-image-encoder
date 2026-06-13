# PDF编码示例归档

## 概况

- **源图像**: 365张来自 D:\wallpapers + 9张透明度测试图
- **编码格式**: 8种 (Raw/Flate/DCT/JPX/CCITT/RLE/LZW/**Alpha**)
- **PDF总数**: 2,564个
- **总大小**: ~106 MB (分割为11个ZIP, 每个≤20MB)

## 目录结构

```
archives/
├── Raw/
│   ├── part01.zip  (19MB, 187个PDF)
│   └── part02.zip  ( 3MB, 178个PDF)
├── Flate/
│   ├── part01.zip  (19MB, 187个PDF)
│   └── part02.zip  ( 3MB, 178个PDF)
├── DCT/
│   └── part01.zip  ( 2MB, 365个PDF)
├── JPX/
│   └── part01.zip  (11MB, 365个PDF)
├── CCITT/
│   └── part01.zip  ( 1MB, 365个PDF)
├── RLE/
│   ├── part01.zip  (19MB, 187个PDF)
│   └── part02.zip  ( 2MB, 178个PDF)
└── LZW/
    └── part01.zip  (19MB, 365个PDF)
└── Alpha/
    └── part01.zip  ( 1MB,   9个PDF)  ← 透明度测试
```

## 编码效率

| 编码 | PDF大小 | 压缩率 |
|------|---------|--------|
| DCT (JPEG) | 2.4 MB | **8.3%** |
| CCITT (G4) | 1.3 MB | **4.5%** |
| JPX (JPEG2000) | 11.9 MB | **41%** |
| LZW | 19.4 MB | **67%** |
| Raw | 23.9 MB | 100% (基线) |
| Flate | 23.9 MB | 100% |
| RLE | 22.0 MB | 92% |

## 生成命令

```bash
python run.py --input D:\wallpapers --encoders all --count 0 --size 200 -q 85
```
