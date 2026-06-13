# PDF Image Encoder

将指定文件夹中的图像转换为 **7种PDF图像编码格式** 的PDF文件。支持标准编码（JPEG/JPEG2000/CCITT/Flate）以及众多PDF库不支持的**非标准编码**（LZW/RLE/Raw）。

## 功能特性

- **7种编码格式**: Raw / Flate / DCT(JPEG) / JPX(JPEG2000) / CCITT(G4) / RLE / LZW
- **双策略PDF构造**:
  - 标准编码 → pikepdf 直接生成
  - 非标准编码(LZW/RLE/Raw) → 手动构造PDF字节，避开pikepdf自动替换Filter
- **图像预处理**: 自动缩放、颜色空间转换
- **CLI接口**: 支持输入文件夹、选择编码器、限制图像数量等
- **详细报告**: 生成编码效率对比报告

## 项目结构

```
pdf_image_encoder/
├── run.py                          # 单文件入口(支持PyInstaller打包)
├── src/
│   ├── main.py                     # CLI入口与参数解析
│   ├── config_manager.py           # YAML配置管理
│   ├── image_loader.py             # 图像文件夹扫描
│   ├── image_preprocessor.py       # 图像缩放/颜色转换
│   ├── encoders/                   # 7种编码器实现
│   │   ├── base.py                 # 抽象基类
│   │   ├── raw.py                  # 无压缩
│   │   ├── flate.py                # FlateDecode (zlib)
│   │   ├── dct.py                  # DCTDecode (JPEG)
│   │   ├── jpx.py                  # JPXDecode (JPEG2000)
│   │   ├── ccitt.py                # CCITTFaxDecode (G4)
│   │   ├── rle.py                  # RunLengthDecode
│   │   └── lzw.py                  # LZWDecode (imagecodecs)
│   ├── pdf/                        # PDF构造层
│   │   ├── objects.py              # PDF对象序列化
│   │   ├── xref.py                 # 交叉引用表
│   │   └── builder.py              # 双策略PDF构造器
│   ├── pipeline.py                 # 流程编排
│   └── reporter.py                 # 报告生成
├── config/default.yaml             # 默认配置文件
├── docs/encoding_spec.md           # 编码格式技术说明
├── build_exe.py                    # PyInstaller打包脚本
├── examples/                       # 示例PDF文件(7种编码 x 3图像)
│   ├── pdfs/                       #   21个PDF文件
│   ├── all_pdfs.zip                #   全部打包(1.5MB)
│   └── report.txt                  #   处理报告
└── output/                         # 输出目录(运行时生成)
```

## 快速开始

### 环境要求

- Python 3.12+
- 依赖: `pip install -r requirements.txt`

### 安装

```bash
git clone https://github.com/Ding-yixia/pdf-image-encoder.git
cd pdf-image-encoder
pip install -r requirements.txt
```

### 基本用法

```bash
# 处理 D:\wallpapers 中的图像，使用全部7种编码器
python run.py --input D:\wallpapers

# 指定编码器和图像数量
python run.py --input D:\photos --encoders LZW,DCT,Flate --count 5

# 控制图像质量和尺寸
python run.py --size 400 --quality 90

# 查看完整帮助
python run.py --help
```

### 参数说明

| 参数 | 缩写 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | `-i` | `D:\wallpapers` | 源图像目录 |
| `--output` | `-o` | `output` | 输出目录 |
| `--encoders` | `-e` | `all` | 编码器列表(逗号分隔)或 `all` |
| `--count` | `-n` | `3` | 处理的图像数量 |
| `--size` | `-s` | `300` | 图像最大边长(px)，0=不缩放 |
| `--quality` | `-q` | `85` | JPEG质量 |
| `--verbose` | `-v` | — | 详细日志 |

## 编码器详解

### Raw — 无压缩

原始RGB数据，不设Filter。测试基准。

### FlateDecode (zlib/Deflate)

