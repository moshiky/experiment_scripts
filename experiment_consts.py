
import os


class ExperimentConsts:

    EXPERIMENT_TYPES = [
        'abstraction', 'reward_shaping', 'similarities'
    ]

    EXPERIMENT_TYPE_STRINGS = {
        'abstraction': 'Abstraction',
        'reward_shaping': 'Reward Shaping',
        'similarities': 'Similarities'
    }

    BASE_BRANCH_NAME = 'experiment'
    EXPERIMENT_BASE_BRANCH_NAME_FORMAT = '{base_branch_name}_{experiment_type}'
    EXPERIMENT_USER_BRANCH_NAME_FORMAT = '{user_name}_{experiment_type}'

    EXPERIMENT_FOLDER_NAME = 'predator_experiment_3'

    WORKING_DIRECTORY_PATH = os.path.join(os.path.dirname(__file__), '..', EXPERIMENT_FOLDER_NAME)

    LOGGING_FILE_DIR = os.path.join(os.path.dirname(__file__), 'logs')
    LOGGING_FILE_PATH_FORMAT = os.path.join(LOGGING_FILE_DIR, 'experiment_manager__{timestamp}.log')

