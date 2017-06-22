
import os
import shutil
from multiprocessing.dummy import Pool as ThreadPool
from logger import Logger
from git_handler import GitHandler
from experiment_consts import ExperimentConsts
from evaluation_consts import EvaluationConsts
from java_execution_manager import JavaExecutionManager


class ExperimentEvaluator:

    def __init__(self):
        self.__logger = Logger()
        self.__git_handler = GitHandler(self.__logger)
        self.__failed_branches = dict()

    def __evaluate_code_folder(self, folder_path):
        self.__logger.log('evaluating folder: {folder_path}'.format(folder_path=folder_path))
        # compile and run code
        java_execution_manager = JavaExecutionManager(self.__logger)
        try:
            java_execution_manager.run_code(folder_path)
            self.__logger.log('folder evaluated successfully')
        except Exception, ex:
            self.__logger.log('folder evaluation failed')
            self.__failed_branches[folder_path] = ex.message

    def __duplicate_directory(self, source_path, destination_path):
        try:
            shutil.copytree(source_path, destination_path)

            return True

        except Exception, ex:
            self.__logger.error(
                'failed to copy directory.'
                '\nsource path: {source_path}'
                '\ndestination path: {destination_path}'
                '\nerror: {ex}'.format(source_path=source_path, destination_path=destination_path, ex=ex)
            )

            return False

    def __copy_file(self, source_path, destination_path):
        try:
            shutil.copy2(source_path, destination_path)

            return True

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

            return False

    def __copy_user_experiment_files(self, experiment_type, source_folder_path, destination_folder_path):

        for file_name_to_replace in EvaluationConsts.EXPERIMENT_REPLACE_FILES[experiment_type]:

            source_file_path = os.path.join(source_folder_path, file_name_to_replace)
            destination_file_path = os.path.join(destination_folder_path, file_name_to_replace)

            if not self.__copy_file(source_file_path, destination_file_path):
                return False

        return True

    def __change_configuration(self, source_folder_path, new_configuration_key):
        # modify evaluation code to run the specific experiment
        run_configuration_file_path = \
            EvaluationConsts.RUN_CONFIGURATION_FILE_TEMPLATE.format(
                folder_path=source_folder_path
            )
        with open(run_configuration_file_path, 'rb') as configuration_file:
            configuration_file_content = configuration_file.read()

        # build current experiment configuration string
        current_configuration_string = \
            EvaluationConsts.EXPERIMENT_CONFIGURATION_BASE_STRING.format(
                experiment_id=new_configuration_key
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
            with open(run_configuration_file_path, 'wb') as configuration_file:
                configuration_file.write(configuration_file_content)
        else:
            self.__logger.error('configuration not replaced. file content:\n***\n{file_content}\n***'.format(
                file_content=configuration_file_content
            ))

        return configuration_replaced

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
        self.__failed_branches = dict()

        # list of folder paths of branches that are ready for evaluation
        folder_paths_to_evaluate = list()

        # for each experiment type
        for experiment_type in EvaluationConsts.EXPERIMENT_TYPE_KEYS.keys():

            self.__logger.log('preparing experiment: {experiment_type}'.format(experiment_type=experiment_type))

            if not self.__change_configuration(
                    EvaluationConsts.EVALUATION_SOURCE_PATH, EvaluationConsts.EXPERIMENT_TYPE_KEYS[experiment_type]
            ):
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
                self.__logger.log('preparing user branch: {branch_name}'.format(branch_name=user_branch_name))

                try:
                    self.__git_handler.checkout_branch(
                        user_branch_name,
                        EvaluationConsts.USER_SOURCE_PATH
                    )
                except Exception, ex:
                    if ex.message.find(EvaluationConsts.BRANCH_NOT_FOUND_EXCEPTION_STRING) > -1:
                        self.__logger.error('branch not found: {branch_name}'.format(branch_name=user_branch_name))
                        self.__failed_branches[user_branch_name] = EvaluationConsts.BRANCH_NOT_FOUND_EXCEPTION_STRING
                    else:
                        self.__failed_branches[user_branch_name] = ex.message
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

                if not self.__duplicate_directory(
                        EvaluationConsts.EVALUATION_SOURCE_PATH, evaluation_with_user_code_folder_path
                ):
                    # remove remains, if any
                    user_branch_folder_path = \
                        os.path.join(EvaluationConsts.EVALUATION_SOURCE_BASE_PATH, user_branch_name)
                    if os.path.exists(user_branch_folder_path):
                        os.remove(user_branch_folder_path)

                    # skip to next id
                    continue

                # copy relevant experiment file
                if not self.__copy_user_experiment_files(
                        experiment_type, EvaluationConsts.USER_SOURCE_PATH, evaluation_with_user_code_folder_path
                ):
                    folder_paths_to_evaluate.append(evaluation_with_user_code_folder_path)
                else:
                    self.__logger.error('some files not copied, see log for more info. skipping to next user id.')

                    # remove remains, if any
                    user_branch_folder_path = \
                        os.path.join(EvaluationConsts.EVALUATION_SOURCE_BASE_PATH, user_branch_name)
                    if os.path.exists(user_branch_folder_path):
                        os.remove(user_branch_folder_path)

                    # useless here, but for case that more code will be added in the loop after this point
                    continue

        # create Similarities on Reward Shaping folders
        for user_id in user_ids:
            self.__logger.log('preparing user {user_id} similarities_on_reward_shaping folder'.format(user_id=user_id))

            # create source folder paths
            reward_shaping_experiment_type_name = 'reward_shaping'
            similarities_experiment_type_name = 'similarities'

            reward_shaping_branch_name = \
                ExperimentConsts.EXPERIMENT_USER_BRANCH_NAME_FORMAT.format(
                    user_name=user_id,
                    experiment_type=reward_shaping_experiment_type_name
                )

            similarities_branch_name = \
                ExperimentConsts.EXPERIMENT_USER_BRANCH_NAME_FORMAT.format(
                    user_name=user_id,
                    experiment_type=similarities_experiment_type_name
                )

            reward_shaping_folder_path = \
                os.path.join(EvaluationConsts.EVALUATION_SOURCE_BASE_PATH, reward_shaping_branch_name)

            similarities_folder_path = \
                os.path.join(EvaluationConsts.EVALUATION_SOURCE_BASE_PATH, similarities_branch_name)

            similarities_on_reward_shaping_folder_path = \
                os.path.join(
                    EvaluationConsts.EVALUATION_SOURCE_BASE_PATH,
                    ExperimentConsts.EXPERIMENT_USER_BRANCH_NAME_FORMAT.format(
                        user_name=user_id,
                        experiment_type=
                        '{similarities_experiment_type_name}_on_{reward_shaping_experiment_type_name}'.format(
                            similarities_experiment_type_name=similarities_experiment_type_name,
                            reward_shaping_experiment_type_name=reward_shaping_experiment_type_name
                        )
                    )
                )

            # verify both folders exists
            should_skip = False
            if not os.path.exists(reward_shaping_folder_path):
                self.__logger.error('reward_shaping folder is missing')
                should_skip = True
            if not os.path.exists(similarities_folder_path):
                self.__logger.error('similarities folder is missing')
                should_skip = True
            if should_skip:
                self.__logger.log('skipping to next user id')
                continue

            try:
                # duplicate reward shaping folder
                if not self.__duplicate_directory(reward_shaping_folder_path, similarities_on_reward_shaping_folder_path):
                    self.__logger.log('skipping to next user id')
                    raise Exception('failed duplicating reward shaping folder')

                # copy similarities file from similarities branch to duplicated folder
                if not self.__copy_user_experiment_files(
                        similarities_experiment_type_name,
                        similarities_folder_path,
                        similarities_on_reward_shaping_folder_path
                ):
                    raise Exception('failed coping similarities files')

                # modify configuration to run SimilaritiesOnRewardShaping
                if not self.__change_configuration(
                        similarities_on_reward_shaping_folder_path,
                        EvaluationConsts.SIMILARITIES_ON_REWARD_SHAPING_CONFIGURATION_KEY
                ):
                    raise Exception('failed changing configuration')

            except Exception, ex:
                self.__logger.error('failed crating folder. exception: {ex}'.format(ex=ex))
                if os.path.exists(similarities_on_reward_shaping_folder_path):
                    os.remove(similarities_on_reward_shaping_folder_path)
                self.__logger.log('skipping to next user id')
                continue

            # add folder path to folder_paths_to_evaluate
            folder_paths_to_evaluate.append(similarities_on_reward_shaping_folder_path)

        self.__logger.log('create thread pool: {num_of_threads} threads'.format(
            num_of_threads=EvaluationConsts.MAX_THREADS
        ))
        thread_pool = ThreadPool(EvaluationConsts.MAX_THREADS)

        self.__logger.log('begin threads run')
        thread_pool.map(self.__evaluate_code_folder, folder_paths_to_evaluate)
        thread_pool.close()

        self.__logger.log('wait for all threads to finish')
        thread_pool.join()
        self.__logger.log('all folders evaluated')

        self.__logger.log("failed branches:\n{failed_branches}".format(
            failed_branches='\n'.join(key + ': ' + self.__failed_branches[key] for key in self.__failed_branches.keys())
        ))

if __name__ == '__main__':
    experiment_evaluator = ExperimentEvaluator()
    experiment_evaluator.generate_results()