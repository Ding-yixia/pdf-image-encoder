# PDF Image Encoder — 产品需求文档 (PRD)

## 1. 项目概述

### 1.1 项目定位

**PDF Image Encoder** 是一个将图像文件转换为PDF的工具，支持多种图像编码格式嵌入PDF中。核心价值在于：不仅支持PDF标准主流编码（JPEG/JPEG2000/Flate等），还支持PDF标准通常不支持或会被PDF库自动替换的编码（LZW/RLE/Raw/SMask等）。

### 1.2 项目目标

1. 将指定文件夹中的图像批量转换为PDF文件
2. 支持9种不同的图像编码格式嵌入PDF
3. 确保所有编码在PDF中正确渲染，无白屏/黑屏/颜色反转
4. 提供自动化校验机制验证PDF中图像数据完整性
5. 支持透明度（Alpha通道）图像的PDF嵌入
6. 提供可执行文件打包能力
7. 生成编码效率对比报告

### 1.3 目标用户

- 需要对比不同PDF图像编码压缩率的开发者
- 需要将大量图像归档为特定编码PDF的用户
- PDF格式研究者
- 图像压缩算法评估人员

---

## 2. 功能需求

### 2.1 核心功能：图像→PDF转换

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| F1 | 批量图像输入 | P0 | 扫描指定文件夹中的所有图像文件 |
| F2 | 多种编码支持 | P0 | 支持至少9种图像编码格式 |
| F3 | 原尺寸输出 | P0 | 支持保持原始图像分辨率输出 |
| F4 | 缩放输出 | P1 | 支持将图像缩放到指定最大边长 |
| F5 | 输出目录结构 | P0 | 按编码类型自动创建子目录分类 |

### 2.2 编码器

| ID | 编码器 | Filter | 有损? | 颜色空间 | 位深 | 说明 |
|----|--------|--------|-------|---------|------|------|
| E1 | **Raw** | 无 | 否 | RGB | 8 | 无压缩原始数据，作为基准对比 |
| E2 | **Flate** | /FlateDecode | 否 | RGB | 8 | zlib/Deflate压缩，PDF最常用 |
| E3 | **DCT** | /DCTDecode | 是 | RGB | 8 | 标准JPEG压缩，照片最优选择 |
| E4 | **JPX** | /JPXDecode | 是 | RGB | 8 | JPEG2000小波压缩 |
| E5 | **CCITT** | /FlateDecode | 否(二值) | Gray | 1 | 黑白图像，Flate压缩1-bit数据 |
| E6 | **RLE** | /RunLengthDecode | 否 | RGB | 8 | 游程编码，大面积色块高效 |
| E7 | **LZW** | /LZWDecode | 否 | RGB | 8 | LZW算法，早期PDF标准 |
| E8 | **Alpha** | /LZWDecode + SMask | 否 | RGB + A | 8 | RGBA透明度通道支持 |
| E9 | **JBIG2** | /FlateDecode | 否(二值) | Gray | 1 | 黑白图像，Flate压缩1-bit数据 |

### 2.3 图像预处理

| ID | 需求 | 说明 |
|----|------|------|
| P1 | 灰度化 | 彩色图像转灰度(用于CCITT/JBIG2) |
| P2 | 二值化 | 阈值128将灰度图转为1-bit黑白 |
| P3 | 缩放 | LANCZOS算法保持宽高比缩放到指定尺寸 |
| P4 | 颜色空间标准化 | 统一转为RGB/RGBA模式 |
| P5 | JPEG重编码 | 可配置JPEG质量(1-100) |

### 2.4 PDF构造策略

| ID | 策略 | 适用编码 | 说明 |
|----|------|---------|------|
| S1 | **pikepdf路径** | DCT/JPX/Flate | 使用pikepdf库生成PDF，由pikepdf管理Filter |
| S2 | **手动构造路径** | Raw/RLE/LZW/Alpha | 直接构造PDF字节流，避免pikepdf自动替换Filter |
| S3 | **pikepdf+SMask** | Alpha | pikepdf路径下额外添加SMask对象 |

