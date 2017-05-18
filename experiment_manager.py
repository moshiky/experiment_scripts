
import os
import shutil
from experiment_consts import ExperimentConsts
from experiment_handler import ExperimentHandler
from logger import Logger
import tlx_collector


class ExperimentManager:

    @staticmethod
    def start():
        # local vars
        logger = Logger()

        # read user name
        user_name = raw_input("Enter your id: ")

        # start interactive mode
        logger.log('Hello {user_name}! lets begin :)'.format(user_name=user_name))

        # get experiment type
        selected_experiment_type_index = -1
        while selected_experiment_type_index < 0:
            logger.log('Available experiments:')
            for type_index, type_name in enumerate(ExperimentConsts.EXPERIMENT_TYPE_STRINGS.values()):
                logger.log('{type_index} - {type_name}'.format(type_index=type_index, type_name=type_name))
            selected_experiment_type_index = \
                raw_input('Please select experiment type: [0-{number_of_types}] '.format(
                    number_of_types=len(ExperimentConsts.EXPERIMENT_TYPE_STRINGS)-1)
                )

            # validate selection
            try:
                selected_experiment_type_index = int(selected_experiment_type_index)
                if selected_experiment_type_index not in range(len(ExperimentConsts.EXPERIMENT_TYPE_STRINGS)):
                    selected_experiment_type_index = -1
            except:
                selected_experiment_type_index = -1

        # create experiment handler
        experiment_type = ExperimentConsts.EXPERIMENT_TYPE_STRINGS.keys()[selected_experiment_type_index]
        experiment_handler = \
            ExperimentHandler(
                logger,
                ExperimentConsts.WORKING_DIRECTORY_PATH,
                experiment_type,
                user_name
            )

        # show basic gui - select action:
        # 0 - initiate experiment for user
        # 1 - save changes
        # 2 - exit
        exit_selected = False
        while not exit_selected:
            logger.print_msg('Available actions:')
            logger.print_msg('0 - end experiment')
            logger.print_msg('1 - initiate participant branch')
            logger.print_msg('2 - commit changes')
            logger.print_msg('3 - push branch(es)')
            selected_action = raw_input('Enter your selection: [0-3] ')

            logger.log('option selected: {selected_action}'.format(selected_action=selected_action), should_print=False)
            try:
                selected_action = int(selected_action)
                if selected_action not in range(4):
                    continue
            except:
                continue

            # apply selected action
            if selected_action == 0:
                # exit experiment manager
                exit_selected = True

            elif selected_action == 1:
                # initiate participant branch
                experiment_handler.initiate_for_participant()
                logger.log('You can begin working on your code now, Good Luck!')

            elif selected_action == 2:
                # store logs and graphs on local hard drive
                ExperimentManager.__store_logs_and_graphs(user_name, experiment_type)

                # commit changes
                experiment_handler.commit_changes("* code completed")
                logger.log('Changes committed successfully!')

            elif selected_action == 3:
                # push just current branch
                experiment_handler.push_branch()
                logger.log('Pushed successfully!')

        # verify that all changes has been committed before exit
        answer = ''
        while answer not in ['y', 'n']:
            answer = raw_input('Have you committed all of your changes? [y/n] ')
        if 'n' == answer:
            experiment_handler.commit_changes("* code completed")

        # collect TLX results
        ExperimentManager.__collect_tlx_results(logger, experiment_handler, user_name, experiment_type)

        # exit manager and print farewell greetings
        logger.log('Thank you {user_name}! this experiment phase is over.'.format(user_name=user_name))
        logger.print_msg('We greatly appreciate your contribution.')
        logger.print_msg('Look! You have made our rabbit happy!')
        logger.print_msg('   (\_/)   ')
        logger.print_msg('   (^.^)   ')
        logger.print_msg('  \(> <)/  ')

    @staticmethod
    def __store_logs_and_graphs(user_id, experiment_type):
        # create remote storage
        remote_storage_path = \
            ExperimentConsts.REMOTE_USER_STORAGE_PATH.format(user_id=user_id, experiment_type=experiment_type)
        os.makedirs(remote_storage_path)
        # move folders to local location
        shutil.move(ExperimentConsts.EXPERIMENT_LOGS_DIR_PATH, remote_storage_path)
        shutil.move(ExperimentConsts.EXPERIMENT_GRAPHS_DIR_PATH, remote_storage_path)
        # create new empty folders instead of the original
        os.makedirs(ExperimentConsts.EXPERIMENT_LOGS_DIR_PATH)
        os.makedirs(ExperimentConsts.EXPERIMENT_GRAPHS_DIR_PATH)

    @staticmethod
    def __collect_tlx_results(logger, experiment_handler, user_name, experiment_type):
        # pull latest version
        logger.log('pulling changes')
        experiment_handler.pull_branch(
            branch_name=ExperimentConsts.SCRIPTS_BRANCH_NAME,
            working_directory=ExperimentConsts.SCRIPTS_WORKING_DIRECTORY
        )

        # collect tlx results
        logger.log('collecting tlx results')
        tlx_collector.collect(user_name, experiment_type)

        # commit changes
        experiment_handler.commit_changes(
            comment="* add tlx results",
            working_directory=ExperimentConsts.SCRIPTS_WORKING_DIRECTORY
        )

        # push changes
        logger.log('pushing changes')
        experiment_handler.push_branch(
            branch_name=ExperimentConsts.SCRIPTS_BRANCH_NAME,
            working_directory=ExperimentConsts.SCRIPTS_WORKING_DIRECTORY
        )

if __name__ == '__main__':
    ExperimentManager.start()
