# SciFigure AI Studio 

> AI 科研绘图工具：从表格数据到论文级图表，一站完成 **数据导入 → 生成绘图 → 参数精修 → 复现代码 → 多格式导出**。

SciFigure AI Studio 是一个面向科研、论文写作、实验报告和数据分析场景的桌面绘图工具。用户可以导入 CSV、Excel、JSON、Parquet，也可以直接在软件中手动输入 X/Y 数据或粘贴 Excel 表格；随后通过自然语言描述绘图需求，由大模型生成安全的绘图方案 `ChartSpec`，再交给本地可信绘图引擎渲染图表。

与传统“让 AI 直接写并执行 Python 代码”的方式不同，本项目采用：

```text
数据表格 → 用户绘图需求 → 大模型生成 ChartSpec → 本地绘图引擎渲染 → 参数面板精修 → 导出/复现
```

这样既保留了自然语言绘图的灵活性，也提升了安全性、稳定性和可复现性。

---

## 功能亮点

### 1. 生成绘图

- 输入自然语言需求即可生成科研图。
- 支持大模型生成绘图方案，也支持无 API Key 时本地规则推荐。
- 模型只返回结构化 JSON，不直接执行任意代码。
- 生成失败时自动回退到本地推荐，避免流程中断。

### 2. 多方式数据导入

支持以下导入方式：

- CSV / TXT
- Excel `.xlsx` / `.xls`
- JSON
- Parquet
- 剪贴板表格
- 软件内手动输入 X/Y 数据
- 从 Excel 复制表格后直接粘贴

手动输入示例：

```text
Sample Group Value
A Control 1.2
B Control 1.5
C Treatment 2.4
D Treatment 2.8
```

### 3. 大模型配置窗口

软件内提供 **⚙️ 大模型配置** 按钮，用户可以自由配置：

- API Key
- Base URL
- Model Name
- Timeout
- OpenAI / DeepSeek / DeepSeek Reasoner / 自定义 OpenAI-compatible 服务
- 本地规则模式

无需修改代码即可切换不同模型服务。

### 4. 论文级图表参数面板

支持在右侧参数面板中精修：

- 图表类型
- 图表语言：纯科研英语 / 中文
- 主题模板：Nature / Science / IEEE / Modern / Dark / Minimal
- X、Y、Y2、Hue 列选择
- Error Bar 列选择
- 聚合方式：none / mean / median / sum / count
- 标题、X 轴标题、Y 轴标题
- 图像尺寸、DPI
- 网格、图例、对数坐标

### 5. 支持的图表类型

- 散点图
- 折线图
- 柱状图
- 水平柱状图
- 直方图
- 箱线图
- 小提琴图
- 相关矩阵
- 热力图
- 回归图
- 误差棒
- 双 Y 轴
- 面积图
- 饼图
- KDE 密度图

### 6. 出图与复现

- 导出 PNG / SVG / PDF / TIFF
- 支持 600 DPI 论文级导出
- 每次绘图自动生成可复制 Python 复现代码
- 支持批量导出多个数值列图表

---

## 软件截图建议

建议在仓库中放置以下截图，便于展示项目效果：

```text
images/
  home.png              # 主界面
  llm_config.png        # 大模型配置窗口
  manual_input.png      # 手动输入数据窗口
  chart_preview.png     # 图表预览
  code_export.png       # 复现代码界面
```

README 中可插入：

```html
<div align="center">
  <img src="images/home.png" width="760">
</div>
```

---

## 快速启动：开发版双击运行

如果你只是自己使用或开发调试，可以直接双击：

```text
启动软件.bat
```

该脚本会自动完成：

1. 创建 `.venv` 虚拟环境
2. 安装 `requirements.txt`
3. 启动 `python main.py`

> 注意：这种方式要求电脑已安装 Python 3.9+，并且安装 Python 时勾选了 `Add Python to PATH`。

---

## 打包成可双击打开的 EXE

如果你想发给别人使用，推荐在 Windows 电脑上执行：

```text
打包成EXE.bat
```

打包完成后，程序位置为：

```text
dist/SciFigure AI Studio/SciFigure AI Studio.exe
```

你可以把整个文件夹：

```text
dist/SciFigure AI Studio/
```

压缩成 zip 发给别人。用户解压后双击：

```text
SciFigure AI Studio.exe
```

即可打开软件。

### 为什么推荐“文件夹版”而不是“单文件版”？

PyQt5、Matplotlib、Pandas 依赖较多，单文件 EXE 首次启动会较慢，也更容易被杀毒软件误报。正式分发建议使用文件夹版。

如果确实想生成单文件 EXE，可以运行：

```text
build_tools/build_windows_onefile.bat
```

生成位置：

```text
dist/SciFigure AI Studio.exe
```

---

## 常规命令行运行

```bash
cd SciFigureAIStudio
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

---

## 大模型配置

启动软件后，点击右上角：

```text
⚙️ 大模型配置
```

### OpenAI 示例

```env
AI_FIGURE_BASE_URL=https://api.openai.com/v1
AI_FIGURE_MODEL=gpt-4.1-mini
AI_FIGURE_API_KEY=你的 OpenAI Key
AI_FIGURE_TIMEOUT=60
```

### DeepSeek 示例

```env
AI_FIGURE_BASE_URL=https://api.deepseek.com
AI_FIGURE_MODEL=deepseek-chat
AI_FIGURE_API_KEY=你的 DeepSeek Key
AI_FIGURE_TIMEOUT=60
```

### 本地规则模式

如果不填写 API Key，软件会自动进入本地规则模式：

- 不调用外部模型
- 根据数据列类型自动推荐图表
- 可继续手动调整参数和导出图表

---

## 推荐提示词

```text
绘制模型名称和测试集平均 R2 的柱状图，按照打印方向分组，使用论文风格。
```

```text
Plot a regression figure between training RMSE and testing RMSE with a clean Nature style.
```

```text
根据所有数值列绘制相关性热力图，标题使用纯科研英语。
```

```text
比较不同模型的测试集 MAE，用箱线图展示，并显示网格。
```

---

## 目录结构

```text
SciFigureAIStudio/
  main.py                       # 程序入口
  requirements.txt              # 运行依赖
  build_requirements.txt        # 打包依赖
  .env.example                  # 大模型配置模板
  启动软件.bat                  # 开发版双击启动器
  打包成EXE.bat                 # Windows 文件夹版 EXE 打包器
  SciFigureAIStudio.spec        # PyInstaller 打包配置
  build_tools/
    build_windows_folder.bat    # Windows 文件夹版打包
    build_windows_onefile.bat   # Windows 单文件版打包
    build_macos_app.sh          # macOS app 打包脚本
    build_linux_appimage_note.sh# Linux 可执行文件打包脚本
  docs/
    PACKAGING.md                # 打包说明
  scifigure/
    app.py                      # 主窗口和 UI 交互
    charting.py                 # ChartSpec 与本地绘图引擎
    llm.py                      # OpenAI-compatible 大模型调用
    dialogs.py                  # 配置弹窗、手动数据录入弹窗
    data_model.py               # 数据加载、数据画像、表格模型
    codegen.py                  # 复现代码生成
    workers.py                  # 后台线程
    styles.py                   # QSS 外观样式
    widgets.py                  # 自定义控件
```
## 开源协议

本项目可继续沿用 MIT License。请在发布时保留 LICENSE 文件。
