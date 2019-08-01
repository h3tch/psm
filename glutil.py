import numpy as np
from OpenGL.GL import *


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


class Texture2D:
    def __init__(self, width, height):
        self._gl_object = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self._gl_object)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, width, height, 0, GL_RGBA,
                     GL_UNSIGNED_BYTE, None)

    def __del__(self):
        if self._gl_object is not None:
            glDeleteTextures(self._gl_object)
            self._gl_object = None

    def bind(self):
        glBindTexture(GL_TEXTURE_2D, self._gl_object)

    @property
    def obj(self):
        return self._gl_object


class Quad2D:
    def __init__(self):
        vertex_data = np.array(
            [[-1, -1, 0, 0], [1, -1, 1, 0], [1, 1, 1, 1], [-1, 1, 0, 1]],
            np.float32)

        self._vertex_buffer = glGenBuffers(1)
        self._vertex_object = glGenVertexArrays(1)
        glBindVertexArray(self._vertex_object)
        glBindBuffer(GL_ARRAY_BUFFER, self._vertex_buffer)
        glBufferData(GL_ARRAY_BUFFER, vertex_data.nbytes, vertex_data,
                     GL_STATIC_DRAW)
        glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 16, None)
        glEnableVertexAttribArray(0)

    def __del__(self):
        if self._vertex_buffer is not None:
            glDeleteBuffers(1, [self._vertex_buffer])
            self._vertex_buffer = None
        if self._vertex_object is not None:
            glDeleteVertexArrays(1, [self._vertex_object])
            self._vertex_object = None

    def bind(self):
        glBindVertexArray(self._vertex_object)

    def draw(self):
        glDrawArrays(GL_TRIANGLE_FAN, 0, 4)


class DrawTexture:
    vs = """
    #version 440 core
    layout(location = 0) uniform vec2 shift;
    layout(location = 1) uniform vec2 scale;

    //layout (location = 0) in vec4 pos;

    out vec2 uv;

    void main()
    {
        const vec4 vertices[] = {
            vec4(0, 0, 0, 0),
            vec4(1, 0, 1, 0),
            vec4(1, 1, 1, 1),
            vec4(0, 1, 0, 1)
        };
        vec4 p = vertices[gl_VertexID];
        gl_Position.xy = (p.xy * scale.xy + shift.xy) * 2.0 - 1.0;
        gl_Position.zw = vec2(0, 1);
        uv = p.zw;
    }
    """

    fs = """
    #version 440 core
    layout(location = 2) uniform int frame;

    layout(binding = 0) uniform sampler2D tex;

    in vec2 uv;

    out vec4 color;

    void main()
    {
        color = texture(tex, uv);
        //color[frame % 3] = 1.0;
    }
    """

    def __init__(self):
        self._vertex_quad = Quad2D()

        vertex_shader = createShader(GL_VERTEX_SHADER, self.vs)
        fragment_shader = createShader(GL_FRAGMENT_SHADER, self.fs)
        self._program = createProgram(vertex_shader, fragment_shader)
        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)
        self.frame = 0

    def __del__(self):
        del self._vertex_quad

        if self._program is not None:
            glDeleteProgram(self._program)
            self._program = None

    def bind(self):
        glUseProgram(self._program)
        self._vertex_quad.bind()

    def draw(self, x, y, width, height, texture):
        glUniform2f(0, x, y)
        glUniform2f(1, width, height)
        glUniform1i(2, self.frame)
        glActiveTexture(GL_TEXTURE0)
        texture.bind()
        self._vertex_quad.draw()
        self.frame += 1
