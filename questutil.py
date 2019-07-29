import glob
import numpy as np
import os
import psm.filter
import psychopy.data
import time
import glutil
import itertools
from OpenGL.GL import glClear, glFlush, GL_COLOR_BUFFER_BIT


class Quests:
    def __init__(self,
                 user,
                 conditions,
                 n_trials,
                 random_trial_probability=0.0,
                 repeat_incorrect_random_reference_trials=False):
        self._quests = psychopy.data.MultiStairHandler(conditions=conditions,
                                                       stairType='simple')
        self._quests.next()

        self._trial_counter = 0

        total_n_trials = n_trials * len(conditions)
        self.number_of_random_trials = int(total_n_trials *
                                           random_trial_probability)
        total_n_trials += self.number_of_random_trials

        self._random_reference_trials = np.zeros((total_n_trials, ), np.int)
        self._random_reference_trials[:self.number_of_random_trials] = 1
        self._random_reference_trials = np.random.permutation(
            self._random_reference_trials).tolist()
        self._is_reference = False
        self._repeat_incorrect_reference_trials = repeat_incorrect_random_reference_trials

        self._data_folder = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self._data_folder, exist_ok=True)
        count = len(glob.glob(os.path.join(self._data_folder, '*/'))) + 1
        self._data_folder = os.path.join(self._data_folder, f'{count}')
        os.makedirs(self._data_folder, exist_ok=True)
        self._backup_file = os.path.join(self._data_folder, 'backup')

        with open(os.path.join(self._data_folder, 'info.txt'), 'w') as file:
            file.write(f'user: {user}\n')

        self._start_time = time.time()

    def save_csv(self, filename):
        with open(filename, 'w') as file:
            results = self._quest_results()
            keys = sorted(set(itertools.chain.from_iterable(results)))

            file.write(','.join(keys) + '\n')
            for result in results:
                try:
                    while True:
                        row = [
                            str(result[key].pop(0)) if key in result else ''
                            for key in keys
                        ]
                        file.write(','.join(row) + '\n')
                except IndexError:
                    pass

    def _quest_result(self, quest):
        n_values = max([0] + [len(v) for v in quest.otherData.values()])
        result = {}
        for k, v in quest.condition.items():
            result[k] = [v] * n_values
        return {**result, **quest.otherData}

    def _quest_results(self):
        return [self._quest_result(q) for q in self._quests.staircases]

    def save(self):
        self._quests.saveAsJson(os.path.join(self._data_folder, 'result.json'))
        self.save_csv(os.path.join(self._data_folder, 'result.csv'))

    def next(self):
        if len(self._random_reference_trials) > 0:
            self._is_reference = self._random_reference_trials.pop() == 1
        else:
            self._is_reference = False

        if self._is_reference:
            intensity, condition = self._random_pick()
        else:
            self._quests.saveAsPickle(self._backup_file)
            intensity, condition = self._quests.next()

        return intensity, condition, self._is_reference, True

    def _random_pick(self):
        i = np.random.randint(len(self._quests.staircases))
        quest = self._quests.staircases[i]
        condition = quest.condition
        intensity = quest.intensities[-1] if len(
            quest.intensities) > 0 else quest.startVal
        return intensity, condition

    def saw_artifact_response(self, selection, x, y):
        self._add_response_info_to_current_quest(True, selection, x, y)

        if self._is_reference and self._repeat_incorrect_reference_trials:
            index = np.random.randint(len(self._random_reference_trials))
            self._random_reference_trials.insert(index, 1)

    def cannot_decide_response(self):
        self._add_response_info_to_current_quest(False,
                                                 selection='none',
                                                 x='',
                                                 y='')

    def _add_response_info_to_current_quest(self, saw_artifact, selection, x,
                                            y):
        is_artifact = not self._is_reference

        quest = self._quests.currentStaircase

        if self._is_reference:
            correct = False if saw_artifact else True
        else:
            correct = True if saw_artifact else False

        if is_artifact:
            if saw_artifact:
                change = 'increase'
            else:
                change = 'decrease'
        else:
            change = 'none'

        intensity = quest.intensities[-1]

        globalTrialId = self._trial_counter
        self._trial_counter += 1
        questTrialId = len(quest.otherData['globalTrialId']
                           ) if 'globalTrialId' in quest.otherData else 0

        self._quests.addOtherData('globalTrialId', globalTrialId)
        self._quests.addOtherData('questTrialId', questTrialId)
        self._quests.addOtherData('intensity', intensity)
        self._quests.addOtherData('intensityChange', change)
        self._quests.addOtherData('selection', selection)
        self._quests.addOtherData('correct', '1' if correct else '0')
        self._quests.addOtherData('x', x)
        self._quests.addOtherData('y', y)

        if change == 'increase':
            self._quests.addResponse(0)
        elif change == 'decrease':
            self._quests.addResponse(1)

    @property
    def done_trials(self):
        return sum([
            max(s.thisTrialN, 0) for s in self._quests.staircases
            if not s.finished
        ])

    @property
    def remaining_trials(self):
        return self.number_of_trials - self.done_trials

    @property
    def number_of_trials(self):
        return sum(
            [s.nTrials for s in self._quests.staircases if not s.finished])

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


