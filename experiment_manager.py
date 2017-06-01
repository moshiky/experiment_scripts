
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
        selected_experiment_type_key = '-'
        while selected_experiment_type_key not in ExperimentConsts.EXPERIMENT_TYPE_KEYS.keys():
            logger.log('Available experiments:')
            for type_key in ExperimentConsts.EXPERIMENT_TYPE_KEYS.keys():
                logger.log('{type_key} - {type_name}'.format(
                    type_key=type_key,
                    type_name=ExperimentConsts.EXPERIMENT_TYPE_STRINGS[
                        ExperimentConsts.EXPERIMENT_TYPE_KEYS[type_key]
                    ])
                )
            selected_experiment_type_key = \
                raw_input('Please select experiment type: '.format(
                    number_of_types=len(ExperimentConsts.EXPERIMENT_TYPE_KEYS)-1)
                )

        # create experiment handler
        experiment_type = ExperimentConsts.EXPERIMENT_TYPE_KEYS[selected_experiment_type_key]
        experiment_handler = \
            ExperimentHandler(
                logger,
                ExperimentConsts.WORKING_DIRECTORY_PATH,
                experiment_type,
                user_name
            )

        # initiate participant branch
        experiment_handler.initiate_for_participant()
        logger.log('You can begin working on your code now, Good Luck!')

        # show basic gui - select action
        selected_action = '-'
        while selected_action not in ['E', 'F']:
            logger.print_msg('Available actions:')
            logger.print_msg('E - exit without saving')
            logger.print_msg('F - finish experiment')
            selected_action = raw_input('Enter your selection: ')

            logger.log('option selected: {selected_action}'.format(selected_action=selected_action), should_print=False)

        # apply selected action
        if selected_action == 'F':
            # store logs and graphs on local hard drive
            ExperimentManager.__store_logs_and_graphs(user_name, experiment_type)

            # commit changes
            experiment_handler.commit_changes("* code completed")
            logger.log('Changes committed successfully!')

            # push just current branch
            experiment_handler.push_branch()
            logger.log('Pushed successfully!')

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
