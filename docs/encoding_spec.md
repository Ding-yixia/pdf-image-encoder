# PDF图像编码格式技术说明

## 编码格式总表

| 编码名称 | PDF Filter | 有损? | 适用场景 | 构造策略 |
|---------|-----------|-------|---------|---------|
| **Raw** | 无 | 否 | 未压缩基线 | **手动** |
| **Flate** | `/FlateDecode` | 否 | 插画/图标/截图 | pikepdf |
| **DCT** | `/DCTDecode` | 是 | 照片/自然图像 | pikepdf |
| **JPX** | `/JPXDecode` | 是 | 高压缩比照片 | pikepdf |
| **CCITT** | `/CCITTFaxDecode` | 否(二值) | 扫描文档/黑白图 | pikepdf |
| **RLE** | `/RunLengthDecode` | 否 | 大面积色块 | **手动** |
| **LZW** | `/LZWDecode` | 否 | 早期PDF兼容 | **手动** |

## 构造策略说明

### A策略: pikepdf (主流编码)

DCT/Flate/JPX/CCITT 等编码使用 pikepdf 生成。

**优点**: 代码简洁, PDF结构标准, 可被所有阅读器打开。

**局限**: pikepdf在 `save()` 时会自动将 `/LZWDecode` 替换为 `/FlateDecode`,
因此LZW编码的图像无法通过pikepdf直接保存。

### B策略: 手动构造 (非标准编码)

LZW/RLE/Raw 使用手动二进制构造。

**原理**: 
1. 直接生成PDF字节流, 跳过pikepdf的save转换层
2. 构造包含以下对象的PDF:
   - 图像XObject (直接写入 `/Filter /LZWDecode`)
   - 页面内容流 (Flate压缩)
   - 页面字典 (Flate压缩)
   - 页面树
   - Catalog
   - 交叉引用表 + trailer

**格式**:
```pdf
%PDF-1.4
1 0 obj
<< /Type /XObject /Subtype /Image
   /Width W /Height H
   /ColorSpace /DeviceRGB /BitsPerComponent 8
   /Filter /LZWDecode /Length N >>
stream
[LZW编码的二进制数据]
endstream
endobj
...
xref
0 6
0000000000 65535 f
...
trailer << /Size 6 /Root 5 0 R >>
startxref OFFSET
%%EOF
```

## 手动构造的注意事项

1. **二进制安全**: LZW/RLE数据中可能包含与PDF关键字相同的字节序列
   (如 `endstream`), 写入前需检查。`imagecodecs` 输出的LZW数据
   经验证不包含 `endstream`/`endobj`/`trailer`/`startxref`/`%%EOF`
   等关键字序列。

2. **xref偏移量**: 每个对象在文件中的字节偏移量必须精确, 否则PDF阅读器
   无法定位对象。

3. **Flate压缩页面字典**: 页面字典使用FlateDecode压缩以减少文件大小,
   同时避免与图像数据中的关键字冲突。

## 编码器性能对比

测试条件: 300×169 px RGB图像 (152,100 bytes 原始数据)

| 编码 | 大小 | 压缩率 | 说明 |
|------|------|-------|------|
| DCT (JPEG q=85) | ~7 KB | ~5% | 照片场景最佳选择 |
| Flate | ~152 KB | ~100% | 照片数据不高效 |
| LZW | 57-148 KB | 38-97% | 依赖图像复杂度 |
| RLE | ~152 KB | ~100% | 对照片数据不高效 |
| JPX (JPEG2000) | ~70 KB | ~46% | 比JPEG差但无损可选 |
| CCITT (G4) | ~10 KB | ~7% | 二值化后大小 |
| Raw | ~152 KB | 100% | 基线对比 |
