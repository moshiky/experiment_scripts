
import os


class EvaluationConsts:

    EVALUATION_SOURCE_BASE_PATH = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'evaluation_source'))

    # should config!
    SOURCE_FOLDER_NAME = 'mario_experiment'

    EVALUATION_SOURCE_PATH = os.path.join(EVALUATION_SOURCE_BASE_PATH, 'evaluation', SOURCE_FOLDER_NAME)

    USER_SOURCE_PATH = os.path.join(EVALUATION_SOURCE_BASE_PATH, 'user', SOURCE_FOLDER_NAME)

    # should config!
    RUN_CONFIGURATION_FILE_TEMPLATE = \
        os.path.join('{folder_path}', 'src', 'main', 'java', 'competition', 'richmario', 'SimpleExperiment.java')

    # should config!
    EXPERIMENT_CONFIGURATION_BASE_STRING = 'AgentType[] agentsToRun = new AgentType[] {{ AgentType.{0} }};'

    EVALUATION_BRANCH_NAME = 'evaluation_version'

    ID_FILE_PATH = os.path.join(os.path.dirname(__file__), 'ids.txt')
    EVALUATION_IDS_FILE_PATH = os.path.join(os.path.dirname(__file__), 'eval_ids.txt')

    # should config!
    EXPERIMENT_TYPE_KEYS = {
        'abstraction': 'Abstraction',
        'reward_shaping': 'RewardShaping',
        'similarities': 'Similarities'
    }
    SIMILARITIES_ON_REWARD_SHAPING_CONFIGURATION_KEY = 'SimilaritiesOnRewardShaping'

    # should config!
    EXPERIMENT_REPLACE_FILES = {
        'abstraction': [
            os.path.join('src', 'main', 'java', 'competition', 'richmario', 'agents', 'AbstractionEnsembleAgent.java')
        ],
        'reward_shaping': [
            os.path.join('src', 'main', 'java', 'competition', 'richmario', 'experiment', 'ShapingManager.java')
        ],
        'similarities': [
            os.path.join('src', 'main', 'java', 'competition', 'richmario', 'experiment', 'SimilarityManager.java')
        ]
    }

    BRANCH_NOT_FOUND_EXCEPTION_STRING = 'BRANCH_NOT_FOUND'

    MAX_THREADS = 3

    # replace parts for similarities on reward shaping
    SIMILARITIES_ON_REWARD_SHAPING_TEMPLATE = r'''if ({0}) {{'''

    ORIGINAL_CONDITIONS = {
        'similarities': r'AgentType.Similarities != SimpleExperiment.activeAgentType',
        'reward_shaping': r'AgentType.RewardShaping != SimpleExperiment.activeAgentType'
    }

    SIMILARITIES_ON_REWARD_SHAPING_COND = {\
        'reward_shaping' : '({reward_shaping_condition}) && (AgentType.SimilaritiesOnRewardShaping != SimpleExperiment.activeAgentType)'.format(
            reward_shaping_condition=ORIGINAL_CONDITIONS['reward_shaping']
        ),
        'similarities' : '({similarities_condition}) && (AgentType.SimilaritiesOnRewardShaping != SimpleExperiment.activeAgentType)'.format(
            similarities_condition=ORIGINAL_CONDITIONS['similarities']
        )
    }

    ABSTRACTION_FILE_CORRECTIONS = [
        (
            'float worldRewardUntilNow',
            'float worldRewardUntilNow, boolean update'
        ),
        (
            '        for (AbstractionQLambdaAgent agent : agents) {\r\n'
            '            agent.update(this.previousState, this.previousAction, actionReward, currentState, nextAction);\r\n'
            '        }'
            ,
            '        if (update) {\r\n'
            '           for (AbstractionQLambdaAgent agent : agents) {\r\n'
            '                agent.update(this.previousState, this.previousAction, actionReward, currentState, nextAction);\r\n'
            '            }\r\n'
            '        }'
        ),
        (
            '    public int egreedyActionSelection(double[] state) {\r\n'
            '        if(RNG.randomDouble() < epsilon) {'
            ,
            '    public int egreedyActionSelection(double[] state, boolean isTrainMode) {\r\n'
            '        if((RNG.randomDouble() < epsilon) && isTrainMode) {'
        ),
        (
            'int nextAction = egreedyActionSelection(currentState);',
            'int nextAction = egreedyActionSelection(currentState, update);'
        )
    ]
