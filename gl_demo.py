import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject
import cairo
import numpy as np
from OpenGL.GL import *
import pyopencl as cl

mem = cl.mem_flags

vs = """
#version 460 core
layout(location = 0) uniform vec2 shift;
layout(location = 1) uniform vec2 scale;

layout (location = 0) in vec4 pos;

void main()
{
    gl_Position.xy = pos.xy * scale.xy + shift.xy;
    gl_Position.zw = vec2(0, 1);
}
"""

fs = """
#version 460 core
out vec4 color;

void main()
{
    color = vec4(1.0f, 0.5f, 0.2f, 1.0f);
}
"""


def createShader(shader_type, shader_source):
    shader = glCreateShader(shader_type)
    glShaderSource(shader, shader_source)
    glCompileShader(shader)

    status = glGetShaderiv(shader, GL_COMPILE_STATUS)
    if status == GL_FALSE:
        log = glGetShaderInfoLog(shader)
        shader_type_str = ""
        if shader_type is GL_VERTEX_SHADER:
            shader_type_str = "vertex"
        elif shader_type is GL_GEOMETRY_SHADER:
            shader_type_str = "geometry"
        elif shader_type is GL_FRAGMENT_SHADER:
            shader_type_str = "fragment"

        print("Compilation failure for " + shader_type_str + " shader:\n" +
              log.decode("utf-8"))

    return shader


def createProgram(*shaders):
    program = glCreateProgram()
    _ = [glAttachShader(program, shader) for shader in shaders]
    glLinkProgram(program)

    status = glGetProgramiv(program, GL_LINK_STATUS)
    if status == GL_FALSE:
        log = glGetProgramInfoLog(program)
        print("Program compilation failure:\n" + log)

    return program


class Gui:
    def __init__(self, glade_file):
        handlers = {
            'onDestroy': Gtk.main_quit,
            'onCreateContext': self.on_create_context,
            'onRealize': self.on_realize,
            'onUnrealize': self.on_unrealize,
            'onResize': self.on_resize,
            'onRender': self.on_render,
        }

        self.builder = Gtk.Builder()
        self.builder.add_from_file(glade_file)
        self.builder.connect_signals(handlers)

        self._texture = None
        self._vertex_buffer = None
        self._vertex_object = None
        self._vertex_shader = None
        self._fragment_shader = None
        self._shader_program = None
        self._context = None
        self._command_queue = None

        self.window = self.builder.get_object("window")
        self.window.show_all()

    def on_create_context(self, gl_area):
        ctx = gl_area.get_window().create_gl_context()
        ctx.set_required_version(4, 6)
        ctx.set_debug_enabled(True)
        print("ctx realize:", ctx.realize())
        ctx.make_current()

        from pyopencl.tools import get_gl_sharing_context_properties
        platform = cl.get_platforms()[-1]
        devices = platform.get_devices()
        properties = [(cl.context_properties.PLATFORM, platform)
                      ] + get_gl_sharing_context_properties()
        self._context = cl.Context(devices=devices, properties=properties)
        self._command_queue = cl.CommandQueue(self._context)

        return ctx

    def on_realize(self, gl_area):
        gl_area.get_context().make_current()

        self._texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self._texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 800, 800, 0, GL_RGB,
                     GL_UNSIGNED_BYTE, None)
        t = cl.GLTexture(self._context, mem.READ_ONLY, GL_TEXTURE_2D, 0, self._texture, dims=2)

        vertex_data = np.array(
            [[-1, -1, 0, 1], [1, -1, 0, 1], [1, 1, 0, 1], [-1, 1, 0, 1]],
            np.float32)

        self._vertex_buffer = glGenBuffers(1)
        self._vertex_object = glGenVertexArrays(1)
        glBindVertexArray(self._vertex_object)
        glBindBuffer(GL_ARRAY_BUFFER, self._vertex_buffer)
        glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data,
                     GL_STATIC_DRAW)
        glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 16, None)
        glEnableVertexAttribArray(0)

        vertex_shader = createShader(GL_VERTEX_SHADER, vs)
        fragment_shader = createShader(GL_FRAGMENT_SHADER, fs)
        self._program = createProgram(vertex_shader, fragment_shader)

        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)

        glClearColor(0.0, 1.0, 0.0, 1.0)

    def on_unrealize(self, gl_area):
        gl_area.get_context().make_current()

        glDeleteTextures([self._texture])
        glDeleteBuffers(1, [self._vertex_buffer])
        glDeleteVertexArrays(1, [self._vertex_object])
        glDeleteProgram(self._program)

        self._command_queue = None
        self._context = None

    def on_resize(self, gl_area, width, height):
        pass

    def on_render(self, gl_area, gl_context):
        glClear(GL_COLOR_BUFFER_BIT)
        glUseProgram(self._program)
        glBindVertexArray(self._vertex_object)
        glUniform2f(0, -0.5, 0.0)
        glUniform2f(1, 0.5, 1.0)
        glDrawArrays(GL_TRIANGLE_FAN, 0, 4)
        glUniform2f(0, 0.5, 0.0)
        glUniform2f(1, 0.5, 1.0)
        glDrawArrays(GL_TRIANGLE_FAN, 0, 4)
        return True


Gui('gl.glade')
Gtk.main()