#### 手动构造PDF结构

```
%PDF-1.4
1 0 obj  ← 图像XObject (/Filter /LZWDecode, /SMask 6 0 R)
2 0 obj  ← 页面内容流 (Flate压缩)
3 0 obj  ← 页面字典 (Flate压缩)
4 0 obj  ← 页面树
5 0 obj  ← Catalog
6 0 obj  ← SMask (Alpha通道, 仅Alpha编码)
xref
trailer
startxref
%%EOF
```

### 2.5 Alpha透明度支持

| ID | 需求 | 说明 |
|----|------|------|
| A1 | RGBA→RGB+SMask | 分离RGBA图像的Alpha通道为独立SMask灰度图 |
| A2 | SMask编码 | SMask使用LZW编码(与主图像一致) |
| A3 | 测试图像生成 | 生成3种透明度测试图(半透明叠加/圆形挖孔/渐变透明) |

### 2.6 自动化校验

| ID | 需求 | 说明 |
|----|------|------|
| V1 | 图像数据校验 | 提取PDF中嵌入的图像数据，逐字节对比原始RGB |
| V2 | 尺寸校验 | 验证PDF中图像尺寸与原始一致 |
| V3 | 可打开性校验 | JBIG2/MuPDF生成的PDF验证可打开即可 |
| V4 | 校验报告 | 校验结果记录在报告文件中 |

### 2.7 报告生成

| ID | 需求 | 说明 |
|----|------|------|
| R1 | 编码效率报告 | CSV/文本格式，记录原始大小、PDF大小、压缩率 |
| R2 | 状态标记 | 每个编码结果标记成功/失败 |

### 2.8 CLI接口

```
run.py --input <目录> [--output <目录>] [--encoders <列表>] [--count <数量>] [--size <像素>] [--quality <1-100>] [--verbose]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--input` / `-i` | `D:\wallpapers` | 源图像目录 |
| `--output` / `-o` | `output` | 输出目录 |
| `--encoders` / `-e` | `all` | 编码器列表(逗号分隔)或`all` |
| `--count` / `-n` | `3` | 处理的图像数量(0=全部) |
| `--size` / `-s` | `300` | 图像最大边长px(0=不缩放) |
| `--quality` / `-q` | `85` | JPEG质量 |
| `--verbose` / `-v` | — | 详细日志 |

### 2.9 可执行打包

| ID | 需求 | 说明 |
|----|------|------|
| B1 | PyInstaller打包 | 将项目打包为单文件exe |
| B2 | Debug/Release | Debug保留控制台，Release隐藏控制台 |

---

## 3. 非功能需求

### 3.1 兼容性

- Python 3.12+
- Windows 10/11
- 依赖: Pillow, pikepdf, imagecodecs, PyYAML
- PDF阅读器: 生成的PDF应能被Adobe Acrobat、Chrome内置PDF阅读器、MuPDF等打开

### 3.2 性能

- 批处理能力: 支持396+图像批量处理
- 内存: 原始图像加载内存受限（逐张处理，不全部加载）

### 3.3 可靠性

- 自动化校验捕获数据不一致问题
- 异常处理: 单图像编码失败不影响其他图像
- LZW编解码验证确保数据完整

---

## 4. 架构设计

### 4.1 模块架构

```
┌─────────────────────────────────────────────────────┐
│                    CLI 入口 (main.py)                │
├─────────────────────────────────────────────────────┤
│                    Pipeline (pipeline.py)            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐ │
│  │ 图像输入  │→ │ 图像预处理 │→ │ 编码器   │→ │PDF   │ │
│  │ loader   │  │preprocess│  │ encoders │  │builder│ │
│  └──────────┘  └──────────┘  └────┬─────┘  └──┬───┘ │
│                                   │            │      │
│                           ┌───────▼────┐  ┌───▼───┐ │
│                           │ Encoder基类 │  │验证器  │ │
│                           │ (7种实现)   │  │verify  │ │
│                           └────────────┘  └───────┘ │
├─────────────────────────────────────────────────────┤
│                   配置管理 (config_manager.py)        │
├─────────────────────────────────────────────────────┤
│                   报告生成 (reporter.py)              │
└─────────────────────────────────────────────────────┘
```

