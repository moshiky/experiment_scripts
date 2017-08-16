
import os
import sys
import csv
from datetime import datetime
from logger import Logger
from evaluation_consts import EvaluationConsts


class ScoreGenerator:

    def __init__(self, p_logger):
        self.__logger = p_logger

    def __parse_log_file_lines(self, log_lines):
        # initiate variables and counters
        evaluation_mean_results_sum = list()
        evaluation_total_time = 0
        evaluation_start_time = None
        evaluation_section_id = 0
        train_end_time = None
        train_start_time = None
        epoch_id = 0

        # parse log lines
        time_format = '[%d/%m/%Y %H:%M:%S]'
        for line in log_lines:

            if line.find('=== Experiment #') > 0:  # first line of train epoch
                log_line_time = datetime.strptime(line.split(' >> ')[0], time_format)
                if line.find(' #0 ') > 0:     # train start
                    train_start_time = log_line_time
                epoch_id += 1
                evaluation_section_id = 0

            elif line.find('-- Evaluation --') > 0:
                evaluation_start_time = datetime.strptime(line.split(' >> ')[0], time_format)

            elif line.find('evaluation results:') > 0:
                evaluation_end_time = datetime.strptime(line.split(' >> ')[0], time_format)
                evaluation_total_time += (evaluation_end_time - evaluation_start_time).seconds + 0.5

            elif line.find('mean result:') > 0:
                evaluation_mean_result = float(line.split('mean result: ')[1])
                if epoch_id == 0 or len(evaluation_mean_results_sum) == evaluation_section_id:
                    evaluation_mean_results_sum.append((evaluation_mean_result, 1))
                else:
                    evaluation_mean_results_sum[evaluation_section_id] = \
                        (
                            evaluation_mean_results_sum[evaluation_section_id][0] + evaluation_mean_result,
                            evaluation_mean_results_sum[evaluation_section_id][1] + 1
                        )
                evaluation_section_id += 1

            elif line.find('total time:') > 0:
                train_end_time = datetime.strptime(line.split(' >> ')[0], time_format)

        if train_end_time is None:
            raise Exception('log file not complete')
        else:
            # calculate train duration
            train_duration = (train_end_time - train_start_time).seconds - evaluation_total_time

        # calculate mean evaluation results
        evaluation_mean_results = [float(x[0])/x[1] for x in evaluation_mean_results_sum]

        # return results
        return {
            'evaluation_mean_results': evaluation_mean_results,
            'evaluation_mean_duration': float(evaluation_total_time) / epoch_id,
            'train_mean_duration': float(train_duration) / epoch_id
        }

    def generate_users_score(self, results_folder_path):
        self.__logger.log("begin score generation")

        # read id list
        user_ids = os.listdir(results_folder_path)
        self.__logger.log("running {num_ids} ids:\n{ids}".format(num_ids=len(user_ids), ids='\n'.join(user_ids)))

        # build the complete experiment list
        exp_list = list(EvaluationConsts.EXPERIMENT_TYPE_KEYS.keys())
        exp_list.append('similarities_on_reward_shaping')

        max_evaluation_sections_number = 0
        raw_info_dict = dict()
        error_row = {'evaluation_mean_results': [-1], 'evaluation_mean_duration': -1, 'train_mean_duration': -1}
        for uid in user_ids:

            raw_info_dict[uid] = dict()

            for experiment_type in exp_list:

                raw_info_dict[uid][experiment_type] = dict()

                # build user results folder path
                self.__logger.log(
                    'calculating score of {uid} at {experiment_type}'.format(uid=uid, experiment_type=experiment_type)
                )

                user_log_file_path = os.path.join(results_folder_path, uid, experiment_type + '.log')

                if not os.path.exists(user_log_file_path):
                    self.__logger.error(
                        'log file not found: {log_file_path}'.format(log_file_path=user_log_file_path)
                    )
                    raw_info_dict[uid][experiment_type] = error_row
                    continue

                # reading user run log file
                with open(user_log_file_path, 'rb') as user_run_log_file:
                    log_file_content = user_run_log_file.read()

                # split log file into lines
                log_file_lines = log_file_content.split('\n')

                # remove header
                log_file_lines = log_file_lines[4:]

                # parse lines
                try:
                    raw_info_dict[uid][experiment_type] = self.__parse_log_file_lines(log_file_lines)

                except Exception, ex:
                    self.__logger.error('log file parsing failed. uid={uid} exp_type={exp_type} ex={ex}'.format(
                        uid=uid, exp_type=experiment_type, ex=ex
                    ))
                    raw_info_dict[uid][experiment_type] = error_row
                    continue

                # compare evaluation results list to max length
                if len(raw_info_dict[uid][experiment_type]['evaluation_mean_results']) > max_evaluation_sections_number:
                    max_evaluation_sections_number = len(raw_info_dict[uid][experiment_type]['evaluation_mean_results'])

        self.__logger.log('preparing for csv')
        for uid in user_ids:
            for experiment_type in exp_list:
                evaluation_results = raw_info_dict[uid][experiment_type]['evaluation_mean_results']
                if len(evaluation_results) < max_evaluation_sections_number:
                    evaluation_results += [''] * (max_evaluation_sections_number - len(evaluation_results))

        evaluation_sections_marks = ['eval_' + str(eval_id) for eval_id in range(max_evaluation_sections_number)]

        # write results to csv
        self.__logger.log('writing info to csv file')
        csv_file_path = os.path.join(results_folder_path, 'scores.csv')

        stats_keys = ['train_mean_duration', 'evaluation_mean_duration']

        with open(csv_file_path, 'wb') as csv_file:
            writer = csv.writer(csv_file)

            headers = ['user_id', 'experiment_type'] + stats_keys + evaluation_sections_marks
            writer.writerow(headers)

        for uid in user_ids:
            for experiment_type in exp_list:
                fields = [uid, experiment_type]
                for key_name in stats_keys:
                    fields.append(raw_info_dict[uid][experiment_type][key_name])
                for eval_id in range(max_evaluation_sections_number):
                    fields.append(raw_info_dict[uid][experiment_type]['evaluation_mean_results'][eval_id])

                with open(csv_file_path, 'ab') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(fields)

        self.__logger.log('score calculation completed')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "usage: score_generator.py <results folder path>"
    else:
        logger = Logger()
        generator = ScoreGenerator(logger)
        generator.generate_users_score(sys.argv[1])
