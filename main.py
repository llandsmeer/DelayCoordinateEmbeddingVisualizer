import sys, ctypes, signal
import numpy as np
from OpenGL import GL, GLU
from PyQt5 import QtCore, QtGui, QtWidgets

import lorenz
from data_form import DataFormDialog

vertex_shader = (GL.GL_VERTEX_SHADER, '''
    #version 150
    
    mat4 rotationMatrix(vec3 axis, float angle) {
        axis = normalize(axis);
        float s = sin(angle);
        float c = cos(angle);
        float oc = 1.0 - c;
        
        return mat4(oc * axis.x * axis.x + c,           oc * axis.x * axis.y - axis.z * s,  oc * axis.z * axis.x + axis.y * s,  0.0,
                    oc * axis.x * axis.y + axis.z * s,  oc * axis.y * axis.y + c,           oc * axis.y * axis.z - axis.x * s,  0.0,
                    oc * axis.z * axis.x - axis.y * s,  oc * axis.y * axis.z + axis.x * s,  oc * axis.z * axis.z + c,           0.0,
                    0.0,                                0.0,                                0.0,                                1.0);
    }

    in float position;
    uniform samplerBuffer tex;
    uniform int t1;
    uniform int t2;
    uniform float q;

    void main() {
        mat4 mat = rotationMatrix(vec3(0, 1, 0), q);
        float p = position;
        float x = texelFetch(tex, gl_VertexID).r;
        float y = texelFetch(tex, gl_VertexID+t1).r;
        float z = texelFetch(tex, gl_VertexID+t2).r;
        vec4 pos = mat * vec4(p*0.001 + x, y, z, 1) / 2;
        gl_Position = vec4(pos.xyz, 1.0);
        //gl_Position = vec4(p*0.01 + x/2, y/2, z/2, 1.0);
    }
''')

fragment_shader = (GL.GL_FRAGMENT_SHADER, '''
    #version 150

    out vec4 color;

    void main() {
        float factor = clamp(exp(-(gl_FragCoord.z+2)/1), 0, 1.0);
        //vec4 back = vec4(0.0, 7.0, 1.0, 1.0);
        //vec4 fore = vec4(1.0, 0.5, 0.0, 1.0);
        vec4 fore = vec4(0.0, 7.0, 1.0, 1.0);
        vec4 back = vec4(0.0, 0.0, 0.3, 1.0);
        color = mix(back, fore, factor);
    }
''')


def compile_shader(shader):
    shader_type, shader_source = shader
    shader_id = GL.glCreateShader(shader_type)
    GL.glShaderSource(shader_id, shader_source)
    GL.glCompileShader(shader_id)
    compile_status = GL.glGetShaderiv(shader_id, GL.GL_COMPILE_STATUS)
    return shader_id


def build_draw_program(vertex_shader, fragment_shader):
    program = GL.glCreateProgram()
    vertex = compile_shader(vertex_shader)
    fragment = compile_shader(fragment_shader)
    GL.glAttachShader(program, vertex)
    GL.glAttachShader(program, fragment)
    GL.glLinkProgram(program)
    link_status = GL.glGetProgramiv(program, GL.GL_LINK_STATUS)
    return program