### 4.2 数据流

```
图像文件 → scan_images() → ImagePreprocessor.process() → Encoder.encode() → PdfBuilder.build() → verify_pdf_image() → PDF文件
                         ↓                          ↓                   ↓
                   原始RGB数据              编码后数据+参数       PDF文件路径
```

---

## 5. 已修复的Bug记录

| Bug | 发现时间 | 原因 | 修复 |
|-----|---------|------|------|
| FlateDecode黑屏 | 2026-06-13 | zlib未压缩RGB数据，阅读器解压失败 | FlateEncoder预压缩zlib.compress() |
| CCITT白屏/颜色反转 | 2026-06-13 | PIL tile.offset=0导致数据提取错误 + DecodeParms/BlackIs1值类型错误 | 改用FlateDecode+1-bit方案 |
| JBIG2段结构错误 | 2026-06-13 | 纯Python JBIG2封装不符合标准 | 改用FlateDecode+1-bit方案 |
| BytesIO.name不存 | 2026-06-13 | 对BytesIO调用.name属性 | 改用TIFF tag提取 |
| DecodeParms布尔值 | 2026-06-13 | bool值误传为Name对象/true | 直接传Python bool给pikepdf |

---

## 6. 输出规范

### 6.1 目录结构

```
{output_dir}/
├── Raw/          ← Raw编码的PDF
├── Flate/        ← Flate编码的PDF
├── DCT/          ← DCT(JPEG)编码的PDF
├── JPX/          ← JPEG2000编码的PDF
├── CCITT/        ← CCITT二值编码的PDF
├── RLE/          ← RLE编码的PDF
├── LZW/          ← LZW编码的PDF
├── Alpha/        ← Alpha透明度编码的PDF
├── JBIG2/        ← JBIG2二值编码的PDF
└── report.txt    ← 处理报告
```

### 6.2 文件命名

```
{源文件名}_{编码器名称}.pdf
```

示例: `abstract-art-3840x2160-26359_DCT.pdf`

---

## 7. 依赖清单

| 库 | 用途 | 必需 |
|----|------|------|
| **Pillow** ≥10.0 | 图像加载、缩放、JPEG/JPEG2000编码 | ✅ |
| **pikepdf** ≥10.0 | 标准PDF生成、图像数据提取、校验 | ✅ |
| **imagecodecs** ≥2025.0 | LZW编解码(C扩展) | ✅ |
| **PyYAML** ≥6.0 | 配置解析 | ✅ |
| **PyMuPDF (fitz)** | JBIG2 PDF生成(已改用Flate，可选) | ❌(可选) |
| **PyInstaller** | exe打包(仅构建时需要) | ❌(可选) |

---

## 8. 附录

### 8.1 术语表

| 术语 | 说明 |
|------|------|
| Filter | PDF中用于解码流数据的算法名称 |
| SMask | PDF中用于表示透明度的软蒙版(Soft Mask) |
| XObject | PDF中的外部对象(如图像) |
| xref | 交叉引用表，PDF对象索引 |
| MMR | Modified Modified READ，CCITT Group 4编码算法 |
| BPC | Bits Per Component，每分量位数 |

### 8.2 参考标准

- PDF 32000-1:2008 (ISO 32000-1)
- ITU-T T.4 (CCITT Group 3/4)
- JBIG2 (ISO/IEC 14492)
- JPEG (ISO/IEC 10918)
- JPEG 2000 (ISO/IEC 15444)
- LZW (US Patent 4,558,302)
