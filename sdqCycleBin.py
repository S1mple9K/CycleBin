import ctypes  # 导入ctypes库，用于调用Windows API
import os  # 导入os库，用于操作系统相关的功能
import sys  # 导入sys库，用于访问与Python解释器密切相关的变量和函数
import send2trash  # 导入send2trash库，用于将文件移动到回收站
import yaml  # 导入yaml库，用于读取YAML配置文件
from PyQt5.QtWidgets import QApplication, QLabel, QSystemTrayIcon, QMenu  # 导入PyQt5的QWidget模块
from PyQt5.QtGui import QPixmap, QIcon, QPainter  # 导入PyQt5的Gui模块
from PyQt5.QtCore import Qt, QPoint, QTimer  # 导入PyQt5的QtCore模块

# 检查是否已经有一个实例在运行
def is_program_running():
    # 创建互斥体
    mutex_name = "Global\\MonitorClientMutex"  # 互斥体名称，全局唯一
    h_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)  # 创建互斥体
    # 检查互斥体是否已经存在
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        print("程序已经在运行.")
        return True
    return False

class DraggableIcon(QLabel):
    def __init__(self, image_path):
        super().__init__()
        self.config = self.load_config()  # 加载配置文件
        self.idle_time = self.config['idle_time']  # 从配置文件中获取idle_time的值
        self.clicked_state_time = self.config['clicked_state_time']  # 从配置文件中获取clicked_state_time的值
        self.draging_state_isupdate = self.config['draging_state_isupdate']  # 从配置文件中获取draging_state_isupdate的值
        self.original_pixmap = QPixmap(image_path)  # 加载原始图片
        self.setPixmap(QPixmap(image_path))  # 设置窗口的图片
        self.setAttribute(Qt.WA_TranslucentBackground)  # 设置窗口背景为透明
        self.setAttribute(Qt.WA_NoSystemBackground)  # 设置窗口无系统背景
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)  # 设置窗口无边框且始终置顶
        self.setGeometry(100, 100, 500, 500)  # 设置窗口的初始位置和大小
        self.drag_position = QPoint(0, 0)  # 初始化拖动位置
        self.dragging = False  # 标记是否正在拖动
        self.setAcceptDrops(True)  # 允许拖放操作
        self.init_tray()  # 初始化系统托盘图标
        self.idle_timer = QTimer()  # 创建一个计时器
        self.idle_timer.timeout.connect(self.idle_timeout)  # 连接计时器超时信号
        self.reset_idle_timer()  # 重置计时器

    # 加载配置文件
    def load_config(self):
        with open('config.yml', 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)

    # 初始化系统托盘图标
    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(self.original_pixmap))
        self.tray_icon.setVisible(True)
        self.tray_icon.setToolTip('Draggable Icon')
        self.tray_icon.activated.connect(self.icon_activated)
        self.tray_menu = QMenu()
        exit_action = self.tray_menu.addAction("Exit")
        exit_action.triggered.connect(self.close_application)
        self.tray_icon.setContextMenu(self.tray_menu)

    # 托盘图标被激活时的槽函数
    def icon_activated(self, reason):
        self.show()
        self.reset_idle_timer()

    # 鼠标按下事件的槽函数
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.pos()
            # self.toggle_image()
            self.reset_idle_timer()

    # 鼠标释放事件的槽函数
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.dragging:
                self.setPixmap(QPixmap("img/默认状态.png"))
            else:
                self.toggle_image()
            self.dragging = False
            self.reset_idle_timer()

    # 切换图片的槽函数
    def toggle_image(self):
        self.setPixmap(QPixmap("img/拖拽.png"))
        if not self.dragging:
            QTimer.singleShot(self.clicked_state_time*1000, self.revert_image)

    # 恢复原始图片的槽函数
    def revert_image(self):
        self.setPixmap(self.original_pixmap)

    # 鼠标移动事件的槽函数
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.dragging = True
            self.idle_timer.stop()
            delta = QPoint(event.pos() - self.drag_position)
            new_pos = self.pos() + delta
            self.move(new_pos)
            if self.draging_state_isupdate:
                self.toggle_image()

    # 拖拽进入事件的槽函数
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setPixmap(QPixmap("img/文件悬浮.png"))

    # 拖拽离开事件的槽函数
    def dragLeaveEvent(self, event):
        self.setPixmap(self.original_pixmap)

    # 拖拽放下事件的槽函数
    def dropEvent(self, event):
        self.setPixmap(self.original_pixmap)
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            self.move_file_to_trash(file_path)

    # 将文件移动到回收站的静态方法
    @staticmethod
    def move_file_to_trash(file_path):
        try:
            file_path = os.path.normpath(file_path)
            send2trash.send2trash(file_path)
            print(f"File {file_path} moved to trash.")
        except Exception as e:
            print(f"Error moving file to trash: {e}")

    # 窗口关闭事件的槽函数
    def closeEvent(self, event):
        self.hide()
        event.ignore()

    # 退出应用程序的槽函数
    def close_application(self):
        self.tray_icon.hide()
        QApplication.quit()

    # 重置空闲计时器的槽函数
    def reset_idle_timer(self):
        self.idle_timer.stop()
        self.idle_timer.start(self.idle_time * 1000)  # 10 seconds

    # 空闲计时器超时的槽函数
    def idle_timeout(self):
        self.draw_images()

    # 长期不点击
    def draw_images(self):
        combined_pixmap = QPixmap(self.size())
        combined_pixmap.fill(Qt.transparent)
        painter = QPainter(combined_pixmap)
        base_pixmap = QPixmap("img/长期不点击.png")
        painter.drawPixmap(0, 200, base_pixmap)
        painter.end()
        self.setPixmap(combined_pixmap)

# 程序的主入口点
if __name__ == '__main__':
    if is_program_running():
        ctypes.windll.user32.MessageBoxTimeoutW(
            None, "一个人只允许拥有一个史迪仔", "警告", 0x40 | 0x1, 0, 1000
        )
        sys.exit(0)
    app = QApplication(sys.argv)
    ex = DraggableIcon("img/默认状态.png")
    ex.show()
    sys.exit(app.exec_())