PDF最常用的无损压缩编码。对照片类数据压缩率一般（~100%），但对插画、图标等重复数据压缩率高。

### DCTDecode (JPEG)

标准JPEG有损压缩。照片场景最优选择，在常见的85质量下压缩率约5-10%。

**实现**: Pillow JPEG编码，quality可调。

### JPXDecode (JPEG2000)

基于小波变换的有损/无损压缩。压缩率优于JPEG（约40-50%），但PDF阅读器支持不如JPEG广泛。

**实现**: Pillow JPEG2000编码。

### CCITTFaxDecode (Group 4)

二值图像专用编码。输入图像会自动转为黑白(阈值128)，对文档扫描件效果极好。

### RunLengthDecode (RLE)

简单游程编码。对大面积同色块数据高效，对照片类数据反而膨胀。

**构造策略**: 手动构造PDF字节 — 此编码会被pikepdf自动替换。

### LZWDecode

Lempel-Ziv-Welch 压缩算法，早期PDF标准使用的编码。后来被FlateDecode取代。

**构造策略**: 手动构造PDF字节 — pikepdf在 `save()` 时会自动将 `/LZWDecode` 替换为 `/FlateDecode`。

**实现**: [imagecodecs](https://pypi.org/project/imagecodecs/) 库的C扩展实现，经解码验证确保数据完整性。

### 编码效率对比 (300px, JPEG q=85)

| 编码 | PDF大小 | 压缩率 | 策略 |
|------|---------|--------|------|
| DCT (JPEG) | 11.7 KB | **7.7%** | pikepdf |
| CCITT (G4) | 7.3 KB | **4.8%** | pikepdf |
| JPX (JPEG2000) | 60 KB | **39.4%** | pikepdf |
| LZW | 142 KB | 93.5% | 手动 |
| Flate | 153 KB | 100.5% | pikepdf |
| Raw | ~153 KB | ~100% | 手动 |
| RLE | ~154 KB | ~101% | 手动 |

## 手动PDF构造原理

对于pikepdf不支持的编码(LZW/RLE/Raw)，跳过pikepdf的save转换层，直接构造PDF字节流。

PDF结构:
```
%PDF-1.4
1 0 obj          ← 图像XObject (/Filter /LZWDecode)
2 0 obj          ← 页面内容流 (Flate压缩)
3 0 obj          ← 页面字典 (Flate压缩)
4 0 obj          ← 页面树
5 0 obj          ← Catalog
xref
trailer
startxref
%%EOF
```

关键要点:
1. 图像流的 `/Filter /LZWDecode` 直接写入PDF字典
2. 交叉引用表偏移量必须精确计算
3. 页面字典用Flate压缩以避免与图像数据中的二进制关键字冲突
4. LZW数据经验证不包含 `endstream`/`endobj`/`trailer`/`startxref`/`%%EOF` 关键字

## 打包 (可选)

```bash
# 安装 PyInstaller
pip install pyinstaller

# Release 构建 (无控制台)
python build_exe.py

# Debug 构建 (保留控制台)
python build_exe.py --debug

# 清理构建产物
python build_exe.py --clean
```

输出: `dist/PDFImageEncoder.exe` (约100MB，含Python运行时+所有依赖)

## 配置

通过 `config/default.yaml` 自定义默认参数:

```yaml
input_dir: D:\wallpapers
output_dir: output
encoders:
  - LZW
  - DCT
  - Flate
  - JPX
  - CCITT
  - RLE
image_count: 3
max_size: 300
jpeg_quality: 85
```

## 依赖

- **Pillow** — 图像加载、缩放、JPEG/JPEG2000编码
- **pikepdf** — 标准编码PDF生成
- **imagecodecs** — LZW编解码 (C扩展，高性能)
- **PyYAML** — 配置解析
- **PyInstaller** (打包时) — 构建单文件exe

## 许可证

MIT
