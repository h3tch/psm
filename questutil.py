import glob
import numpy as np
import os
import psm.filter
import psychopy.data
import time
import glutil


class Quests:
    def __init__(self, user, conditions, n_trials):
        self._quests = psychopy.data.MultiStairHandler(conditions=conditions,
                                                       nTrials=n_trials,
                                                       stairType='QUEST')
        self._quests.next()

        self._start_time = time.time()

        self._data_folder = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self._data_folder, exist_ok=True)
        count = len(glob.glob(os.path.join(self._data_folder, '*/'))) + 1
        self._data_folder = os.path.join(self._data_folder, f'{count}')
        os.makedirs(self._data_folder, exist_ok=True)
        self._backup_file = os.path.join(self._data_folder, 'backup')

        with open(os.path.join(self._data_folder, 'info.txt'), 'w') as file:
            file.write(f'user: {user}\n')

    def save_csv(self, filename):
        with open(filename, 'w') as file:
            file.write(
                'label,artifact_size,line_angle,velocity,filter_noise,filter_radius,decrease,side,correct,x,y\n'
            )
            for quest in self._quests.staircases:
                condition = quest.condition
                extra_info = quest.extraInfo if quest.extraInfo is not None else []
                label = condition['label']
                artifact_size = condition['artifact_size']
                line_angle = np.rad2deg(condition['line_angle'])
                filter_radius = condition['filter_radius']
                filter_noise = condition['filter_noise']
                velocity = condition['velocity']
                for intensity, response, info in zip(quest.intensities, quest.data, extra_info):
                    file.write(
                        f'{label},{artifact_size},{line_angle},{velocity},{filter_noise},{filter_radius*intensity},{response},{info[0]},{info[1]},{info[2]},{info[3]}\n'
                    )

    def save(self):
        self._quests.saveAsJson(os.path.join(self._data_folder, 'result.json'))
        self.save_csv(os.path.join(self._data_folder, 'result.csv'))

    def next(self):
        self._quests.saveAsPickle(self._backup_file)
        return self._quests.next()

    def add_response(self, selected_left, correct_response, x, y):
        increase_radius = 0
        decrease_radius = 1
        self._add_response_info_to_current_quest(selected_left, correct_response, x, y)
        self._quests.addResponse(
            increase_radius if correct_response else decrease_radius)

    def cannot_decide_response(self):
        decrease_radius = 1
        self._add_empty_response_info_to_current_quest()
        self._quests.addResponse(decrease_radius)

    def _add_response_info_to_current_quest(self, selected_left, correct_response, x, y):
        current_quest = self._quests.currentStaircase
        if current_quest.extraInfo is None:
            current_quest.extraInfo = []
        if correct_response is None:
            side = 'none'
            correct_response = ''
            x = ''
            y = ''
        else:
            side = 'left' if selected_left else 'right'
        current_quest.extraInfo.append((side, '1' if correct_response else '0', x, y))

    def _add_empty_response_info_to_current_quest(self):
        self._add_response_info_to_current_quest(False, None, 0, 0)

    @property
    def done_trials(self):
        return self._quests.totalTrials

    @property
    def remaining_trials(self):
        return self.number_of_trials - self.done_trials

    @property
    def number_of_trials(self):
        return self._quests.nTrials * len(self._quests.staircases)

    @property
    def percent_done(self):
        return (100.0 * self.done_trials) / self.number_of_trials

    @property
    def running_time(self):
        return time.time() - self._start_time

    @property
    def average_trial_time(self):
        return self.running_time / self.done_trials if self.done_trials > 0 else 5.0

    @property
    def estimated_minutes_remaining(self):
        return int(
            np.ceil(self.average_trial_time * self.remaining_trials / 60.0))


class StimuliGenerator:
    def __init__(self, image_size):
        self._image_size = image_size

        self.reference_image = glutil.Texture2D(image_size, image_size)
        self.artifact_image = glutil.Texture2D(image_size, image_size)

        self._draw_line = psm.filter.Line(
            image_size, image_size, self.reference_image.obj)

        self._draw_artifact_line = psm.filter.ArtifactLine(
            image_size, image_size, self.artifact_image.obj)

        self.settings(1, 0, 0, 0, 0)
        self._last_time = time.time()

    def __del__(self):
        del self.reference_image
        del self.artifact_image
        self._draw_line = None
        self._draw_artifact_line = None

    def has_selected_artifact(self, selected_left):
        return self.flip_images if selected_left else not self.flip_images

    def settings(self, artifact_size, line_angle, filter_radius, filter_noise, velocity):
        image_angle = np.random.rand() * np.pi * 2
        image_size = self._image_size
        half_image_size = image_size / 2.0

        line_angle = np.clip(line_angle, -np.pi / 4, np.pi / 4)
        line_nx = -np.sin(line_angle)
        line_ny = np.cos(line_angle)

        sin, cos = np.sin(image_angle), np.cos(image_angle)

        def rotate(x, y):
            u = x - half_image_size
            v = y - half_image_size
            x = cos * u - sin * v + half_image_size
            y = sin * u + cos * v + half_image_size
            return x, y

        min_size = -filter_radius
        max_size = image_size + filter_radius - 1
        corners = [(min_size, min_size), (max_size, min_size),
                   (min_size, max_size), (max_size, max_size)]
        corners = [rotate(corner[0], corner[1]) for corner in corners]

        corner_distances = [
            corner[0] * line_nx + corner[1] * line_ny for corner in corners
        ]

        self.artifact_size = max(1, artifact_size)
        self.line_x = half_image_size + artifact_size * (
            np.random.rand() * 2 - 1)
        self.line_y = half_image_size + artifact_size * (
            np.random.rand() * 2 - 1)
        self.current_line_x = self.line_x
        self.current_line_y = self.line_y
        self.line_angle = line_angle
        self.line_nx = line_nx
        self.line_ny = line_ny
        self.line_vx = self.line_nx * velocity
        self.line_vy = self.line_ny * velocity
        self.filter_radius = max(0.0, filter_radius)
        self.filter_noise = np.clip(filter_noise, 0, 255) / 255.0
        self.image_angle = image_angle
        self.flip_images = np.random.rand() >= 0.5
        self.min_image_d = min(corner_distances)
        self.max_image_d = max(corner_distances)
        self.frame = 0

    def render(self, reference=True, artifact=True):
        current_time = time.time()
        elapsed_time = current_time - self._last_time
        self._last_time = current_time

        # if there is no animation we do not need to render again
        if self.frame > 0 and self.line_vx == 0 and self.line_vy == 0:
            return False

        self._draw_line(self.current_line_x,
                        self.current_line_y,
                        self.line_angle,
                        self.filter_radius,
                        self.filter_noise,
                        self.image_angle)
        self._draw_artifact_line(
            self.current_line_x,
            self.current_line_y,
            self.line_angle,
            self.artifact_size,
            self.filter_radius,
            self.filter_noise,
            self.image_angle)

        self.current_line_x += self.line_vx * elapsed_time
        self.current_line_y += self.line_vy * elapsed_time
        current_line_d = self.current_line_x * self.line_nx + self.current_line_y * self.line_ny
        if current_line_d < self.min_image_d or self.max_image_d < current_line_d:
            current_line_d = min(max(current_line_d, self.min_image_d),
                                    self.max_image_d)
            self.current_line_x = self.line_nx * current_line_d
            self.current_line_y = self.line_ny * current_line_d
            self.line_vx = -self.line_vx
            self.line_vy = -self.line_vy

        self.frame += 1
        return True
