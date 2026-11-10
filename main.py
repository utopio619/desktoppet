"""
桌面宠物 —— 最终版（增加再见气泡与延迟退出 + 托盘头像支持）
"""

import sys
import random
import datetime
from pathlib import Path
from enum import Enum

try:
    from PyQt5.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QUrl
    from PyQt5.QtGui import QPixmap, QIcon, QPainter, QColor, QPen
    from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QMenu,
                                 QSystemTrayIcon, QInputDialog, QVBoxLayout)
except ImportError:
    from PySide6.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QUrl
    from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor, QPen
    from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QMenu,
                                   QSystemTrayIcon, QInputDialog, QVBoxLayout)

# ============================================================
# 可调参数
# ============================================================
IMAGE_DIR = Path(__file__).resolve().parent
TEXT_FILE = IMAGE_DIR / "texts.txt"
BYE_FILE = IMAGE_DIR / "bye.txt"

MAX_SIZE = 400
USE_MASK = False

BLINK_FRAMES = ["Blink1.png", "Blink2.png", "Blink3.png", "Blink2.png", "Blink1.png"]
BLINK_FRAME_MS = 100
BLINK_INTERVAL_RANGE = (3000, 6000)


class PetState(Enum):
    SIT = "sit"


STATE_IMAGES = {
    PetState.SIT: "Raven.png",
}


def _event_global_pos(event):
    if hasattr(event, "globalPosition"):
        return event.globalPosition().toPoint()
    return event.globalPos()


def _read_random_line(filepath):
    if not filepath.exists():
        return f"找不到 {filepath.name} 文件哦~"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        if not lines:
            return f"{filepath.name} 里面是空的呢..."
        return random.choice(lines)
    except Exception as e:
        return f"读取文本失败: {e}"


def _get_random_text():
    return _read_random_line(TEXT_FILE)


def _get_time_greeting_text():
    hour = datetime.datetime.now().hour
    if 6 <= hour < 12:
        target_file = IMAGE_DIR / "morning.txt"
    elif 12 <= hour < 18:
        target_file = IMAGE_DIR / "afternoon.txt"
    elif 18 <= hour < 22:
        target_file = IMAGE_DIR / "evening.txt"
    else:
        target_file = IMAGE_DIR / "night.txt"
    return _read_random_line(target_file)


# ============================================================
# 气泡窗口 (纯代码绘制，零依赖)
# ============================================================
class BubbleWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background: transparent; color: #2c3e50; font-size: 14px; font-family: 'Microsoft YaHei'; font-weight: bold;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.addWidget(self.label)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.start_fade_out)

        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(800)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self.hide)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setBrush(QColor(255, 255, 255, 240))
        pen = QPen(QColor(200, 200, 200))
        pen.setWidth(1)
        painter.setPen(pen)

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 12, 12)

    def show_text(self, text, duration=3000):
        self.label.setText(text)
        font_metrics = self.label.fontMetrics()
        text_width = font_metrics.horizontalAdvance(text)
        self.label.setFixedWidth(min(text_width, 250))

        self.adjustSize()
        self.setWindowOpacity(1.0)
        self.show()
        self.timer.start(duration)

    def start_fade_out(self):
        self.anim.start()


