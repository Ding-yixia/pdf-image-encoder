# PDF编码示例归档

## 概况

- **源图像**: 365张 (D:\wallpapers)
- **编码格式**: 9种 (Raw/Flate/DCT/JPX/CCITT/RLE/LZW/Alpha/**JBIG2**)
- **PDF总数**: 3,285个
- **总大小**: ~120 MB (分割为13个ZIP, 每个≤20MB)

## 目录结构

```
archives/
├── Raw/     part01.zip, part02.zip  (23MB)
├── Flate/   part01.zip, part02.zip  (23MB)
├── DCT/     part01.zip              ( 2MB)
├── JPX/     part01.zip              (11MB)
├── CCITT/   part01.zip              ( 1MB)
├── RLE/     part01.zip, part02.zip  (21MB)
├── LZW/     part01.zip              (19MB)
├── Alpha/   part01.zip              (19MB)
└── JBIG2/   part01.zip              ( 0.5MB) ← NEW
```

## 编码效率

| 编码 | PDF大小 | 压缩率 |
|------|---------|--------|
| **JBIG2** | 0.5 MB | **1.7%** 🏆 |
| **DCT** (JPEG) | 2.4 MB | **8.3%** |
| **CCITT** (G4) | 1.3 MB | **4.5%** |
| **JPX** (JPEG2000) | 11.9 MB | **41%** |
| **LZW** | 19.4 MB | **67%** |
| **Alpha** | 19.5 MB | **67%** |
| **Raw** | 23.9 MB | 100% (基线) |
| **Flate** | 23.9 MB | 100% |
| **RLE** | 22.0 MB | 92% |

## 生成命令

```bash
python run.py --input D:\wallpapers --encoders all --count 0 --size 200 -q 85
```
