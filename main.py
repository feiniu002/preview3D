import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QPushButton
from PyQt5.QtCore import Qt
from PyQt5 import uic
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5.QtOpenGL import QGLWidget
from PyQt5.QtCore import QTimer
import trimesh
import numpy as np
import os

class GLWidget(QGLWidget):
    def __init__(self, parent=None):
        super(GLWidget, self).__init__(parent)
        self.setMinimumSize(400, 400)
        # 保存初始状态的值
        self.initial_y_rotation = 270
        self.initial_zoom = 4.0
        
        # 初始化其他变量
        self.x_rotation = 0
        self.y_rotation = self.initial_y_rotation
        self.last_pos = None
        self.zoom = self.initial_zoom
        
        # 初始化模型相关变量
        self.model = None
        self.vertices = None
        self.faces = None
        self.model_scale = 1.0
        self.model_center = [0, 0, 0]
        
        # VBO相关变量
        self.vbo = None
        self.vertex_count = 0
        self.use_vbo = False
        
        # 添加动画相关变量
        self.fall_angle = 0
        self.fall_speed = 2  # 初始速度
        self.fall_acceleration = 0.8  # 加速度
        self.turn_angle = 0
        self.is_falling = False
        self.is_turning = False
        self.turn_stage = 0  # 0:未开始, 1:左转, 2:回正, 3:右转, 4:最终回正
        self.pause_time = 0
        self.pause_duration = 3  # 约250ms的停顿
        
        # 添加定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)
        
        # 加载默认模型
        self.load_default_model()

    def load_default_model(self):
        model_path = "An_elderly_man.glb"
        if os.path.exists(model_path):
            print(f"开始加载模型: {model_path}")
            result = self.load_model(model_path)
            if result:
                print("模型加载成功")
                print(f"顶点数量: {len(self.vertices)}")
                print(f"面片数量: {len(self.faces)}")
            else:
                print("模型加载失败")
        else:
            print(f"模型文件 {model_path} 不存在")
            
    def load_model(self, file_path):
        try:
            print(f"正在加载模型: {file_path}")
            # 加载GLB文件
            scene = trimesh.load(file_path)
            
            # 如果是场景，获取第一个网格
            if isinstance(scene, trimesh.Scene):
                print("加载的是场景文件")
                meshes = list(scene.geometry.values())
                if not meshes:
                    print("错误：模型不包含任何网格")
                    return False
                print(f"场景中包含 {len(meshes)} 个网格")
                self.model = meshes[0]
            else:
                print("加载的是单个网格")
                self.model = scene
            
            # 获取顶点和面
            self.vertices = self.model.vertices
            self.faces = self.model.faces
            
            print(f"模型信息:")
            print(f"- 顶点数量: {len(self.vertices)}")
            print(f"- 面片数量: {len(self.faces)}")
            
            # 创建顶点数组
            vertices_array = []
            for face in self.faces:
                for vertex_id in face:
                    vertices_array.extend(self.vertices[vertex_id])
            
            # 转换为numpy数组
            self.vertex_data = np.array(vertices_array, dtype=np.float32)
            self.vertex_count = len(self.vertex_data) // 3
            
            # 计算缩放和中心
            extents = self.model.extents
            if extents is not None and max(extents) > 0:
                self.model_scale = 2.0 / max(extents)
                print(f"模型尺寸: {extents}")
                print(f"缩放系数: {self.model_scale}")
            else:
                self.model_scale = 1.0
                print("警告：无法获取模型尺寸，使用默认缩放")
            
            self.model_center = self.model.centroid
            print(f"模型中心点: {self.model_center}")
            
            # 如果支持VBO，则创建VBO
            if self.use_vbo:
                try:
                    if self.vbo is None:
                        self.vbo = glGenBuffers(1)
                    
                    # 绑定VBO并上传数据
                    glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
                    glBufferData(GL_ARRAY_BUFFER, self.vertex_data.nbytes, self.vertex_data, GL_STATIC_DRAW)
                    glBindBuffer(GL_ARRAY_BUFFER, 0)
                except Exception as e:
                    print(f"VBO创建失败，将使用即时模式渲染: {str(e)}")
                    self.use_vbo = False
            
            print("模型加载成功")
            self.updateGL()
            return True
        except Exception as e:
            print(f"加载模型失败: {str(e)}")
            print(f"错误类型: {type(e).__name__}")
            import traceback
            print("详细错误信息:")
            print(traceback.format_exc())
            self.model = None
            self.vertices = None
            self.faces = None
            self.model_scale = 1.0
            return False

    def wheelEvent(self, event):
        # 获取滚轮滚动的角度
        delta = event.angleDelta().y()
        # 根据滚动方向调整缩放因子
        if delta > 0:
            self.zoom -= 0.5
        else:
            self.zoom += 0.5
        # 限制缩放范围
        self.zoom = max(0.5, min(10.0, self.zoom))
        self.updateGL()
        
    def initializeGL(self):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glEnable(GL_DEPTH_TEST)
        
        # 检查是否支持VBO
        if not bool(glGenBuffers):
            print("警告：显卡不支持VBO，将使用即时模式渲染")
            self.use_vbo = False
        else:
            self.use_vbo = True

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
        self.fall_speed = 1  # 重置初始速度
        
    def turn_left_right(self):
        if not self.is_turning:
            self.is_turning = True
            self.turn_stage = 1
            self.turn_angle = 0
            self.pause_time = 0
            print("开始转动动画：第1阶段 - 向左转")

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluLookAt(0, 0, self.zoom, 0, 0, 0, 0, 1, 0)
        
        # 先应用基础旋转
        glRotatef(self.x_rotation, 1, 0, 0)
        
        # 处理左右转动画
        if self.is_turning:
            if self.pause_time > 0:
                self.pause_time -= 1
                if self.pause_time == 0:
                    self.turn_stage += 1
            else:
                if self.turn_stage == 1:  # 左转
                    self.turn_angle -= 15  # 负值表示向左转
                    if self.turn_angle <= -90:
                        self.turn_angle = -90
                        self.pause_time = self.pause_duration
                elif self.turn_stage == 2:  # 回正
                    self.turn_angle += 15
                    if self.turn_angle >= 0:
                        self.turn_angle = 0
                        self.pause_time = self.pause_duration
                elif self.turn_stage == 3:  # 右转
                    self.turn_angle += 15  # 正值表示向右转
                    if self.turn_angle >= 90:
                        self.turn_angle = 90
                        self.pause_time = self.pause_duration
                elif self.turn_stage == 4:  # 最终回正
                    self.turn_angle -= 15
                    if self.turn_angle <= 0:
                        self.turn_angle = 0
                        self.is_turning = False
                        self.turn_stage = 0

            glRotatef(self.turn_angle, 0, 1, 0)
        
        # 应用初始朝向
        glRotatef(self.y_rotation, 0, 1, 0)
        
        # 处理倒下动画 - 添加加速效果
        if self.is_falling:
            # 增加速度
            self.fall_speed += self.fall_acceleration
            # 使用当前速度更新角度
            self.fall_angle += self.fall_speed
            
            # 限制最大角度
            if self.fall_angle >= 90:
                self.fall_angle = 90
                self.is_falling = False
                self.fall_speed = 1  # 重置速度
            
            glRotatef(self.fall_angle, 0, 0, 1)
        
        if self.model is not None:
            glColor3f(0.8, 0.8, 0.8)
            glScalef(self.model_scale, self.model_scale, self.model_scale)
            
            if hasattr(self, 'model_center'):
                glTranslatef(-self.model_center[0], -self.model_center[1], -self.model_center[2])
            
            if self.use_vbo and self.vbo is not None:
                # 使用VBO渲染
                glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
                glEnableClientState(GL_VERTEX_ARRAY)
                glVertexPointer(3, GL_FLOAT, 0, None)
                glDrawArrays(GL_TRIANGLES, 0, self.vertex_count)
                glDisableClientState(GL_VERTEX_ARRAY)
                glBindBuffer(GL_ARRAY_BUFFER, 0)
            else:
                # 使用即时模式渲染
                glBegin(GL_TRIANGLES)
                for face in self.faces:
                    for vertex_id in face:
                        vertex = self.vertices[vertex_id]
                        glVertex3f(vertex[0], vertex[1], vertex[2])
                glEnd()

    def reset_model(self):
        """重置模型到初始状态"""
        print("重置模型状态")
        # 重置所有动画和旋转状态
        self.x_rotation = 0
        self.y_rotation = self.initial_y_rotation
        self.zoom = self.initial_zoom
        self.fall_angle = 0
        self.turn_angle = 0
        self.is_falling = False
        self.is_turning = False
        self.turn_stage = 0
        self.pause_time = 0
        self.fall_speed = 1
        # 更新显示
        self.updateGL()

    def mouseReleaseEvent(self, event):
        """处理鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            # 当点击鼠标左键时重置模型
            self.reset_model()
            event.accept()

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
        
        # 设置按钮透明
        transparent_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                color: transparent;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 10);
            }
        """
        
        # 将"往后倒"和"左右转"按钮设置为透明
        self.pushButton_3.setStyleSheet(transparent_style)
        self.pushButton_turnLeftRight.setStyleSheet(transparent_style)
        
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