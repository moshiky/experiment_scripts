
import os
import shutil

# create new folder named 'results'
os.mkdir('results')

# for each folder
dir_folders = os.listdir('.')
for folder_name in dir_folders:

    if folder_name == 'results' or not os.path.isdir(folder_name):
        continue

    # create new folder under results
    new_folder_path = os.path.join('results', folder_name)
    os.mkdir(new_folder_path)

    experiment_folders = os.listdir(folder_name)
    for exp_folder in experiment_folders:

        exp_folder_path = os.path.join(folder_name, exp_folder)

        # find the log files
        logs_folder_path = os.path.join(exp_folder_path, 'logs')
        largest_log_file_size = 0
        largest_log_file_path = None
        log_files = os.listdir(logs_folder_path)
        for log_file_name in log_files:
            log_file_path = os.path.join(logs_folder_path, log_file_name)
            log_file_size = os.path.getsize(log_file_path)
            if log_file_size > largest_log_file_size:
                largest_log_file_size = log_file_size
                largest_log_file_path = log_file_path

        if largest_log_file_path is None:
            print folder_name, exp_folder, 'no logs'

        else:
            # copy just the larges file
            new_file_name = os.path.join(new_folder_path, exp_folder + '.log')
            shutil.copy2(largest_log_file_path, new_file_name)
