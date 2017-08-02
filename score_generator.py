
import os
import csv
from datetime import datetime
from logger import Logger
from evaluation_consts import EvaluationConsts
from score_generator_consts import ScoreGeneratorConsts


class ScoreGenerator:

    def __init__(self, p_logger):
        self.__logger = p_logger

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

        last_time = None
        in_eval = False

        train_total_seconds = 0
        eval_total_seconds = 0

        time_format = '[%d/%m/%Y %H:%M:%S]'

        # iterate log lines and parse lines
        for line in log_lines:

            if line.find('=== Experiment #') > 0:  # first line of train section
                time_part = line.split(' >> ')[0]
                curr_time = datetime.strptime(time_part, time_format)
                if last_time is not None:
                    eval_total_seconds += (curr_time - last_time).seconds
                    in_eval = False
                last_time = curr_time

            elif line.find('eval_ep') > 0 and not in_eval:  # line of evaluation section
                time_part = line.split(' >> ')[0]
                curr_time = datetime.strptime(time_part, time_format)
                train_total_seconds += (curr_time - last_time).seconds
                last_time = curr_time
                in_eval = True

            elif line.find('ex_eval_mean:') > 0:    # evaluation section mean result
                eval_results.append(float(line.split('ex_eval_mean:')[1]))

            elif line.find('Train episodes mean:') > 0:
                if train_episodes_means is not None:
                    raise Exception('duplicated train episodes list')

                line_part = line.split('Train episodes mean:')[1:][0]
                list_text = line_part.replace('[', '').replace(']', '')
                train_episodes_means = list_text.split(', ')
                train_episodes_means = map(float, train_episodes_means)

        return {
            'train': train_episodes_means,
            'train_time': train_total_seconds,
            'eval': sum(eval_results) / len(eval_results),
            'eval_time': eval_total_seconds
        }

    def generate_users_score(self):
        self.__logger.log("begin score generation")

        # read id list
        current_folder_path = os.path.dirname(__file__)
        user_ids = os.listdir(
            os.path.join(current_folder_path, '..', ScoreGeneratorConsts.RESULTS_FOLDER_NAME)
        )
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

                user_log_file_path = \
                    os.path.join(
                        current_folder_path, '..',
                        ScoreGeneratorConsts.RESULTS_FOLDER_NAME,
                        uid,
                        experiment_type + '.log'
                    )

                if not os.path.exists(user_log_file_path):
                    self.__logger.error(
                        'log file not found: {log_file_path}'.format(log_file_path=user_log_file_path)
                    )
                    raw_info_dict[uid][experiment_type] = {'train': [-1], 'train_time': 0, 'eval': -1, 'eval_time': 0}
                    continue

                # reading user run log file
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

        self.__logger.log('extracting learning curve info')
        split_keys = list()
        for uid in user_ids:

            for experiment_type in exp_list:
                user_train_results = raw_info_dict[uid][experiment_type]['train']
                raw_info_dict[uid][experiment_type]['train_mean'] = sum(user_train_results) / len(user_train_results)

                split_interval = len(user_train_results) / ScoreGeneratorConsts.GRAPH_MARKS_COUNT
                previous_index = 0
                for i in range(ScoreGeneratorConsts.GRAPH_MARKS_COUNT):
                    mean_record_index = (i+1)*split_interval
                    key_string = '{record_index}_mean'.format(
                        record_index=mean_record_index
                    )
                    if key_string not in split_keys:
                        split_keys.append(key_string)

                    raw_info_dict[uid][experiment_type][key_string] = \
                        sum(user_train_results[previous_index:mean_record_index-1]) / float(split_interval)
                    previous_index = mean_record_index-1

        # write results to csv
        self.__logger.log('writing info to csv file')
        csv_file_path = os.path.join(os.path.dirname(__file__), 'scores.csv')

        stats_keys = ['train_mean', 'train_time', 'eval', 'eval_time']
        stats_keys += split_keys

        with open(csv_file_path, 'wb') as csv_file:
            writer = csv.writer(csv_file)

            headers = ['user_id', 'experiment_type'] + stats_keys
            writer.writerow(headers)

        for uid in user_ids:
            for experiment_type in exp_list:
                fields = [uid, experiment_type]
                for key_name in stats_keys:
                    fields.append(raw_info_dict[uid][experiment_type][key_name])

                with open(csv_file_path, 'ab') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(fields)

        self.__logger.log('score calculation completed')


if __name__ == '__main__':
    logger = Logger()
    generator = ScoreGenerator(logger)
    generator.generate_users_score()
