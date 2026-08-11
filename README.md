# ofd2pdf

OFD（GB/T 33190，国标版式文档）转 PDF 的命令行工具，支持可插拔后端。适合批量转换电子发票、政务公文、民航统计通报等 OFD 文件。

## 特性

- **可插拔后端**：默认使用纯 Python 的 `easyofd`；复杂文档可切换到 `taurusxin/Ofd2Pdf`（Windows）或 `ofdrw`（Java）。
- **命令行 + Python API**：单文件、批量目录转换。
- **进度显示**：批量转换时显示进度。
- ** MIT 协议**：代码可自由使用。

## 后端对比

| 后端 | 依赖 | 复杂表格 | 电子签章 | 推荐场景 |
|------|------|----------|----------|----------|
| `easyofd` | Python 包 | 可能错位 | 可能丢失 | 简单发票、正文为主的公文 |
| `taurusxin` | 下载 Windows EXE | 较好 | 保留印章外观 | Windows 本地批量处理 |
| `ofdrw` | Java + Maven | 最好 | 较好 | Java 后端/服务器 |

> 本项目**不自带** `taurusxin` EXE 或 `ofdrw` JAR。首次使用这些后端时，运行项目提供的下载脚本即可。

## 安装

```bash
# 1. 克隆仓库
git clone https://github.com/swingmonkey/ofd2pdf.git
cd ofd2pdf

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate     # Windows
source .venv/bin/activate # Linux/macOS

# 3. 安装
pip install -e .
```

## 快速开始

```bash
# 转换单个文件（默认 easyofd 后端）
ofd2pdf input.ofd -o output.pdf

# 批量转换目录下所有 .ofd
ofd2pdf D:\incoming\ -o D:\pdf\ --batch

# 使用 taurusxin 后端（Windows，效果最佳）
ofd2pdf input.ofd -o output.pdf --backend taurusxin
```

## 后端启用说明

### easyofd（默认）
无需额外操作，安装 `pip install -e .` 后即可使用。

### taurusxin（Windows）

```powershell
# 下载并解压 Ofd2Pdf.exe 到项目 bin/ 目录
.\scripts\setup_taurusxin.ps1
```

脚本会自动从 [taurusxin/Ofd2Pdf releases](https://github.com/taurusxin/Ofd2Pdf/releases) 下载 `Ofd2Pdf_1.2.zip` 并解压到 `bin/Ofd2Pdf.exe`。

### ofdrw（Java）

需要 Java 8+ 与 Maven。项目提供示例 `ofdrw` Java 转换代码，请见 `scripts/ofdrw/`，按其中 `README.md` 构建后，将生成的 jar 放到 `bin/ofdrw-converter.jar`，本工具会自动调用。

## 使用示例（Python API）

```python
from ofd2pdf.converter import convert_file

convert_file("input.ofd", "output.pdf", backend="easyofd")
```

## 实测效果

用仓库同目录下的测试文件（民航局 1353 号 2026 年 6 月份航班正常考核指标通报，20 页 WPS 生成 OFD）验证：

- `easyofd` 后端：
  - 封面、正文页：文字清晰、排版正确。
  - 统计附表页：出现表格内文字竖排/重叠错位（复杂版式典型问题）。
- `taurusxin` 后端（需自行下载 EXE）：对该类表格排版通常更稳定。
- `ofdrw` 后端（需 Java）：版式还原度最高。

因此建议：
- **正文多/发票**：用 `easyofd`（零原生依赖，跨平台）。
- **复杂统计表/公文**：用 `taurusxin`（Windows）或 `ofdrw`（Java）。

## 目录结构

```text
ofd2pdf/
├── ofd2pdf/              # 主包
│   ├── backends/         # 转换后端
│   ├── cli.py            # 命令行入口
│   └── converter.py      # 统一 API
├── scripts/              # 后端安装脚本
├── tests/                # 测试
├── README.md
└── pyproject.toml
```

## 已知限制

- `easyofd` 对复杂表格、多栏混排、CTM 变换的 OFD 文件可能排版错位。
- 电子签章在多数开源转换后仅保留印章图片，**不再具备验签法律效力**。
- 中文字体缺失时会出现方框；Windows 通常已有宋体/微软雅黑，Linux 需安装 `fonts-noto-cjk`。

## License

MIT © 廖总
