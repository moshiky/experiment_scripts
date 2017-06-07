
import os
import shutil
from logger import Logger
from git_handler import GitHandler
from experiment_consts import ExperimentConsts
from evaluation_consts import EvaluationConsts
from java_execution_manager import JavaExecutionManager


class ExperimentEvaluator:

    def __init__(self):
        self.__logger = Logger()
        self.__git_handler = GitHandler(self.__logger)
        self.__java_execution_manager = JavaExecutionManager(self.__logger)

    def generate_results(self):

        self.__logger.log("begin result generation")

        # read id list
        with open(EvaluationConsts.ID_FILE_PATH, 'rb') as user_ids_file:
            user_ids = user_ids_file.read().replace('\r', '').split('\n')

        if user_ids[-1] == '':
            user_ids = user_ids[:-1]
        self.__logger.log("running {num_ids} ids:\n{ids}".format(num_ids=len(user_ids), ids='\n'.join(user_ids)))

        # checkout the evaluation code
        self.__git_handler.checkout_branch(
            EvaluationConsts.EVALUATION_BRANCH_NAME,
            EvaluationConsts.EVALUATION_SOURCE_PATH
        )

        # dictionary that contains all the problematic branches
        failed_branches = dict()

        # for each experiment type
        for experiment_type in EvaluationConsts.EXPERIMENT_TYPE_KEYS.keys():

            # modify evaluation code to run the specific experiment
            with open(EvaluationConsts.MAIN_FILE_PATH, 'rb') as main_file:
                main_file_content = main_file.read()

            new_string = \
                EvaluationConsts.EXPERIMENT_CONFIGURATION_BASE_STRING.format(
                    experiment_id=EvaluationConsts.EXPERIMENT_TYPE_KEYS[experiment_type]
                )
            for experiment_id in EvaluationConsts.EXPERIMENT_TYPE_KEYS.values():
                experiment_id_string = \
                    EvaluationConsts.EXPERIMENT_CONFIGURATION_BASE_STRING.format(experiment_id=experiment_id)
                if main_file_content.find(experiment_id_string) > -1:
                    main_file_content = main_file_content.replace(experiment_id_string, new_string)
                    break

            with open(EvaluationConsts.MAIN_FILE_PATH, 'wb') as main_file:
                main_file.write(main_file_content)

            # for each id
            for user_id in user_ids:

                # checkout user code
                user_branch_name = \
                    ExperimentConsts.EXPERIMENT_USER_BRANCH_NAME_FORMAT.format(
                        user_name=user_id,
                        experiment_type=experiment_type
                    )
                self.__logger.log('running {branch_name}'.format(branch_name=user_branch_name))

                try:
                    self.__git_handler.checkout_branch(
                        user_branch_name,
                        EvaluationConsts.USER_SOURCE_PATH
                    )
                except Exception, ex:
                    if ex.message.find(EvaluationConsts.BRANCH_NOT_FOUND_EXCEPTION_STRING) > -1:
                        self.__logger.error('branch not found: {branch_name}'.format(branch_name=user_branch_name))
                        failed_branches[user_branch_name] = EvaluationConsts.BRANCH_NOT_FOUND_EXCEPTION_STRING
                    else:
                        failed_branches[user_branch_name] = ex.message
                    continue

                # duplicate evaluation code
                evaluation_with_user_code_folder_path = \
                    os.path.join(EvaluationConsts.EVALUATION_SOURCE_BASE_PATH, user_branch_name)

                if not os.path.exists(evaluation_with_user_code_folder_path):
                    os.makedirs(evaluation_with_user_code_folder_path)

                evaluation_with_user_code_folder_path = \
                    os.path.join(evaluation_with_user_code_folder_path, EvaluationConsts.SOURCE_FOLDER_NAME)

                try:
                    shutil.copytree(
                        EvaluationConsts.EVALUATION_SOURCE_PATH,
                        evaluation_with_user_code_folder_path
                    )
                except WindowsError, ex:
                    if ex.winerror != 183:
                        raise ex

                # copy relevant experiment file
                for file_name_to_replace in EvaluationConsts.EXPERIMENT_REPLACE_FILES[experiment_type]:

                    source_path = \
                        os.path.join(
                            EvaluationConsts.USER_SOURCE_PATH,
                            file_name_to_replace
                        )

                    destination_path = \
                        os.path.join(
                            evaluation_with_user_code_folder_path,
                            file_name_to_replace
                        )

                    shutil.copy2(source_path, destination_path)

                # compile and run code
                try:
                    self.__java_execution_manager.run_code(evaluation_with_user_code_folder_path)
                except Exception, ex:
                    failed_branches[user_branch_name] = ex.message

        self.__logger.log("failed branches:\n{failed_branches}".format(
            failed_branches='\n'.join(key + ' = ' + failed_branches[key] for key in failed_branches.keys())
        ))

if __name__ == '__main__':
    experiment_evaluator = ExperimentEvaluator()
    experiment_evaluator.generate_results()
