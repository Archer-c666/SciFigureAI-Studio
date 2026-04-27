# 打包说明

本文说明如何把 SciFigure AI Studio 打包成可以双击启动的软件。

## 一、开发版双击启动器

适合自己使用或开发调试。

双击项目根目录：

```text
启动软件.bat
```

优点：

- 易维护
- 不需要每次改代码后重新打包
- 自动创建虚拟环境并安装依赖

缺点：

- 用户电脑必须安装 Python 3.9+
- 首次运行需要联网安装依赖

## 二、Windows EXE 文件夹版，推荐

在 Windows 电脑上双击：

```text
打包成EXE.bat
```

输出目录：

```text
dist/SciFigure AI Studio/
```

其中可执行文件是：

```text
dist/SciFigure AI Studio/SciFigure AI Studio.exe
```

发布时，请把整个 `dist/SciFigure AI Studio` 文件夹压缩发给用户，不要只发 `.exe` 一个文件，因为该文件夹里还包含运行所需动态库和资源。

## 三、Windows 单文件版

如果你希望最终只得到一个 `.exe`，可以运行：

```text
build_tools/build_windows_onefile.bat
```

输出文件：

```text
dist/SciFigure AI Studio.exe
```

注意：

- 单文件版首次启动会较慢。
- 体积较大。
- 某些杀毒软件可能误报。
- 如果用户反馈打不开，优先改用文件夹版。

## 四、macOS app

在 macOS 上运行：

```bash
chmod +x build_tools/build_macos_app.sh
./build_tools/build_macos_app.sh
```

输出：

```text
dist/SciFigure AI Studio.app
```

## 五、Linux 可执行文件

在 Linux 上运行：

```bash
chmod +x build_tools/build_linux_appimage_note.sh
./build_tools/build_linux_appimage_note.sh
```

输出：

```text
dist/SciFigure AI Studio/SciFigure AI Studio
```

如需 AppImage，可在此基础上继续使用 `appimagetool` 或 `linuxdeployqt` 封装。

## 六、发布前检查清单

- [ ] 软件可以正常打开
- [ ] 可以导入 CSV / Excel
- [ ] 可以手动输入 X/Y 数据
- [ ] 可以生成图表
- [ ] 可以导出 PNG / SVG / PDF
- [ ] 大模型配置窗口可以保存配置
- [ ] 未配置 API Key 时可以回退到本地规则模式
- [ ] README、LICENSE 已放入发布包
- [ ] 没有把真实 API Key 写入 `.env` 或代码中

## 七、重要安全提醒

不要把真实 API Key 打进公开发布包。发布前请删除本地 `.env` 文件，只保留 `.env.example`。