def attach(program, name, data):
    vao = GL.glGenVertexArrays(1)
    GL.glBindVertexArray(vao)
    vbo = GL.glGenBuffers(1)
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
    GL.glBufferData(GL.GL_ARRAY_BUFFER, data, GL.GL_STATIC_DRAW)
    attr = GL.glGetAttribLocation(program, name)
    GL.glEnableVertexAttribArray(attr)
    GL.glVertexAttribPointer(attr, 1, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

    tex = GL.glGenTextures(1)
    GL.glBindTexture(GL.GL_TEXTURE_BUFFER, tex)
    GL.glTexBuffer(GL.GL_TEXTURE_BUFFER, GL.GL_R32F, vbo)


class Window(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.widget = Widget()
        color = self.palette().color(QtGui.QPalette.Background)
        self.widget.bgcolor = color
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.widget)
        formwidget = QtWidgets.QWidget()
        form = QtWidgets.QVBoxLayout()
        form.setAlignment(QtCore.Qt.AlignTop)
        formwidget.setMaximumWidth(200)
        formwidget.setLayout(form)
        layout.addWidget(formwidget)
        self.embed1label = QtWidgets.QLabel('Embedding 1 [0]')
        form.addWidget(self.embed1label)
        self.embed1 = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.embed1.valueChanged.connect(self.propchanged)
        form.addWidget(self.embed1)
        self.embed2label = QtWidgets.QLabel('Embedding 2 [0]')
        form.addWidget(self.embed2label)
        self.embed2 = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.embed2.valueChanged.connect(self.propchanged)
        form.addWidget(self.embed2)
        form.addWidget(QtWidgets.QLabel('Point Size'))
        self.ps = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.ps.valueChanged.connect(self.propchanged)
        form.addWidget(self.ps)
        self.ps.setValue(1)
        self.setLayout(layout)
        self.embed1.setMaximum(100)
        self.embed2.setMaximum(100)
        self.ps.setMinimum(1)
        self.ps.setMaximum(15)
        self.btnload = QtWidgets.QPushButton('Load Data')
        self.btnload.clicked.connect(self.on_click_load)
        form.addWidget(self.btnload)
        self.load_data_dialog = DataFormDialog()
        formwidget.palette().setColor(QtGui.QPalette.Background, QtCore.Qt.transparent)

    def on_click_load(self):
        if self.load_data_dialog.exec() == QtWidgets.QDialog.Accepted:
            data = self.load_data_dialog.col
            self.embed1.setMaximum(len(data)//10)
            self.embed2.setMaximum(len(data)//10)
            self.widget.load_data(data)

    def propchanged(self):
        self.widget.t1 = self.embed1.value()
        self.widget.t2 = self.embed2.value()
        self.widget.ps = self.ps.value()
        self.embed1label.setText(f'Embedding 1 [{-self.widget.t1}]')
        self.embed2label.setText(f'Embedding 2 [{-self.widget.t2}]')


class Widget(QtWidgets.QOpenGLWidget):
    def __init__(self):
        super().__init__()
        surface_format = QtGui.QSurfaceFormat()
        surface_format.setMajorVersion(3)
        surface_format.setMajorVersion(2)
        surface_format.setProfile(QtGui.QSurfaceFormat.CoreProfile)
        surface_format.setOption(QtGui.QSurfaceFormat.DebugContext)
        self.setFormat(surface_format)
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_tick)
        self.update_timer.start(1000//60)
        self.tick = 0
        self.t1 = self.t2 = 0
        self.q = 0
        y = lorenz.lorenz(num_steps=2000000)
        self.data = y.astype('float32')
        self.newdata = False

    def update_tick(self):
        self.tick += 1
        self.q += 0.005
        self.update()

    def log_debug_message(self, msg):
        print(msg.message())

    def load_data(self, data):
        data = np.array(data).astype('float32')
        data = (data - data.min()) / (data.max() - data.min())
        data = 2*data - 1
        data = data * 2
        self.data = data
        self.newdata = True

    def initializeGL(self):
        self.makeCurrent()
        self.ctx = self.context()
        self.logger = QtGui.QOpenGLDebugLogger(self)
        self.logger.initialize()
        self.logger.messageLogged.connect(self.log_debug_message)
        self.logger.startLogging()
        draw_program = build_draw_program(vertex_shader, fragment_shader)
        GL.glUseProgram(draw_program)
        attach(draw_program, 'position', self.data)
        GL.glPointSize(self.ps)
        self.attr_t1 = GL.glGetUniformLocation(draw_program, 't1')
        self.attr_t2 = GL.glGetUniformLocation(draw_program, 't2')
        self.attr_q = GL.glGetUniformLocation(draw_program, 'q')
        GL.glEnable(GL.GL_DEPTH_TEST)
        c = self.bgcolor
        GL.glClearColor(c.red() / 0xff, c.green() / 0xff, c.blue() / 0xff, 1.0)

    def paintGL(self):
        if self.newdata:
            GL.glBufferData(GL.GL_ARRAY_BUFFER, self.data, GL.GL_STATIC_DRAW)
            self.newdata = False
        GL.glClear(GL.GL_COLOR_BUFFER_BIT |
                   GL.GL_DEPTH_BUFFER_BIT |
                   GL.GL_STENCIL_BUFFER_BIT)
        GL.glUniform1i(self.attr_t1, self.t1)
        GL.glUniform1i(self.attr_t2, self.t2)
        GL.glUniform1f(self.attr_q, self.q)
        GL.glPointSize(self.ps)
        GL.glDrawArrays(GL.GL_POINTS, 0, len(self.data)-max(self.t1, self.t2))
        GL.glFlush()
        self.ctx.swapBuffers(self.ctx.surface())

    def resizeGL(self, w, h):
        pass


def main():
    app = QtWidgets.QApplication(sys.argv)
    signal.signal(signal.SIGINT, lambda *a: app.quit())
    timer = QtCore.QTimer()
    timer.start(200)
    timer.timeout.connect(lambda: 'run interpreter to allow ctrl-c exit')
    window = Window()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()