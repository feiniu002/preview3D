import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt
from PyQt5 import uic
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5.QtOpenGL import QGLWidget
from PyQt5.QtCore import QTimer

class GLWidget(QGLWidget):
    def __init__(self, parent=None):
        super(GLWidget, self).__init__(parent)
        self.setMinimumSize(400, 400)
        self.x_rotation = 0
        self.y_rotation = 0
        self.last_pos = None
        self.zoom = 8.0
        
        # 添加动画相关变量
        self.fall_angle = 0
        self.turn_angle = 0
        self.is_falling = False
        self.is_turning = False
        self.turn_direction = 1  # 1表示左转，-1表示右转
        self.turn_stage = 0  # 0:初始, 1:左转, 2:回正, 3:右转, 4:回正
        
        # 添加定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)  # 约60fps
        
    def mousePressEvent(self, event):
        self.last_pos = event.pos()
        
    def mouseMoveEvent(self, event):
        if self.last_pos:
            dx = event.x() - self.last_pos.x()
            dy = event.y() - self.last_pos.y()
            
            self.x_rotation += dy
            self.y_rotation += dx
            
            self.updateGL()
            self.last_pos = event.pos()
            
    def mouseReleaseEvent(self, event):
        self.last_pos = None
        
    def wheelEvent(self, event):
        # 获取滚轮滚动的角度
        delta = event.angleDelta().y()
        # 根据滚动方向调整缩放因子
        if delta > 0:
            self.zoom -= 0.5
        else:
            self.zoom += 0.5
        # 限制缩放范围
        self.zoom = max(1.0, min(10.0, self.zoom))
        self.updateGL()
        
    def initializeGL(self):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glEnable(GL_DEPTH_TEST)
        
    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, width/height, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)
        
    def update_animation(self):
        if self.is_falling or self.is_turning:
            self.updateGL()
            
    def fall_backward(self):
        self.is_falling = True
        self.fall_angle = 0
        
    def turn_left_right(self):
        self.is_turning = True
        self.turn_stage = 1
        self.turn_direction = -1  # 修改初始方向为-1，表示左转
        self.turn_angle = 0
        
    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluLookAt(0, 0, self.zoom, 0, 0, 0, 0, 1, 0)
        
        # 处理倒下动画
        if self.is_falling:
            self.fall_angle += 2
            if self.fall_angle >= 90:
                self.fall_angle = 90
                self.is_falling = False
            glRotatef(self.fall_angle, -1, 0, 0)
            
        # 处理左右转动动画
        if self.is_turning:
            if self.turn_stage == 1:  # 左转
                self.turn_angle += 2 * self.turn_direction
                if abs(self.turn_angle) >= 90:
                    self.turn_angle = 90 * self.turn_direction
                    self.turn_stage = 2
            elif self.turn_stage == 2:  # 左转回正
                self.turn_angle -= 2 * self.turn_direction
                if self.turn_angle == 0:
                    self.turn_stage = 3
                    self.turn_direction = 1  # 改为右转方向
            elif self.turn_stage == 3:  # 右转
                self.turn_angle += 2 * self.turn_direction
                if abs(self.turn_angle) >= 90:
                    self.turn_angle = 90 * self.turn_direction
                    self.turn_stage = 4
            elif self.turn_stage == 4:  # 右转回正
                self.turn_angle -= 2 * self.turn_direction
                if self.turn_angle == 0:
                    self.is_turning = False
                    self.turn_stage = 0
            glRotatef(self.turn_angle, 0, 1, 0)
            
        # 应用鼠标旋转
        glRotatef(self.x_rotation, 1, 0, 0)
        glRotatef(self.y_rotation, 0, 1, 0)
        
        # 绘制长方体
        glBegin(GL_QUADS)
        # 前面
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(-1.0, -2.0, 1.0)
        glVertex3f(1.0, -2.0, 1.0)
        glVertex3f(1.0, 2.0, 1.0)
        glVertex3f(-1.0, 2.0, 1.0)
        
        # 后面
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(-1.0, -2.0, -1.0)
        glVertex3f(-1.0, 2.0, -1.0)
        glVertex3f(1.0, 2.0, -1.0)
        glVertex3f(1.0, -2.0, -1.0)
        
        # 上面
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(-1.0, 2.0, -1.0)
        glVertex3f(-1.0, 2.0, 1.0)
        glVertex3f(1.0, 2.0, 1.0)
        glVertex3f(1.0, 2.0, -1.0)
        
        # 下面
        glColor3f(1.0, 1.0, 0.0)
        glVertex3f(-1.0, -2.0, -1.0)
        glVertex3f(1.0, -2.0, -1.0)
        glVertex3f(1.0, -2.0, 1.0)
        glVertex3f(-1.0, -2.0, 1.0)
        
        # 右面
        glColor3f(1.0, 0.0, 1.0)
        glVertex3f(1.0, -2.0, -1.0)
        glVertex3f(1.0, 2.0, -1.0)
        glVertex3f(1.0, 2.0, 1.0)
        glVertex3f(1.0, -2.0, 1.0)
        
        # 左面
        glColor3f(0.0, 1.0, 1.0)
        glVertex3f(-1.0, -2.0, -1.0)
        glVertex3f(-1.0, -2.0, 1.0)
        glVertex3f(-1.0, 2.0, 1.0)
        glVertex3f(-1.0, 2.0, -1.0)
        glEnd()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('mainWindow.ui', self)
        
        # 替换widget为GLWidget
        self.gl_widget = GLWidget(self)
        layout = self.groupBox.layout()
        layout.replaceWidget(self.widget, self.gl_widget)
        self.widget.deleteLater()
        
        # 连接按钮信号
        self.pushButton_connect.clicked.connect(self.on_connect)
        self.pushButton_disconnect.clicked.connect(self.on_disconnect)
        self.pushButton_fallBackward.clicked.connect(self.gl_widget.fall_backward)
        self.pushButton_3.clicked.connect(self.gl_widget.fall_backward)
        self.pushButton_turnLeftRight.clicked.connect(self.gl_widget.turn_left_right)
        
        # 添加连接状态定时器
        self.connect_timer = QTimer(self)
        self.connect_timer.timeout.connect(self.update_connect_status)
        self.is_connecting = False
        self.is_disconnecting = False
        self.connect_count = 0
        
    def update_connect_status(self):
        if self.is_connecting:
            self.connect_count += 1
            if self.connect_count <= 5:
                self.labelConnectStatus.setText(f"正在连接...{self.connect_count}/5")
            else:
                self.connect_timer.stop()
                self.is_connecting = False
                self.connect_count = 0
                self.labelConnectStatus.setText("已连接")
                
        elif self.is_disconnecting:
            self.connect_count += 1
            if self.connect_count <= 5:
                self.labelConnectStatus.setText(f"正在断开...{self.connect_count}/5")
            else:
                self.connect_timer.stop()
                self.is_disconnecting = False
                self.connect_count = 0
                self.labelConnectStatus.setText("已断开")
        
    def on_connect(self):
        self.is_connecting = True
        self.is_disconnecting = False
        self.connect_count = 0
        self.connect_timer.start(1000)  # 每秒更新一次
        
    def on_disconnect(self):
        self.is_disconnecting = True
        self.is_connecting = False
        self.connect_count = 0
        self.connect_timer.start(1000)  # 每秒更新一次

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())