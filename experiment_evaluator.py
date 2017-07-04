
import os
import sys
import shutil
import csv
from multiprocessing.dummy import Pool as ThreadPool
from logger import Logger
from git_handler import GitHandler
from experiment_consts import ExperimentConsts
from evaluation_consts import EvaluationConsts
from java_execution_manager import JavaExecutionManager
from java_execution_manager_consts import JavaExecutionManagerConsts


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

    def generate_results(self):

        self.__logger.log("begin result generation")

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
        full_experiments_list = list(EvaluationConsts.EXPERIMENT_TYPE_KEYS.keys()) + ['similarities_on_reward_shaping']
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
                if self.__copy_user_experiment_files(
                        experiment_type, EvaluationConsts.USER_SOURCE_PATH, evaluation_with_user_code_folder_path
                ):
                    if experiment_type in configuration_record:
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
        for configuration_record in run_configurations:

            if 'similarities_on_reward_shaping' not in configuration_record:
                # skip that experiment type for current user
                continue

            user_id = configuration_record[0]

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
                        EvaluationConsts.SIMILARITIES_ON_REWARD_SHAPING_COND,
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
                        EvaluationConsts.SIMILARITIES_ON_REWARD_SHAPING_COND,
                        EvaluationConsts.ORIGINAL_CONDITIONS.values(),
                        EvaluationConsts.SIMILARITIES_ON_REWARD_SHAPING_TEMPLATE
                ):
                    raise Exception('failed changing reward shaping file content for similarities on reward shaping')

            except Exception, ex:
                self.__logger.error('failed crating folder. exception: {ex}'.format(ex=ex))
                if os.path.exists(similarities_on_reward_shaping_folder_path):
                    os.remove(similarities_on_reward_shaping_folder_path)
                self.__logger.log('skipping to next user id')
                continue

            # add folder path to folder_paths_to_evaluate
            folder_paths_to_evaluate.append(similarities_on_reward_shaping_folder_path_with_folder_name)

        self.__logger.log('create thread pool: {num_of_threads} threads'.format(
            num_of_threads=EvaluationConsts.MAX_THREADS
        ))
        thread_pool = ThreadPool(EvaluationConsts.MAX_THREADS)

        self.__logger.log('########### begin threads run ###########')
        thread_pool.map(self.__evaluate_code_folder, folder_paths_to_evaluate)
        thread_pool.close()

        self.__logger.log('wait for all threads to finish')
        thread_pool.join()
        self.__logger.log('########### all folders evaluated ###########')

        self.__logger.log("failed branches:\n{failed_branches}".format(
            failed_branches='\n'.join(key + ': ' + self.__failed_branches[key] for key in self.__failed_branches.keys())
        ))

    def __parse_all_lines(self, log_lines):
        # create result dict
        result_dict = dict()

        # experiment round id
        experiment_round_id = -1
        last_ep_id = -1
        logging_stage = None

        # parse lines
        for line in log_lines:

            if line[0] == '[' and line[20] == ']':  # regular log line
                line_parts = line.split(' >> ')
                line_time = line_parts[0]
                line_content = line_parts[1]

                if line_content in [
                    'Logger created',
                    'Abstraction',
                    'Similarities',
                    'RewardShaping',
                    'SimilaritiesOnRewardShaping'
                ]:
                    # line not important and could be ignored
                    continue

                elif line_content.startswith('=== Experiment #'):
                    # line declares that new experiment round is started
                    experiment_round_id = (line_content.split('#')[1]).split(' ')[0]
                    result_dict[experiment_round_id] = \
                        {
                            'train': list(),
                            'eval': list()
                        }
                    last_ep_id = -1
                    logging_stage = 'train'

                elif line_content.startswith('ex') and line_content.find('ep') > 0 \
                        and line_content.find('mean:') > 0:
                    # train score log line

                    ex_id = line_content[2:].split('ep')[0]
                    if str(ex_id) != str(experiment_round_id):
                        raise Exception(
                            'wrong log file format. ex id mismatch: '
                            'declared {experiment_round_id} but line contains {ex_id}'.format(
                                experiment_round_id=experiment_round_id, ex_id=ex_id
                            )
                        )

                    ep_id = (line_content.split('ep')[1]).split(' ')[0]
                    if int(last_ep_id) + 100 != int(ep_id):
                        raise Exception(
                            'wrong log file format. eps not ordered correctly: '
                            'last is {last_ep_id} but current is {ep_id}'.format(
                                last_ep_id=last_ep_id, ep_id=ep_id
                            )
                        )
                    last_ep_id = ep_id

                    mean_score = line_content.split(' ')[2]
                    result_dict[logging_stage].append(mean_score)

                elif line_content.startswith('ex') and line_content.find('eval_ep') > 0:
                    # evaluation session score log line

                    ex_id = line_content[2:].split('eval')[0]
                    if str(ex_id) != str(experiment_round_id):
                        raise Exception(
                            'wrong log file format. eval ex id mismatch: '
                            'declared {experiment_round_id} but line contains {ex_id}'.format(
                                experiment_round_id=experiment_round_id, ex_id=ex_id
                            )
                        )

                    ep_id = (line_content.split('eval_ep')[1]).split(' ')[0].replace(':', '')
                    if str(ep_id) == '0':
                        logging_stage = 'eval'
                        last_ep_id = -1

                    if int(last_ep_id) + 1 != int(ep_id):
                        raise Exception(
                            'wrong log file format. eval eps not ordered correctly: '
                            'last is {last_ep_id} but current is {ep_id}'.format(
                                last_ep_id=last_ep_id, ep_id=ep_id
                            )
                        )
                    last_ep_id = ep_id

                    mean_score = line_content.split(' ')[1]
                    result_dict[ex_id][logging_stage].append(mean_score)

        return result_dict

    def __parse_selected_lines(self, log_lines):
        # create result lists
        eval_results = list()
        train_episodes_means = None

        # iterate log lines and parse lines
        for line in log_lines:

            if line.find('ex_eval_mean:') > 0:  # regular log line
                eval_results.append(float(line.split('ex_eval_mean:')[1]))

            elif line.find('Train episodes mean:') > 0:
                if train_episodes_means is not None:
                    raise Exception('duplicated train episodes list')

                line_part = line.split('Train episodes mean:')[1:][0]
                list_text = line_part.replace('[', '').replace(']', '')
                train_episodes_means = list_text.split(', ')
                train_episodes_means = map(float, train_episodes_means)

        return {'eval': sum(eval_results) / len(eval_results), 'train': train_episodes_means}

    def generate_users_score(self):
        self.__logger.log("begin score generation")

        # read id list
        with open(EvaluationConsts.EVALUATION_IDS_FILE_PATH, 'rb') as user_ids_file:
            user_ids = user_ids_file.read().replace('\r', '').split('\n')

        if user_ids[-1] == '':
            user_ids = user_ids[:-1]
        self.__logger.log("running {num_ids} ids:\n{ids}".format(num_ids=len(user_ids), ids='\n'.join(user_ids)))

        exp_list = list(EvaluationConsts.EXPERIMENT_TYPE_KEYS.keys())
        exp_list.append('similarities_on_reward_shaping')

        raw_info_dict = dict()
        for uid in user_ids:

            raw_info_dict[uid] = dict()

            for experiment_type in exp_list:

                raw_info_dict[uid][experiment_type] = dict()

                # build user results folder path
                self.__logger.log(
                    'calculating score of {uid} at {experiment_type}'.format(uid=uid, experiment_type=experiment_type)
                )

                user_log_dir_path = \
                    os.path.join(
                        JavaExecutionManagerConsts.OUTPUT_DIR_PATH,
                        uid,
                        experiment_type,
                        JavaExecutionManagerConsts.EXECUTION_LOGS_FOLDER_NAME
                    )
                logs_dir_files = os.listdir(user_log_dir_path)

                if len(logs_dir_files) != 1:
                    self.__logger.error(
                        'logs folder not contains what it should. files: {dir_files}'.format(dir_files=logs_dir_files)
                    )
                    continue

                # reading user run log file
                user_log_file_path = os.path.join(user_log_dir_path, logs_dir_files[0])
                with open(user_log_file_path, 'rb') as user_run_log_file:
                    log_file_content = user_run_log_file.read()

                # split log file into lines
                log_file_lines = log_file_content.split('\n')

                # remove header
                log_file_lines = log_file_lines[4:]

                try:
                    # raw_info_dict[uid][experiment_type] = self.__parse_all_lines(log_file_lines)
                    raw_info_dict[uid][experiment_type] = self.__parse_selected_lines(log_file_lines)

                except Exception, ex:
                    self.__logger.error('log file parsing failed. uid={uid} exp_type={exp_type} ex={ex}'.format(
                        uid=uid, exp_type=experiment_type, ex=ex
                    ))
                    return None

        # find global info
        lower_eval_res = dict()  # lower = better
        higher_eval_res = dict()  # higher = worth
        self.__logger.log('extracting eval info')
        for experiment_type in exp_list:

            tmp_lower = None
            tmp_higher = None

            for uid in user_ids:

                if tmp_lower is None:
                    tmp_lower = tmp_higher = raw_info_dict[uid][experiment_type]['eval']

                else:
                    user_eval_result = raw_info_dict[uid][experiment_type]['eval']

                    if tmp_lower > user_eval_result:
                        tmp_lower = user_eval_result

                    elif tmp_higher < user_eval_result:
                        tmp_higher = user_eval_result

            lower_eval_res[experiment_type] = tmp_lower
            higher_eval_res[experiment_type] = tmp_higher

        # extract info for grade
        learning_curve_factors = {
            'p1': 0.01, 'p10': 0.1, 'p50': 0.5, 'p90': 0.9, 'p99': 0.99
        }
        meta_info = dict()
        self.__logger.log('extracting learning curve info')
        for uid in user_ids:

            meta_info[uid] = dict()

            for experiment_type in exp_list:

                meta_info[uid][experiment_type] = dict()

                # 1. train session mean in compare to others: (higher-current) / (higher-lower)
                user_train_results = raw_info_dict[uid][experiment_type]['train']
                meta_info[uid][experiment_type]['train_mean'] = sum(user_train_results) / len(user_train_results)

                # 2. evaluation session mean in compare to others: (higher-current) / (higher-lower)
                user_eval_result = raw_info_dict[uid][experiment_type]['eval']
                meta_info[uid][experiment_type]['eval_mean'] = user_eval_result
                meta_info[uid][experiment_type]['score__eval_mean'] = \
                    (higher_eval_res[experiment_type] - user_eval_result)\
                    / (higher_eval_res[experiment_type] - lower_eval_res[experiment_type])

                # 3. find how much eps until convergence
                for p_type in learning_curve_factors:
                    meta_info[uid][experiment_type][p_type] = None

                total_eps = len(user_train_results)
                first_result = sum(user_train_results[:10]) / 10.0
                for i in range(total_eps):

                    for p_type in learning_curve_factors:
                        if meta_info[uid][experiment_type][p_type] is None \
                                and user_train_results[i] < first_result - (first_result - user_eval_result) * learning_curve_factors[p_type]:

                            meta_info[uid][experiment_type][p_type] = i

        # normalize results
        self.__logger.log('normalizing results')
        stats_keys = ['train_mean'] + learning_curve_factors.keys()
        stats = dict()
        for p_type in stats_keys:
            stats[p_type] = {'lower': None, 'higher': None}

        for experiment_type in exp_list:

            # find higher and lower scores
            for uid in user_ids:

                for p_type in stats:

                    if stats[p_type]['lower'] is None \
                            or meta_info[uid][experiment_type][p_type] < stats[p_type]['lower']:
                        stats[p_type]['lower'] = meta_info[uid][experiment_type][p_type]

                    if stats[p_type]['higher'] is None \
                            or meta_info[uid][experiment_type][p_type] > stats[p_type]['higher']:
                        stats[p_type]['higher'] = meta_info[uid][experiment_type][p_type]

            # normalize results accordingly
            for uid in user_ids:

                for p_type in stats:

                    meta_info[uid][experiment_type]['score__' + p_type] = \
                        (stats[p_type]['higher'] - meta_info[uid][experiment_type][p_type]) \
                        / (stats[p_type]['higher'] - stats[p_type]['lower'])

        # write results to csv
        self.__logger.log('writing info to csv file')
        csv_file_path = os.path.join(os.path.dirname(__file__), 'scores.csv')

        stats_keys = ['eval_mean'] + stats_keys
        stats_keys += ['score__' + key_name for key_name in stats_keys]

        with open(csv_file_path, 'wb') as csv_file:
            writer = csv.writer(csv_file)

            headers = ['user_id', 'experiment_type'] + stats_keys
            writer.writerow(headers)

        for uid in user_ids:
            for experiment_type in exp_list:
                fields = [uid, experiment_type]
                for key_name in stats_keys:
                    fields.append(meta_info[uid][experiment_type][key_name])

                with open(csv_file_path, 'ab') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(fields)

        self.__logger.log('score calculation completed')

if __name__ == '__main__':
    experiment_evaluator = ExperimentEvaluator()

    if sys.argv[1] == '-r':
        experiment_evaluator.generate_results()
    elif sys.argv[1] == '-s':
        experiment_evaluator.generate_users_score()
