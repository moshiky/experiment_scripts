
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

            self.__logger.log('evaluating experiment: {experiment_type}'.format(experiment_type=experiment_type))

            # modify evaluation code to run the specific experiment
            with open(EvaluationConsts.RUN_CONFIGURATION_FILE_PATH, 'rb') as configuration_file:
                configuration_file_content = configuration_file.read()

            # build current experiment configuration string
            current_configuration_string = \
                EvaluationConsts.EXPERIMENT_CONFIGURATION_BASE_STRING.format(
                    experiment_id=EvaluationConsts.EXPERIMENT_TYPE_KEYS[experiment_type]
                )

            # search for other configurations and replace them with current experiment configuration
            configuration_replaced = False
            for experiment_id in EvaluationConsts.EXPERIMENT_TYPE_KEYS.values():

                # build experiment configuration string
                experiment_configuration_string = \
                    EvaluationConsts.EXPERIMENT_CONFIGURATION_BASE_STRING.format(experiment_id=experiment_id)

                # replace other experiment configuration with current experiment configuration
                if configuration_file_content.find(experiment_configuration_string) > -1:
                    configuration_file_content = \
                        configuration_file_content.replace(
                            experiment_configuration_string,
                            current_configuration_string
                        )
                    configuration_replaced = True
                    break

            # override old configuration file with updated content
            if configuration_replaced:
                with open(EvaluationConsts.RUN_CONFIGURATION_FILE_PATH, 'wb') as configuration_file:
                    configuration_file.write(configuration_file_content)
            else:
                self.__logger.error('configuration not replaced. file content:\n***\n{file_content}\n***'.format(
                    file_content=configuration_file_content
                ))
                # skip to next experiment type
                continue

            # iterate user ids
            for user_id in user_ids:

                # checkout user code
                user_branch_name = \
                    ExperimentConsts.EXPERIMENT_USER_BRANCH_NAME_FORMAT.format(
                        user_name=user_id,
                        experiment_type=experiment_type
                    )
                self.__logger.log('evaluating user branch: {branch_name}'.format(branch_name=user_branch_name))

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
                    # skip to next user id
                    continue

                # duplicate evaluation code
                evaluation_with_user_code_folder_path = \
                    os.path.join(EvaluationConsts.EVALUATION_SOURCE_BASE_PATH, user_branch_name)

                # create combined code folder, if not exists
                if not os.path.exists(evaluation_with_user_code_folder_path):
                    os.makedirs(evaluation_with_user_code_folder_path)

                evaluation_with_user_code_folder_path = \
                    os.path.join(evaluation_with_user_code_folder_path, EvaluationConsts.SOURCE_FOLDER_NAME)

                # remove old files in case already exists
                if os.path.exists(evaluation_with_user_code_folder_path):
                    os.remove(evaluation_with_user_code_folder_path)

                try:
                    shutil.copytree(
                        EvaluationConsts.EVALUATION_SOURCE_PATH,
                        evaluation_with_user_code_folder_path
                    )
                except Exception, ex:
                    self.__logger.error(
                        'failed to copy directory.'
                        '\nsource path: {source_path}'
                        '\ndestination path: {dest_path}'
                        '\nerror: {ex}'.format(
                            source_path=EvaluationConsts.EVALUATION_SOURCE_PATH,
                            dest_path=evaluation_with_user_code_folder_path,
                            ex=ex
                        )
                    )
                    # skip to next id
                    continue

                # copy relevant experiment file
                all_copied = True
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

                    try:
                        shutil.copy2(source_path, destination_path)
                    except Exception, ex:
                        self.__logger.error(
                            'failed to copy file.'
                            '\nsource path: {source_path}'
                            '\ndestination path: {dest_path}'
                            '\nerror: {ex}'.format(
                                source_path=source_path,
                                dest_path=destination_path,
                                ex=ex
                            )
                        )
                        all_copied = False
                        break

                if all_copied:
                    # compile and run code
                    try:
                        self.__java_execution_manager.run_code(evaluation_with_user_code_folder_path)
                    except Exception, ex:
                        failed_branches[user_branch_name] = ex.message
                else:
                    self.__logger.error('some files not copied, see log for more info. skipping to next user id.')
                    # useless here, but for case that more code will be added in the loop after this point
                    continue

        self.__logger.log("failed branches:\n{failed_branches}".format(
            failed_branches='\n'.join(key + ': ' + failed_branches[key] for key in failed_branches.keys())
        ))

if __name__ == '__main__':
    experiment_evaluator = ExperimentEvaluator()
    experiment_evaluator.generate_results()
