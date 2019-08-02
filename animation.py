from OpenGL.GLUT import *
from OpenGL.GL import *
import sys
import numpy as np
import json
import glutil
import quest
import stimuli
import time
import os
import study


s = None


class Event:
    def __init__(self, x, y):
        self.x = x
        self.y = y


def main():
    global s

    settings, conditions = study.load_config('test.json')
    stimuli_size = settings['stimuli_size'] if 'stimuli_size' in settings else 400
    window_size = settings['window_size'] if 'window_size' in settings else stimuli_size

    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA)
    glutInitWindowSize(window_size, window_size)
    glutCreateWindow('Study')
    glutSetOption(GLUT_ACTION_ON_WINDOW_CLOSE, GLUT_ACTION_GLUTMAINLOOP_RETURNS)

    s = study.Study(None, settings, conditions, user='')
    s.on_realize(stimuli_size)

    glutMouseFunc(mouse)
    glutKeyboardFunc(keyboard)
    glutDisplayFunc(render)
    glutIdleFunc(render)
    glutMainLoop()

    s.on_quit()
    s.on_unrealize(None)


def mouse(button, state, x, y):
    global s
    if button == 0 and state == 1:  # LEFT UP
        s.on_different(None, Event(x, y))


def keyboard(key, x, y):
    global s
    if key == b' ':  # SPACE
        s.on_cannot_decide(None)
    elif key == b'\x08':  # BACKSPACE
        s.on_undo(None)
    elif key == b'l':
        s.on_is_line(None)


def render():
    global s
    s.on_render(None, None)
    glutSetWindowTitle(s.window_title)
    glutSwapBuffers()


if __name__ == '__main__':
    main()
