#include <GL/glew.h>
#include <GLFW/glfw3.h>
#include <chrono>
#include <iostream>
#include <thread>
#include <cstring>
#include <string>
#include <fstream>
#include <vector>
#define _USE_MATH_DEFINES
#include <cmath>

template<typename real_t>
real_t deg2rad(real_t deg)
{
    return deg * (M_PI / 180.0);
}

static const float vertexdata[] = {
    0.0f, 0.0f, 0.0f, 0.0f,
    1.0f, 0.0f, 1.0f, 0.0f,
    1.0f, 1.0f, 1.0f, 1.0f,
    0.0f, 1.0f, 0.0f, 1.0f
};

static const char* vs =
"#version 440 core\n"
"layout(location = 0) uniform vec2 shift;\n"
"layout(location = 1) uniform vec2 scale;\n"

"in vec4 pos;\n"

"void main()\n"
"{\n"
"    gl_Position.xy = (pos.xy * scale.xy + shift.xy) * 2.0 - 1.0;\n"
"    gl_Position.zw = vec2(0, 1);\n"
"}";

static std::string readFile(const std::string& filename)
{
    std::ifstream file(filename, std::ios::ate | std::ios::binary);

    if (!file.is_open())
        throw std::runtime_error("failed to open file!");

    size_t fileSize = (size_t)file.tellg();
    std::vector<char> buffer(fileSize);

    file.seekg(0);
    file.read(buffer.data(), fileSize);
    file.close();

    return std::string(buffer.begin(), buffer.end());
}

void error_callback(int error, const char* description)
{
    std::cerr << "Error: " << description << '\n';
}

static void key_callback(GLFWwindow* window, int key, int scancode, int action, int mods)
{
    if (key == GLFW_KEY_ESCAPE && action == GLFW_PRESS)
        glfwSetWindowShouldClose(window, GLFW_TRUE);
}

GLuint createShader(const GLenum type, const char* code, GLint length)
{
    GLint success = 0;
    char log[1024];
    auto shader = glCreateShader(type);
    glShaderSource(shader, 1, &code, &length);
    glCompileShader(shader);
    glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
    if (success == GL_FALSE) {
        glGetShaderInfoLog(shader, 1024, nullptr, log);
        std::cerr << log << '\n';
        throw std::runtime_error("Shader compilation failed");
    }
    return shader;
}

int main()
{
    if (!glfwInit())
        return -1;
    glfwSetErrorCallback(error_callback);
    glfwWindowHint(GLFW_RESIZABLE, GLFW_FALSE);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 5);
    auto window = glfwCreateWindow(800, 800, "My Title", NULL, NULL);
    if (!window)
        return glfwTerminate(), -2;
    glfwSetKeyCallback(window, key_callback);
    glfwMakeContextCurrent(window);

    if (glewInit() != GLEW_OK)
        return glfwTerminate(), -3;

    glfwSwapInterval(1);
    int width, height;
    glfwGetFramebufferSize(window, &width, &height);
    glViewport(0, 0, width, height);

    GLuint vertexbuffer = -1;
    glGenBuffers(1, &vertexbuffer);
    GLuint vertexinput = -1;
    glGenVertexArrays(1, &vertexinput);
    glBindVertexArray(vertexinput);
    glBindBuffer(GL_ARRAY_BUFFER, vertexbuffer);
    glBufferData(GL_ARRAY_BUFFER, 4*4*4, vertexdata, GL_STATIC_DRAW);
    glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 16, 0);
    glEnableVertexAttribArray(0);

    auto fs = readFile("shader/artifact.frag");
    auto vertexshader = createShader(GL_VERTEX_SHADER, vs, std::strlen(vs));
    auto fragmentshader = createShader(GL_FRAGMENT_SHADER, fs.c_str(), fs.length());

    GLint success;
    auto program = glCreateProgram();
    glAttachShader(program, vertexshader);
    glAttachShader(program, fragmentshader);
    glLinkProgram(program);
    glGetProgramiv(program, GL_LINK_STATUS, &success);
    if (success == GL_FALSE)
        throw std::runtime_error("Program linking failed");

    glDeleteShader(vertexshader);
    glDeleteShader(fragmentshader);

    auto scaleuniform = glGetUniformLocation(program, "scale");
    auto shiftuniform = glGetUniformLocation(program, "shift");
    auto uniform_artifact_size = glGetUniformLocation(program, "artifact_size");
    auto uniform_line = glGetUniformLocation(program, "line");
    auto uniform_filter_radius = glGetUniformLocation(program, "filter_radius");

    double time = glfwGetTime();
    const float line_angle = deg2rad(5.0f);
    const float line_nx = -std::sin(line_angle);
    const float line_ny = std::cos(line_angle);
    float line_cx = width * 0.5f;
    float line_cy = height * 0.5f;
    float line_vx = line_nx * 80;
    float line_vy = line_ny * 80;

    while (!glfwWindowShouldClose(window)) {
        double currentTime = glfwGetTime();
        double elapsedTime = currentTime - time;
        time = currentTime;

        line_cx += line_vx * elapsedTime;
        line_cy += line_vy * elapsedTime;

        auto distance = line_cx * line_nx + line_cy * line_ny;

        if (distance < 0.f || distance > width * line_nx + height * line_ny) {
            line_vx = -line_vx;
            line_vy = -line_vy;
        }

        glUseProgram(program);
        glUniform2f(scaleuniform, 1.0f, 1.0f);
        glUniform2f(shiftuniform, 0.0f, 0.0f);
        glUniform1ui(uniform_artifact_size, 8);
        glUniform3f(uniform_line, line_cx, line_cy, line_angle);
        glUniform1f(uniform_filter_radius, 40.0f);
        glDrawArrays(GL_TRIANGLE_FAN, 0, 4);
        glfwSwapBuffers(window);
        glfwPollEvents();
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }

    glDeleteProgram(program);
    glDeleteBuffers(1, &vertexbuffer);
    glDeleteVertexArrays(1, &vertexinput);
    glfwDestroyWindow(window);
    glfwTerminate();
    return 0;
}