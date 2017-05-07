
import subprocess
from git_commands import GitCommands
from experiment_consts import ExperimentConsts
from logger import Logger


def run_git_command(cmd, logger):
    logger.log('running command: {cmd}'.format(cmd=cmd), should_print=False)
    try:
        # execute command
        output = \
            subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=ExperimentConsts.WORKING_DIRECTORY_PATH
            )

        # log command output
        logger.log('command output:', should_print=False)
        has_errors = False
        for line in output.stdout.readlines():
            logger.log(line, should_print=False)
            # check for errors
            if line.lower().find('error') != -1:
                has_errors = True

        # log return value
        return_value = output.wait()
        logger.log('return value: {return_value}'.format(return_value=return_value), should_print=False)

        # exit if has errors
        if has_errors or return_value != 0:
            raise Exception('Git command failed. see log file for more details.')

    except Exception, ex:
        logger.error('command failed with exception: {ex}'.format(ex=ex))
        logger.error('exiting')
        exit(0)


def initiate_experiment_type(user_name, experiment_type, logger):
    # checkout experiment base branch
    experiment_base_branch_name = \
        ExperimentConsts.EXPERIMENT_BASE_BRANCH_NAME_FORMAT.format(
            base_branch_name=ExperimentConsts.BASE_BRANCH_NAME, experiment_type=experiment_type
        )
    logger.log(
        'checkout base branch: {branch_name}'.format(branch_name=experiment_base_branch_name), should_print=False
    )
    run_git_command(GitCommands.CHECKOUT_BRANCH.format(branch_name=experiment_base_branch_name), logger)

    # create new branch for the user
    new_branch_name = \
        ExperimentConsts.EXPERIMENT_USER_BRANCH_NAME_FORMAT.format(
            user_name=user_name, experiment_type=experiment_type
        )
    logger.log('create new branch: {branch_name}'.format(branch_name=new_branch_name), should_print=False)
    run_git_command(GitCommands.CREATE_NEW_BRANCH.format(branch_name=new_branch_name), logger)

    # checkout created branch
    logger.log('checkout new branch: {branch_name}'.format(branch_name=new_branch_name), should_print=False)
    run_git_command(GitCommands.CHECKOUT_BRANCH.format(branch_name=new_branch_name), logger)

    # return new branch name
    return new_branch_name


def commit_changes(logger):
    # add all files
    run_git_command(GitCommands.ADD_ALL_FILES, logger)

    # commit changes
    logger.log('Please briefly explain what have you done: ')
    commit_message = raw_input()
    run_git_command(GitCommands.COMMIT_CHANGES.format(msg=commit_message), logger)


def end_experiment_type(branch_name, logger):
    # verify that all changes has been committed
    answer = ''
    while answer not in ['y', 'n']:
        answer = raw_input('Have you committed all of your changes? [y/n] ')
    if 'n' == answer:
        commit_changes(logger)

    # push changes
    run_git_command(GitCommands.PUSH_CHANGES.format(branch_name=branch_name), logger)


def main():
    # local vars
    left_experiments = list(ExperimentConsts.EXPERIMENT_TYPES)
    logger = Logger()

    # read user name
    user_name = raw_input("Enter your id: ")

    # start interactive mode
    logger.log('Hello {user_name}! lets begin :)'.format(user_name=user_name))

    while len(left_experiments) > 0:
        # start experiment
        logger.print_msg('Choose experiment type:')
        for index, name in enumerate(left_experiments):
            logger.print_msg('{index} - {name}'.format(index=index, name=name))
        selected_experiment_type_index = \
            raw_input('Enter your selection: [0-{max_val}] '.format(max_val=len(left_experiments)-1))

        # verify input
        try:
            if int(selected_experiment_type_index) not in range(len(left_experiments)):
                continue
        except:
            continue

        selected_experiment_type_index = int(selected_experiment_type_index)
        selected_experiment_type = left_experiments[selected_experiment_type_index]
        logger.log(
            'selected: {experiment_type}'.format(experiment_type=selected_experiment_type), should_print=False
        )

        # initiate experiment
        branch_name = initiate_experiment_type(user_name, selected_experiment_type, logger)

        # run the experiment until its completion
        logger.print_msg('Ok, you can start working on the code, as explained to you. Good Luck!')

        selected_action = 0
        while selected_action != '1':
            logger.print_msg('Now you can:')
            logger.print_msg('0 - commit changes')
            logger.print_msg('1 - end experiment')
            selected_action = raw_input('Enter your selection: [0-1] ')
            if selected_action == '0':
                commit_changes(logger)

        # end experiment and start another one
        end_experiment_type(branch_name, logger)
        left_experiments.remove(selected_experiment_type)

    logger.log('Thank you {user_name}! the experiment is over.'.format(user_name=user_name))
    logger.print_msg('We greatly appreciate your contribution.')
    logger.print_msg('You have made our rabbit happy!')
    logger.print_msg('   (\_/)   ')
    logger.print_msg('   (^.^)   ')
    logger.print_msg('  \(> <)/  ')


if __name__ == '__main__':
    main()
