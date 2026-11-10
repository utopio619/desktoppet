# DeskPet (桌面宠物)
这是我的vibe coding课程项目。

## 运行环境
- Python 3.8 及以上
- 依赖库：PySide6、PyQt5

## 如何运行本项目
1. 确保已安装 Python。
2. 在终端中安装依赖：
   `pip install PySide6`
3. 确保根目录下包含所需的素材文件（立绘 PNG、文本 TXT、音效 MP3）。
4. 运行主程序：
   `python main.py`

## 操作说明
- **单击**：随机弹出一句话
- **双击 / 右键**：打开设置菜单
- **拖拽**：移动宠物（会有互动提示）
- **托盘**：支持后台常驻，单击托盘图标显示/隐藏。
  
<img width="762" height="688" alt="QQ_1794306515984" src="https://github.com/user-attachments/assets/b82eb08d-8fc9-44b4-acf7-8999365c11e2" />


## 📦 素材说明 (Assets & Dependencies)
为了确保项目能顺利运行，请注意以下素材配置：
### 1. 立绘与文本 (Images & Text)
- `Raven.png` 及 `Blink1~3.png`：角色的立绘差分图。
- `texts.txt`、`morning.txt`、`afternoon.txt`、`evening.txt`、`night.txt`、`bye.txt`：桌宠的对话文本库。请确保它们与代码在同一目录下，且编码为 UTF-8。

### 2. 音频素材特别说明 (Audio Asset Notice)
- **`ding.mp3` 不在本仓库中提供。**
- **原因**：本程序使用的提示音效来源于 [Pixabay](https://pixabay.com/zh/sound-effects/film-special-effects-ding-101492/)，根据其授权协议（Pixabay Content License），禁止将未修改的原始音频文件作为独立素材进行再分发（Redistribute）。因此，为遵守版权规定，我没有在 GitHub 仓库中上传该音频。
- **如何获取与运行**：
  - 程序已做了**容错处理**。如果你没有 `ding.mp3`，点击“设定倒计时”到点后，依然会弹出“叮！时间到了！”的气泡，只是没有声音，**程序不会崩溃**。
  - 如果需要恢复声音，请前往 [Pixabay](https://pixabay.com/zh/sound-effects/film-special-effects-ding-101492/)下载，将其重命名为 `ding.mp3` 并放在与 `main.py` 同一目录下即可。
 
    
