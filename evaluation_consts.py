
import os


class EvaluationConsts:

    EVALUATION_SOURCE_BASE_PATH = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'evaluation_source'))

    SOURCE_FOLDER_NAME = 'predator_experiment_3'

    EVALUATION_SOURCE_PATH = os.path.join(EVALUATION_SOURCE_BASE_PATH, 'evaluation', SOURCE_FOLDER_NAME)

    USER_SOURCE_PATH = os.path.join(EVALUATION_SOURCE_BASE_PATH, 'user', SOURCE_FOLDER_NAME)

    MAIN_FILE_PATH = \
        os.path.join(EVALUATION_SOURCE_PATH, 'src', 'main', 'java', 'problem', 'predator', 'Experiments.java')

    EXPERIMENT_CONFIGURATION_BASE_STRING = 'int[]{{{experiment_id}}}'

    EVALUATION_BRANCH_NAME = 'evaluation_version'

    ID_FILE_PATH = os.path.join(os.path.dirname(__file__), 'ids.txt')

    EXPERIMENT_TYPE_KEYS = {
        'abstraction': 8,
        'reward_shaping': 11,
        'similarities': 10
    }

    EXPERIMENT_REPLACE_FILES = {
        'abstraction': [os.path.join('src', 'main', 'java', 'problem', 'predator', 'FeatureExtractor.java')],
        'reward_shaping': [os.path.join('src', 'main', 'java', 'problem', 'predator', 'ShapingManager.java')],
        'similarities': [os.path.join('src', 'main', 'java', 'problem', 'predator', 'SimilarityManager.java')]
    }

    BRANCH_NOT_FOUND_EXCEPTION_STRING = 'BRANCH_NOT_FOUND'
