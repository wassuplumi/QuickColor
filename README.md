# QuickColor 截图调色

一个简单的 Windows 桌面小工具：按快捷键框选屏幕区域，在浮窗中实时调整截图色彩。

## 下载与使用

在本仓库的 [Releases](https://github.com/wassuplumi/QuickColor/releases) 页面下载 Windows x64 压缩包，解压后双击 `QuickColor.exe`，无需安装 Python。

1. 按 **Alt + Shift + C**，拖动鼠标框选需要调整的区域。
2. 调节色相、饱和度、对比度、亮度。
3. 点击 **调色盘…** 选择叠加颜色，用 **着色强度** 控制效果。
4. 按住 **按住看原图** 临时比较，点击 **重置** 恢复初始参数。
5. **Esc** 或鼠标右键取消框选。

### 精确调整

- 拖动时持续刷新预览，并缓存缩放后的图像。
- 在滑块上滚动鼠标滚轮，或聚焦滑块后按左右方向键微调。
- 按住 **Shift** 可按更小步长调整。
- 数值框支持直接输入，按回车或移开焦点确认；也可使用上下小箭头。

### 后台与退出

运行后，Windows 右下角托盘会出现彩色圆环图标；若未显示，可展开隐藏图标。

右键菜单支持 **框选调色、显示控制面板、退出工具**。关闭浮窗或启动面板会保留后台，选择“退出工具”才会完全退出。

任务管理器中的进程名为 `QuickColor.exe`。单文件发行版可能显示两个同名父子进程。源码运行时则显示为 `python.exe` 或 `pythonw.exe`。

程序不会自动设置开机启动。日志位于 `%LOCALAPPDATA%\QuickColor\runtime.log`，只记录运行事件和错误，不记录截图内容。

## 系统与边界

- 面向 Windows 10 / 11 x64；在一台 Windows 11 双屏电脑上完成运行验证，尚未覆盖全部显示器、缩放比例和系统组合。
- 支持包含负坐标的扩展桌面，框选层与截图使用虚拟桌面坐标。
- 显示的是**静态截图**，不会实时改变其他应用窗口或持续录屏。
- 截图保存在内存，不自动保存或上传。
- 受保护的窗口内容可能无法截取；快捷键被其他应用占用时，可从托盘菜单调用。
- 本工具用于视觉辅助和图像实验，不提供医学诊断或色觉恢复治疗。增强后的色觉检测图不能用于诊断。

## 从源码运行

需要 Windows 和 Python 3.12（包含 Tkinter）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe quick_color.py
```

`color_tool.py` 同时保留了最初的图片文件调色界面，可单独运行。

## 构建独立 EXE

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

脚本创建项目内虚拟环境，安装固定版本依赖，构建 `dist\QuickColor.exe`。构建过程需要网络访问 PyPI；生成的软件运行时无需联网。

## 检查

先退出正在运行的 QuickColor，再执行：

```powershell
.\.venv\Scripts\python.exe check_quick_color.py
```

检查会临时截图、打开框选层和调色窗口，验证快捷键消息线程、双屏坐标、图像裁剪、调色盘、精确输入和控件布局；不保存或上传截图。此检查模拟热键消息，实际键盘快捷键还应手动验证。

## 源文件

| 文件 | 用途 |
| --- | --- |
| `quick_color.py` | 全局快捷键、框选、调色浮窗和托盘 |
| `color_tool.py` | 图像调整函数和图片文件调色界面 |
| `check_quick_color.py` | Windows 运行检查 |
| `requirements.txt` | 运行依赖 |
| `requirements-build.txt` | 打包依赖 |
| `build.ps1` | Windows 构建脚本 |

当前尚未选定本项目源码的开源许可证；仓库公开不等于授予任意使用、修改或分发源码的许可。第三方组件遵循各自许可证，见发行包中的 `licenses` 及 `THIRD_PARTY_NOTICES.md`。
