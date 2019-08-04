import contextlib
import copy
import enum
import glob
import itertools
import numpy as np
import os
import pickle
from psychopy.data import QuestHandler
import time


class Response(enum.Enum):
    NONE = 0
    SAW_ARTIFACT = 1
    SAW_LINE = 2
    CANNOT_DECIDE = 3


class MultiQuest:
    def __init__(self,
                 user,
                 conditions,
                 random_reference_probability=0.0,
                 **kwargs):
        self._user = user
        self._conditions = conditions
        self._quests = [QuestHandler(**condition) for condition in conditions]
        self._quest_labels = [condition['label'] for condition in conditions]
        self._random_reference_trials = None
        self._random_reference_probability = random_reference_probability

        self._active_quest_history = []
        self._max_active_quest_history = 0
        self._active_quest_index = self._random_quest_index()
        self._is_reference = self._random_reference_decision
        self._reference_quest = copy.deepcopy(self._active_quest)
        self._trial_counter = 0
        self._quest_changes = 0
        self._quest_changed = False
        self._start_time = time.time()
        self._previous_response = Response.NONE

        self._init_output_folder(user)
        self._load_backup()

    def saw_artifact_response(self, duration, selection, x, y):
        self._previous_response = Response.SAW_ARTIFACT
        self._add_response_info_to_current_quest(duration=duration,
                                                 saw_artifact=True,
                                                 selection=selection,
                                                 x=x,
                                                 y=y)
        self._save_backup()

    def saw_line_response(self, duration):
        self._previous_response = Response.SAW_LINE
        self._add_response_info_to_current_quest(duration=duration,
                                                 saw_artifact=False,
                                                 selection='none',
                                                 x='',
                                                 y='')
        self._save_backup()

    def cannot_decide_response(self, duration):
        self._previous_response = Response.CANNOT_DECIDE
        self._add_response_info_to_current_quest(duration=duration,
                                                 saw_artifact=False,
                                                 selection='none',
                                                 x='',
                                                 y='')
        self._save_backup()

    def undo(self):
        self._load_backup(-1)

    def next(self):
        if not self._next_trial():
            raise StopIteration
        intensity = self._quest.next()
        condition = self._active_condition
        return intensity, condition

    def save(self):
        self._save_csv(os.path.join(self._data_folder, 'result.csv'))

    def _save_csv(self, filename):
        self._backup_file(filename)
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

    @property
    def _random_reference_decision(self):
        if self._random_reference_trials is None or len(self._random_reference_trials) == 0:
            n = 20
            s = int(n * (1.0 - self._random_reference_probability))
            t = int(n * self._random_reference_probability)
            a = np.zeros((s + t,), np.bool)
            a[:t] = True
            self._random_reference_trials = np.random.permutation(a).tolist()
        return self._random_reference_trials.pop() == 1

    def _add_response_info_to_current_quest(self, duration, saw_artifact, selection, x, y):
        quest = self._quest
        intensity = quest.intensities[-1]
        change = 'increase' if saw_artifact else 'decrease'
        if self._is_reference:
            correct = False if saw_artifact else True
        else:
            correct = True if saw_artifact else False

        active = self._active_quest
        active.addOtherData('user', self._user)
        active.addOtherData('globalTrialId', self.trial_count)
        active.addOtherData('questTrialId', self.quest_trial_count)
        active.addOtherData('intensity', intensity)
        active.addOtherData('intensityChange', change)
        active.addOtherData('selection', selection)
        active.addOtherData('correct', '1' if correct else '0')
        active.addOtherData('x', x)
        active.addOtherData('y', y)
        active.addOtherData('is_reference', self._is_reference)
        active.addOtherData('duration', duration)

        if change == 'increase':
            quest.addResponse(0)
        elif change == 'decrease':
            quest.addResponse(1)

    def _next_trial(self):
        self._trial_counter += 1
        if self._active_quest_index_needs_update:
            self._is_reference = self._random_reference_decision
            self._quest_changed = True
            self._quest_changes += 1
            self._next_quest_index()
            if self._is_reference and self._has_active_quest:
                self._reference_quest = copy.deepcopy(self._active_quest)
            else:
                self._reference_quest = None
        else:
            self._quest_changed = False
        return self._has_active_quest

    def _next_quest_index(self):
        self._active_quest_history.append(self._active_quest_index)
        max_active_quest_history = int(self.remaining_quests / 3)
        while len(self._active_quest_history) > max_active_quest_history:
            del self._active_quest_history[0]
        self._active_quest_index = self._next_active_quest_index()

    def _next_active_quest_index(self):
        indices = [i for i, q in enumerate(self._quests) if not q.finished]
        if len(indices) == 0:
            self._active_quest_index = None
            return
        if len(indices) > 1:
            with contextlib.suppress(ValueError, AttributeError):
                for i in self._active_quest_history:
                    indices.remove(i)
        return np.random.choice(indices)

    def _init_output_folder(self, user=None):
        self._data_folder = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self._data_folder, exist_ok=True)
        if user is None or len(user) == 0:
            count = len(glob.glob(os.path.join(self._data_folder, '*/'))) + 1
            user = f'{count}'
        self._user = user
        self._data_folder = os.path.join(self._data_folder, user)
        os.makedirs(self._data_folder, exist_ok=True)

    def _load_backup(self, undo=0):
        n_backups = len(glob.glob(os.path.join(self._data_folder, '*.pickle')))
        if n_backups == 0:
            return False

        backup = max(1, n_backups - abs(undo))

        for i in range(backup+1, n_backups+1):
            src = os.path.join(self._data_folder, f'{i}.pickle')
            self._backup_file(src)

        filename = os.path.join(self._data_folder, f'{backup}.pickle')
        with open(filename, 'rb') as file_handle:
            backup = pickle.load(file_handle)

        for key in self.__dict__.keys():
            setattr(self, key, getattr(backup, key))

        return True

    def _save_backup(self):
        n_backups = len(glob.glob(os.path.join(self._data_folder, '*.pickle')))
        filename = os.path.join(self._data_folder, f'{n_backups + 1}.pickle')
        self._backup_file(filename)
        with open(filename, 'wb') as file_handle:
            pickle.dump(self, file_handle, protocol=pickle.HIGHEST_PROTOCOL)

    def _backup_file(self, filename):
        if os.path.exists(filename):
            dst = f'{filename}.backup'
            while os.path.exists(dst):
                dst = f'{dst}.newer'
            os.rename(filename, dst)
            return dst

    @property
    def is_reference(self):
        return self._is_reference

    @property
    def quest_changes(self):
        return self._quest_changes

    @property
    def quest_changed(self):
        return self._quest_changed

    @property
    def trial_count(self):
        return self._trial_counter

    @property
    def quest_trial_count(self):
        quest = self._quest
        if 'globalTrialId' in quest.otherData:
            return len(quest.otherData['globalTrialId'])
        return 0

    @property
    def _has_active_quest(self):
        return self._active_quest_index is not None

    @property
    def _quest(self):
        return self._reference_quest if self._is_reference else self._active_quest

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
    def _active_quest_index_needs_update(self):
        if self.previous_response == Response.SAW_LINE:
            return True
        quest = self._quest
        if quest.finished:
            return True
        if len(quest.data):
            return quest.data[-1] == 0
        return False

    @property
    def previous_response(self):
        return self._previous_response

    @property
    def done_trials(self):
        return sum([max(q.thisTrialN, 0) for q in self._quests])

    @property
    def remaining_trials(self):
        return self.number_of_trials - self.done_trials

    @property
    def remaining_quests(self):
        return sum(1 for q in self._quests if not q.finished)

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