class MultiQuest:
    def __init__(self, user, conditions, **kwargs):
        self._user = user
        self._conditions = conditions
        self._quests = [
            psychopy.data.QuestHandler(**condition) for condition in conditions
        ]
        self._quest_labels = [condition['label'] for condition in conditions]
        self._active_quest_index = self._random_quest_index()
        self._active_quest_index_needs_update = False
        self._ended_quests = {}

        self._init_output_folder()
        self._is_reference = False
        self._trial_counter = 0
        self._reversal_counter = 0
        self._start_time = time.time()

    def saw_artifact_response(self, selection, x, y):
        self._add_response_info_to_current_quest(True, selection, x, y)

    def cannot_decide_response(self):
        self._add_response_info_to_current_quest(False,
                                                 selection='none',
                                                 x='',
                                                 y='')

    def next(self):
        if self._active_quest_index_needs_update:
            self._active_quest_index_needs_update = False
            quest_changed = True
            self._reversal_counter += 1
            self._next_quest()
        else:
            quest_changed = False

        if not self._has_active_quest:
            raise StopIteration
        intensity = self._active_quest.next()
        condition = self._active_condition
        return intensity, condition, self._is_reference, quest_changed

    def save(self):
        self._save_csv(os.path.join(self._data_folder, 'result.csv'))

    def _save_csv(self, filename):
        with open(filename, 'w') as file:
            results = self._quest_results()
            keys = sorted(set(itertools.chain.from_iterable(results)))

            file.write(','.join(keys) + '\n')
            for result in results:
                try:
                    while True:
                        row = [
                            str(result[key].pop(0)) if key in result else ''
                            for key in keys
                        ]
                        file.write(','.join(row) + '\n')
                except IndexError:
                    pass

    def _quest_result(self, label, condition, quest):
        n_values = max([0] + [len(v) for v in quest.otherData.values()])
        result = {'label': [label] * n_values, 'user': [self._user] * n_values}
        for k, v in condition.items():
            result[k] = [v] * n_values
        return {**result, **quest.otherData}

    def _quest_results(self):
        return [
            self._quest_result(l, c, q) for l, c, q in zip(
                self._quest_labels, self._conditions, self._quests)
        ]

    def _random_quest_index(self):
        return np.random.randint(len(self._quests))

    def _add_response_info_to_current_quest(self, saw_artifact, selection, x,
                                            y):
        is_artifact = not self._is_reference

        quest = self._active_quest

        if self._is_reference:
            correct = False if saw_artifact else True
        else:
            correct = True if saw_artifact else False

        if is_artifact:
            change = 'increase' if saw_artifact else 'decrease'
        else:
            change = 'none'

        intensity = self._active_quest.intensities[-1]

        globalTrialId = self._trial_counter
        self._trial_counter += 1
        questTrialId = len(quest.otherData['globalTrialId']
                           ) if 'globalTrialId' in quest.otherData else 0

        quest.addOtherData('globalTrialId', globalTrialId)
        quest.addOtherData('questTrialId', questTrialId)
        quest.addOtherData('intensity', intensity)
        quest.addOtherData('intensityChange', change)
        quest.addOtherData('selection', selection)
        quest.addOtherData('correct', '1' if correct else '0')
        quest.addOtherData('x', x)
        quest.addOtherData('y', y)

        if change == 'increase':
            quest.addResponse(0)
            self._active_quest_index_needs_update = True
        elif change == 'decrease':
            quest.addResponse(1)
            if quest.finished:
                self._active_quest_index_needs_update = True

    def _next_quest(self):
        self._update_active_quest_index()
        while self._has_active_quest and self._active_quest.finished:
            self._end_active_quest()
            self._update_active_quest_index()

    def _end_active_quest(self):
        self._ended_quests[self._active_label] = self._active_quest
        del self._quest_labels[self._active_quest_index]
        del self._quests[self._active_quest_index]

    def _update_active_quest_index(self):
        if len(self._quests) == 0:
            self._active_quest_index = None
            return

        next_active_quest = self._random_quest_index()

        while len(self._quests
                  ) > 1 and next_active_quest == self._active_quest_index:
            next_active_quest = self._random_quest_index()

        self._active_quest_index = next_active_quest

    def _init_output_folder(self):
        self._data_folder = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self._data_folder, exist_ok=True)
        count = len(glob.glob(os.path.join(self._data_folder, '*/'))) + 1
        self._data_folder = os.path.join(self._data_folder, f'{count}')
        os.makedirs(self._data_folder, exist_ok=True)

    @property
    def reversal_counter(self):
        return self._trial_counter

    @property
    def _has_active_quest(self):
        return self._active_quest_index is not None

    @property
    def _active_quest(self):
        return self._quests[self._active_quest_index]

    @property
    def _active_label(self):
        return self._quest_labels[self._active_quest_index]

    @property
    def _active_condition(self):
        return self._conditions[self._active_quest_index]

    @property
    def done_trials(self):
        return sum([max(q.thisTrialN, 0) for q in self._quests])

    @property
    def remaining_trials(self):
        return self.number_of_trials - self.done_trials

    @property
    def number_of_trials(self):
        return sum([q.nTrials for q in self._quests])

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
    def __init__(self, image_size, black_screen_timeout=0.0):
        self._image_size = image_size

        self.reference_image = glutil.Texture2D(image_size, image_size)
        self.artifact_image = glutil.Texture2D(image_size, image_size)

        self._clear_image = psm.filter.Clear()

        self._draw_line = psm.filter.Line(image_size, image_size,
                                          self.reference_image.obj)

        self._draw_artifact_line = psm.filter.ArtifactLine(
            image_size, image_size, self.artifact_image.obj)

        self.settings(1, 0, 0, 0, 0, 0, 1, True, black_screen_timeout)
        self._last_time = time.time()

    def __del__(self):
        del self.reference_image
        del self.artifact_image
        self._draw_line = None
        self._draw_artifact_line = None

    def has_selected_artifact(self, selected_left):
        return self.flip_images if selected_left else not self.flip_images

    def settings(self, artifact_size, line_angle, filter_radius, filter_noise,
                 filter_samples, velocity, image_samples, randomize, pause):
        if randomize:
            # self.image_angle = np.random.rand() * np.pi * 2
            self.image_angle = np.random.randint(4) * np.pi / 2
        image_size = self._image_size
        half_image_size = image_size / 2.0

        line_angle = np.clip(line_angle, -np.pi / 4, np.pi / 4)
        line_nx = -np.sin(line_angle)
        line_ny = np.cos(line_angle)

        sin, cos = np.sin(self.image_angle), np.cos(self.image_angle)

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

        if randomize:
            self.rand_x = 100 * (np.random.rand() * 2 - 1)
            self.rand_y = 100 * (np.random.rand() * 2 - 1)

        self.artifact_size = max(1, artifact_size)
        self.line_x = half_image_size + self.rand_x
        self.line_y = half_image_size + self.rand_y
        self.current_line_x = self.line_x
        self.current_line_y = self.line_y
        self.line_samples = 2
        self.line_angle = line_angle
        self.line_nx = line_nx
        self.line_ny = line_ny
        self.line_vx = self.line_nx * velocity
        self.line_vy = self.line_ny * velocity
        self.filter_radius = max(0.0, filter_radius)
        self.filter_noise = np.clip(filter_noise, 0, 255) / 255.0
        self.filter_samples = max(0.0, filter_samples)
        self.image_samples = min(max(image_samples, 1), 8)
        self.flip_images = np.random.rand() >= 0.5
        self.min_image_d = min(corner_distances)
        self.max_image_d = max(corner_distances)
        self.frame = 0
        if pause > 0.0:
            self._last_update_time = time.time()
            self._black_screen_timeout = pause

    def render(self, reference=True, artifact=True):
        current_time = time.time()
        elapsed_time = current_time - self._last_time
        self._last_time = current_time

        if current_time - self._last_update_time < self._black_screen_timeout:
            if reference:
                self._clear_image(self._draw_line.cl_image)
            if artifact:
                self._clear_image(self._draw_artifact_line.cl_image)
            return True

        # if there is no animation we do not need to render again
        if self.frame > 0 and self.line_vx == 0 and self.line_vy == 0:
            return False

        if reference:
            self._draw_line(self.current_line_x, self.current_line_y,
                            self.line_angle, self.filter_radius,
                            self.filter_noise, self.filter_samples,
                            self.image_angle)
        if artifact:
            self._draw_artifact_line(self.current_line_x, self.current_line_y,
                                     self.line_angle, self.artifact_size,
                                     self.filter_radius, self.filter_noise,
                                     self.filter_samples, self.image_angle,
                                     self.image_samples)

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
