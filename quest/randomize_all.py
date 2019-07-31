import glob
import itertools
import numpy as np
import os
import psychopy
import time


class Quests:
    def __init__(self,
                 user,
                 conditions,
                 n_trials,
                 random_reference_probability=0.0,
                 repeat_incorrect_random_reference_trials=False):
        self._quests = psychopy.data.MultiStairHandler(conditions=conditions,
                                                       stairType='simple')
        self._quests.next()

        self._trial_counter = 0

        total_n_trials = n_trials * len(conditions)
        self.number_of_random_trials = int(total_n_trials *
                                           random_reference_probability)
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
