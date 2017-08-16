
import os
import sys
import shutil
from multiprocessing.dummy import Pool as ThreadPool
from threading import Lock
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
        self.__compile_lock = Lock()

    def __evaluate_code_folder(self, folder_path):
        self.__logger.log('evaluating folder: {folder_path}'.format(folder_path=folder_path))

        # compile and run code
        java_execution_manager = JavaExecutionManager(self.__logger)
        try:
            java_execution_manager.run_code(folder_path, self.__compile_lock)
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
            self.__logger.log('file copied successfully: {source_path} => {destination_path}'.format(
                source_path=source_path, destination_path=destination_path
            ), should_print=False)

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

        return True

    def __copy_user_experiment_files(self, experiment_type, source_folder_path, destination_folder_path):

        for file_name_to_replace in EvaluationConsts.EXPERIMENT_REPLACE_FILES[experiment_type]:

            source_file_path = os.path.join(source_folder_path, file_name_to_replace)
            destination_file_path = os.path.join(destination_folder_path, file_name_to_replace)

            if not self.__copy_file(source_file_path, destination_file_path):
                return False

        return True

    '''
    file_path = EvaluationConsts.RUN_CONFIGURATION_FILE_TEMPLATE.format(folder_path=source_folder_path)
    new_content = experiment_id
    possible_value_list = EvaluationConsts.EXPERIMENT_TYPE_KEYS.values()
    value_template = EvaluationConsts.EXPERIMENT_CONFIGURATION_BASE_STRING
    '''

    def __custom_file_edit(self, file_path, new_content_value, possible_value_list, value_template):
        # read original file content
        with open(file_path, 'rb') as destination_file:
            file_content = destination_file.read()

        # build required value string
        required_value_string = value_template.format(new_content_value)

        # search for other possible values and replace them with required value
        content_replaced = False
        for file_value in possible_value_list:

            # build possible value string
            value_string = value_template.format(file_value)

            # replace other possible values with required one
            if file_content.find(value_string) > -1:
                file_content = \
                    file_content.replace(
                        value_string,
                        required_value_string
                    )
                content_replaced = True
                break

        # override old content with updated content
        if content_replaced:
            with open(file_path, 'wb') as destination_file:
                destination_file.write(file_content)
        else:
            self.__logger.error('content not replaced. file content:\n***\n{file_content}\n***'.format(
                file_content=file_content
            ))

        return content_replaced

    def generate_results(self, cmd_param=None):

        self.__logger.log("begin result generation")

        path_list_to_evaluate = None
        if cmd_param is None:
            self.__logger.log('creating code folders to evaluate from ids.txt file')

            # read id list
            with open(EvaluationConsts.ID_FILE_PATH, 'rb') as configuration_row:
                configuration_lines = configuration_row.read().replace('\r', '').split('\n')

            if configuration_lines[-1] == '':
                configuration_lines = configuration_lines[:-1]
            self.__logger.log(
                "running {configuration_count} ids:\n{configurations}".format(
                    configuration_count=len(configuration_lines), configurations='\n'.join(configuration_lines)
                )
            )

            run_configurations = map(lambda x: x.split(' '), configuration_lines)
            full_experiments_list = \
                list(EvaluationConsts.EXPERIMENT_TYPE_KEYS.keys()) + ['similarities_on_reward_shaping']
            run_configurations = map(lambda x: x if len(x) > 1 else x + full_experiments_list, run_configurations)

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

                if not self.__custom_file_edit(
                        EvaluationConsts.RUN_CONFIGURATION_FILE_TEMPLATE.format(
                            folder_path=EvaluationConsts.EVALUATION_SOURCE_PATH),
                        EvaluationConsts.EXPERIMENT_TYPE_KEYS[experiment_type],
                        EvaluationConsts.EXPERIMENT_TYPE_KEYS.values(),
                        EvaluationConsts.EXPERIMENT_CONFIGURATION_BASE_STRING
                ):
                    # skip to next experiment type
                    continue

                # iterate user ids
                for configuration_record in run_configurations:

                    user_id = configuration_record[0]

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
                            self.__failed_branches[user_branch_name] = \
                                EvaluationConsts.BRANCH_NOT_FOUND_EXCEPTION_STRING
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
                        shutil.rmtree(evaluation_with_user_code_folder_path)

                    if not self.__duplicate_directory(
                            EvaluationConsts.EVALUATION_SOURCE_PATH, evaluation_with_user_code_folder_path
                    ):
                        # remove remains, if any
                        user_branch_folder_path = \
                            os.path.join(EvaluationConsts.EVALUATION_SOURCE_BASE_PATH, user_branch_name)
                        if os.path.exists(user_branch_folder_path):
                            shutil.rmtree(user_branch_folder_path)

                        # skip to next id
                        continue

                    # copy relevant experiment file
                    if self.__copy_user_experiment_files(
                            experiment_type, EvaluationConsts.USER_SOURCE_PATH, evaluation_with_user_code_folder_path
                    ):
                        if experiment_type == 'abstraction':
                            # apply some corrections to abstraction user file
                            try:
                                for correction_record in EvaluationConsts.ABSTRACTION_FILE_CORRECTIONS:
                                    if not self.__custom_file_edit(
                                            os.path.join(evaluation_with_user_code_folder_path,
                                                         EvaluationConsts.EXPERIMENT_REPLACE_FILES[experiment_type][0]),
                                            correction_record[1], [correction_record[0]], '{0}'
                                    ):
                                        raise Exception(
                                            'failed changing abstraction file. pair: {0}'.format(correction_record)
                                        )
                            except Exception, ex:
                                self.__logger.error("abstraction corrections failed. ex: {ex}".format(ex=ex))
                                continue

                        if experiment_type in configuration_record:
                            folder_paths_to_evaluate.append(evaluation_with_user_code_folder_path)
                    else:
                        self.__logger.error('some files not copied, see log for more info. skipping to next user id.')

                        # remove remains, if any
                        user_branch_folder_path = \
                            os.path.join(EvaluationConsts.EVALUATION_SOURCE_BASE_PATH, user_branch_name)
                        if os.path.exists(user_branch_folder_path):
                            shutil.rmtree(user_branch_folder_path)

                        # useless here, but for case that more code will be added in the loop after this point
                        continue

            # create Similarities on Reward Shaping folders
            for configuration_record in run_configurations:

                if 'similarities_on_reward_shaping' not in configuration_record:
                    # skip that experiment type for current user
                    continue

                user_id = configuration_record[0]

                self.__logger.log(
                    'preparing user {user_id} similarities_on_reward_shaping folder'.format(user_id=user_id)
                )

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
                    os.path.join(
                        EvaluationConsts.EVALUATION_SOURCE_BASE_PATH,
                        similarities_branch_name,
                        EvaluationConsts.SOURCE_FOLDER_NAME
                    )

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

                    # append source folder name
                    similarities_on_reward_shaping_folder_path_with_folder_name = \
                        os.path.join(similarities_on_reward_shaping_folder_path, EvaluationConsts.SOURCE_FOLDER_NAME)

                    # copy similarities file from similarities branch to duplicated folder
                    if not self.__copy_user_experiment_files(
                            similarities_experiment_type_name,
                            similarities_folder_path,
                            similarities_on_reward_shaping_folder_path_with_folder_name
                    ):
                        raise Exception('failed coping similarities files')

                    # modify configuration to run SimilaritiesOnRewardShaping
                    if not self.__custom_file_edit(
                            EvaluationConsts.RUN_CONFIGURATION_FILE_TEMPLATE.format(
                                folder_path=similarities_on_reward_shaping_folder_path_with_folder_name),
                            EvaluationConsts.SIMILARITIES_ON_REWARD_SHAPING_CONFIGURATION_KEY,
                            EvaluationConsts.EXPERIMENT_TYPE_KEYS.values(),
                            EvaluationConsts.EXPERIMENT_CONFIGURATION_BASE_STRING
                    ):
                        raise Exception('failed changing configuration for similarities on reward shaping')

                    # modify similarities file to run code when in combined mode
                    if not self.__custom_file_edit(
                            os.path.join(
                                similarities_on_reward_shaping_folder_path_with_folder_name,
                                EvaluationConsts.EXPERIMENT_REPLACE_FILES['similarities'][0]
                            ),
                            EvaluationConsts.SIMILARITIES_ON_REWARD_SHAPING_COND['similarities'],
                            EvaluationConsts.ORIGINAL_CONDITIONS.values(),
                            EvaluationConsts.SIMILARITIES_ON_REWARD_SHAPING_TEMPLATE
                    ):
                        raise Exception('failed changing similarities file content for similarities on reward shaping')

                    # modify reward shaping file to run code when in combined mode
                    if not self.__custom_file_edit(
                            os.path.join(
                                similarities_on_reward_shaping_folder_path_with_folder_name,
                                EvaluationConsts.EXPERIMENT_REPLACE_FILES['reward_shaping'][0]
                            ),
                            EvaluationConsts.SIMILARITIES_ON_REWARD_SHAPING_COND['reward_shaping'],
                            EvaluationConsts.ORIGINAL_CONDITIONS.values(),
                            EvaluationConsts.SIMILARITIES_ON_REWARD_SHAPING_TEMPLATE
                    ):
                        raise Exception('failed changing reward shaping file content for similarities on reward shaping')

                except Exception, ex:
                    self.__logger.error('failed crating folder. exception: {ex}'.format(ex=ex))
                    if os.path.exists(similarities_on_reward_shaping_folder_path):
                        shutil.rmtree(similarities_on_reward_shaping_folder_path)
                    self.__logger.log('skipping to next user id')
                    continue

                # add folder path to folder_paths_to_evaluate
                folder_paths_to_evaluate.append(similarities_on_reward_shaping_folder_path_with_folder_name)

            # set path list
            path_list_to_evaluate = folder_paths_to_evaluate
        
        else:
            self.__logger.log('reading existing folder list from file')
            
            # read path list from file
            with open(cmd_param, 'rb') as path_list_file:
                path_list_to_evaluate = path_list_file.read().replace('\r', '').split('\n')
                
        self.__logger.log(
            'evaluating existing folders:\n{path_list}'.format(path_list='\n'.join(path_list_to_evaluate))
        )

        self.__logger.log('create thread pool: {num_of_threads} threads'.format(
            num_of_threads=EvaluationConsts.MAX_THREADS
        ))
        thread_pool = ThreadPool(EvaluationConsts.MAX_THREADS)

        self.__logger.log('########### begin threads run ###########')
        self.__logger.log('wait for all threads to finish')
        thread_pool.map(self.__evaluate_code_folder, path_list_to_evaluate)
        thread_pool.close()
        thread_pool.join()
        self.__logger.log('########### all folders evaluated ###########')

        self.__logger.log("failed branches:\n{failed_branches}".format(
            failed_branches='\n'.join(key + ': ' + self.__failed_branches[key] for key in self.__failed_branches.keys())
        ))


if __name__ == '__main__':
    experiment_evaluator = ExperimentEvaluator()
    if len(sys.argv) == 3 and sys.argv[1] == '-ef':
        experiment_evaluator.generate_results(sys.argv[2])
    elif len(sys.argv) > 2 and sys.argv[1] == '-e':
        experiment_evaluator.generate_results(sys.argv[2:])
    elif len(sys.argv) == 1:
        experiment_evaluator.generate_results()
    else:
        print "usage: <script_name> " \
              "[-e <list of paths to execute> " \
              "| -ef <path of a file that contains list of folder paths to evaluate>]"
