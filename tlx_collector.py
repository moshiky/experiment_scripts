
# the objective is to extract the info from the tlx output and organize it in a csv file

# first step- load output from file and parse it
# second step- add parsed info into (already exist) csv file
# csv structure:
#       date&time, mental demand, physical demand, temporal demand, performance, effort, frustration, overall

import os
import csv
import time

INPUT_FILE_NAME = 'tlx_output.txt'
CSV_FILE_PATH = 'results.csv'


class CsvKeys:
    DATE_TIME = 'date_time'
    MENTAL_DEMAND = 'mental_demand'
    PHYSICAL_DEMAND = 'physical_demand'
    TEMPORAL_DEMAND = 'temporal_demand'
    PERFORMANCE = 'performance'
    EFFORT = 'effort'
    FRUSTRATION = 'frustration'
    OVERALL = 'overall'


def parse_tlx_content(raw_content):
    """
    Parse tlx content into dictionary
    :param raw_content: raw tlx output
    :return: dictionary
    """
    # split to lines
    raw_content = raw_content.replace('\r', '')
    raw_content_lines = raw_content.split('\n')

    # build output dict
    parsed_content = dict()

    # fill values
    parsed_content[CsvKeys.MENTAL_DEMAND] = raw_content_lines[1].split('\t')[1]
    parsed_content[CsvKeys.PHYSICAL_DEMAND] = raw_content_lines[2].split('\t')[1]
    parsed_content[CsvKeys.TEMPORAL_DEMAND] = raw_content_lines[3].split('\t')[1]
    parsed_content[CsvKeys.PERFORMANCE] = raw_content_lines[4].split('\t')[1]
    parsed_content[CsvKeys.EFFORT] = raw_content_lines[5].split('\t')[1]
    parsed_content[CsvKeys.FRUSTRATION] = raw_content_lines[6].split('\t')[1]
    parsed_content[CsvKeys.OVERALL] = raw_content_lines[8].split(' ')[2]

    # return dict
    return parsed_content


def get_current_date_and_time():
    return time.strftime('%Y_%m_%d__%H_%M_%S')


def add_csv_row(csv_values_dict):
    fields = [
        csv_values_dict[CsvKeys.DATE_TIME],
        csv_values_dict[CsvKeys.MENTAL_DEMAND],
        csv_values_dict[CsvKeys.PHYSICAL_DEMAND],
        csv_values_dict[CsvKeys.TEMPORAL_DEMAND],
        csv_values_dict[CsvKeys.PERFORMANCE],
        csv_values_dict[CsvKeys.EFFORT],
        csv_values_dict[CsvKeys.FRUSTRATION],
        csv_values_dict[CsvKeys.OVERALL]
    ]

    csv_file_path = os.path.join(os.path.dirname(__file__), CSV_FILE_PATH)
    if not os.path.exists(csv_file_path):
        headers = [
            CsvKeys.DATE_TIME,
            CsvKeys.MENTAL_DEMAND,
            CsvKeys.PHYSICAL_DEMAND,
            CsvKeys.TEMPORAL_DEMAND,
            CsvKeys.PERFORMANCE,
            CsvKeys.EFFORT,
            CsvKeys.FRUSTRATION,
            CsvKeys.OVERALL
        ]
        with open(csv_file_path, 'wb') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(headers)

    with open(csv_file_path, 'ab') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(fields)


def main():
    # load file content
    input_file_path = os.path.join(os.path.dirname(__file__), INPUT_FILE_NAME)
    with open(input_file_path, 'rb') as input_file:
        tlx_raw_content = input_file.read()

    # parse content
    tlx_parsed_content = parse_tlx_content(tlx_raw_content)

    # add content to csv
    tlx_parsed_content[CsvKeys.DATE_TIME] = get_current_date_and_time()
    add_csv_row(tlx_parsed_content)


if __name__ == '__main__':
    main()