# ============================================================
# 主窗口
# ============================================================
class PetWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.label = QLabel(self)
        self.label.setStyleSheet("background-color: transparent;")
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.state = PetState.SIT
        self.drag_pos = QPoint()
        self._click_start_pos = QPoint()
        self._is_dragging = False
        self._has_greeted = False

        self.click_timer = QTimer(self)
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self._on_single_click)

        self.bubble = BubbleWindow()

        self._build_menu()
        self._setup_tray()
        self._setup_blink()
        self.set_image(STATE_IMAGES[self.state])

    def showEvent(self, event):
        super().showEvent(event)
        self._on_state_changed()
        if not self._has_greeted:
            self._has_greeted = True
            QTimer.singleShot(800, lambda: self.show_bubble(_get_time_greeting_text(), 4000))

    # ------------------------------------------------------------
    # 菜单与托盘
    # ------------------------------------------------------------
    def _build_menu(self):
        self.menu = QMenu(self)

        self.act_timer = self.menu.addAction("设定倒计时")
        self.act_timer.triggered.connect(self._set_timer)

        self.act_top = self.menu.addAction("始终置于顶端")
        self.act_top.setCheckable(True)
        self.act_top.setChecked(True)
        self.act_top.triggered.connect(self._toggle_top)

        self.opacity_menu = self.menu.addMenu("调整透明度")
        for label, value in [("100%", 1.0), ("80%", 0.8), ("60%", 0.6), ("40%", 0.4)]:
            act = self.opacity_menu.addAction(label)
            act.triggered.connect(lambda checked=False, v=value: self.setWindowOpacity(v))

        self.menu.addSeparator()

        self.act_quit = self.menu.addAction("再见")
        self.act_quit.triggered.connect(self._quit_app)

        self.menu.aboutToShow.connect(self._refresh_menu_text)

    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)

        # ========== 修改：优先使用 head.png，没有则用默认立绘 ==========
        head_path = IMAGE_DIR / "head.png"
        if head_path.exists():
            icon_path = head_path
        else:
            icon_path = IMAGE_DIR / STATE_IMAGES[PetState.SIT]

        self.tray_icon.setIcon(QIcon(str(icon_path)))
        # ============================================================

        self.tray_icon.setToolTip("桌面宠物")
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
                self.bubble.hide()
            else:
                self.show()

    def _refresh_menu_text(self):
        self.act_top.setChecked(bool(self.windowFlags() & Qt.WindowStaysOnTopHint))

    def _toggle_top(self, checked):
        pos = self.pos()
        flags = self.windowFlags()
        if checked:
            flags = flags | Qt.WindowStaysOnTopHint
        else:
            flags = flags & ~Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()
        self.move(pos)

    def _quit_app(self):
        if hasattr(self, 'countdown_timer'):
            self.countdown_timer.stop()
        self._stop_blink()
        self.blink_trigger_timer.stop()

        self.tray_icon.hide()
        self.show_bubble(_read_random_line(BYE_FILE), duration=2500)
        QTimer.singleShot(2500, QApplication.quit)

    def show_menu(self, global_pos):
        self.menu.popup(global_pos)

    # ------------------------------------------------------------
    # 倒计时与音效
    # ------------------------------------------------------------
    def _set_timer(self):
        minutes, ok = QInputDialog.getInt(self, "计时器设定", "请输入倒计时分钟数:", 5, 1, 120)
        if ok:
            if hasattr(self, 'countdown_timer'):
                self.countdown_timer.stop()
            self.countdown_timer = QTimer(self)
            self.countdown_timer.setSingleShot(True)
            self.countdown_timer.timeout.connect(self._timer_finished)
            self.countdown_timer.start(minutes * 60 * 1000)
            self.show_bubble(f"倒计时启动：{minutes} 分钟")

    def _timer_finished(self):
        self.show_bubble("叮！时间到了！")
        sound_file = IMAGE_DIR / "ding.mp3"
        if not sound_file.exists():
            return
        try:
            if 'PyQt5' in sys.modules:
                from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
                self.player = QMediaPlayer()
                self.player.setMedia(QMediaContent(QUrl.fromLocalFile(str(sound_file))))
                self.player.play()
            elif 'PySide6' in sys.modules:
                from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
                self.audio_output = QAudioOutput()
                self.player = QMediaPlayer()
                self.player.setAudioOutput(self.audio_output)
                self.player.setSource(QUrl.fromLocalFile(str(sound_file)))
                self.player.play()
        except Exception as e:
            print(f"音效播放失败（可能未安装 QtMultimedia）: {e}")

    # ------------------------------------------------------------
    # 立绘
    # ------------------------------------------------------------
    def set_image(self, filename: str):
        path = IMAGE_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"找不到立绘文件：{path}")

        pix = QPixmap(str(path))
        if pix.isNull():
            raise ValueError(f"立绘加载失败：{path}")

        if pix.width() > MAX_SIZE or pix.height() > MAX_SIZE:
            pix = pix.scaled(MAX_SIZE, MAX_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        if pix.width() == self.width() and pix.height() == self.height():
            self.label.setPixmap(pix)
            return

        old_geo = self.geometry()
        self.label.setPixmap(pix)
        self.label.resize(pix.width(), pix.height())
        self.setFixedSize(pix.width(), pix.height())

        if self.isVisible() and old_geo.width() > 0:
            new_x = old_geo.left() + old_geo.width() // 2 - pix.width() // 2
            new_y = old_geo.bottom() - pix.height() + 1
            self.move(new_x, new_y)

        if USE_MASK:
            self.setMask(pix.mask())

    # ------------------------------------------------------------
    # 气泡
    # ------------------------------------------------------------
    def _update_bubble_position(self):
        geo = self.geometry()
        x = geo.center().x() - self.bubble.width() // 2
        y = geo.top() - self.bubble.height() + 10
        self.bubble.move(x, y)

    def show_bubble(self, text, duration=3000):
        if not self.isVisible():
            return
        self.bubble.show_text(text, duration)
        self._update_bubble_position()

    def _on_single_click(self):
        self.show_bubble(_get_random_text())

    # ------------------------------------------------------------
    # 眨眼动画
    # ------------------------------------------------------------
    def _setup_blink(self):
        self.blink_frame_timer = QTimer(self)
        self.blink_frame_timer.setInterval(BLINK_FRAME_MS)
        self.blink_frame_timer.timeout.connect(self._blink_next_frame)

        self.blink_trigger_timer = QTimer(self)
        self.blink_trigger_timer.setSingleShot(True)
        self.blink_trigger_timer.timeout.connect(self._start_blink)

        self.blink_index = 0

    def _on_state_changed(self):
        self._schedule_next_blink()

    def _schedule_next_blink(self):
        if self.blink_trigger_timer.isActive():
            return
        delay = random.randint(*BLINK_INTERVAL_RANGE)
        self.blink_trigger_timer.start(delay)

    def _start_blink(self):
        self.blink_index = 0
        self.blink_frame_timer.start()

    def _blink_next_frame(self):
        if self.blink_index >= len(BLINK_FRAMES):
            self._stop_blink()
            self.set_image(STATE_IMAGES[PetState.SIT])
            self._schedule_next_blink()
            return

        self.set_image(BLINK_FRAMES[self.blink_index])
        self.blink_index += 1

    def _stop_blink(self):
        self.blink_frame_timer.stop()
        self.blink_index = 0

    # ------------------------------------------------------------
    # 鼠标事件
    # ------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = _event_global_pos(event) - self.frameGeometry().topLeft()
            self._click_start_pos = _event_global_pos(event)
            self._is_dragging = False
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            end_pos = _event_global_pos(event)
            if (end_pos - self._click_start_pos).manhattanLength() < 5:
                self.click_timer.start(250)
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            current_pos = _event_global_pos(event)

            if (current_pos - self._click_start_pos).manhattanLength() >= 5:
                if not self._is_dragging:
                    self._is_dragging = True
                    self.show_bubble("嗯？要去哪儿？")

            self.move(current_pos - self.drag_pos)

            if self.bubble.isVisible():
                self._update_bubble_position()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.click_timer.stop()
            self.show_menu(_event_global_pos(event))
            event.accept()

    def contextMenuEvent(self, event):
        self.show_menu(_event_global_pos(event))
        event.accept()


def main():
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    win = PetWindow()
    win.show()

    if hasattr(app, "exec"):
        sys.exit(app.exec())
    else:
        sys.exit(app.exec_())


if __name__ == "__main__":
    main()