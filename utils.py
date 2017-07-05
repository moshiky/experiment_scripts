
import os
import sys
import shutil
from evaluation_consts import EvaluationConsts
from java_execution_manager_consts import JavaExecutionManagerConsts


def prepare_for_experiment():
    # 1. delete
    pass


def recursive_log_clear(folder_path):
    folder_files = os.listdir(folder_path)

    if os.path.basename(folder_path) == 'logs':
        # find largest file
        max_size = -1
        max_size_file_name = None
        for file_name in folder_files:
            file_size = os.path.getsize(os.path.join(folder_path, file_name))
            if file_size > max_size:
                max_size = file_size
                max_size_file_name = file_name

        # delete all files except of the largest one
        for file_name in folder_files:
            if file_name != max_size_file_name:
                os.remove(os.path.join(folder_path, file_name))

    else:
        for file_name in folder_files:
            file_path = os.path.join(folder_path, file_name)
            if os.path.isdir(file_path) and file_name is not 'compiled_code':
                recursive_log_clear(file_path)


def delete_code_folders():
    for file_name in os.listdir(EvaluationConsts.EVALUATION_SOURCE_BASE_PATH):
        if file_name not in ['user', 'evaluation']:
            shutil.rmtree(os.path.join(EvaluationConsts.EVALUATION_SOURCE_BASE_PATH, file_name), ignore_errors=True)


if __name__ == '__main__':

    options = {
        '-c': 'clear redundant log files',
        '-dc': 'delete old code folders',
        '-dr': 'delete old result folders'
    }

    if len(sys.argv) != 2 or sys.argv[1] not in options.keys():
        print 'usage: {script_name} [{options}]'.format(
            script_name=os.path.basename(__file__), options=' | '.join(options.keys())
        )
        print '\n'.join(x[0]+'\t'+x[1] for x in zip(options.keys(), options.values()))

    else:
        if sys.argv[1] == '-c':
            # remove redundant log files
            recursive_log_clear(JavaExecutionManagerConsts.OUTPUT_DIR_PATH)

        elif sys.argv[1] == '-dc':
            delete_code_folders()

