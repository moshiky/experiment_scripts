
import subprocess
from experiment_consts import ExperimentConsts
from git_commands import GitCommands


class ExperimentHandler:

    def __init__(self, logger, base_path, experiment_type, participant_name):
        self.__logger = logger
        self.__base_path = base_path
        self.__experiment_type = experiment_type
        self.__participant_name = participant_name

        # build experiment base branch name
        self.__experiment_base_branch_name = self.__get_experiment_base_branch_name()

        # build participant branch name
        self.__participant_branch_name = self.__get_participant_branch_name(self.__participant_name)

    def initiate_for_participant(self):
        # checkout experiment base branch
        self.__checkout_branch(self.__experiment_base_branch_name)

        # create branch for participant
        self.__create_branch(self.__participant_branch_name)

        # checkout participant branch
        self.__checkout_branch(self.__participant_branch_name)

    def __checkout_branch(self, branch_name):
        git_command = GitCommands.CHECKOUT_BRANCH.format(branch_name=branch_name)
        self.__run_git_command(git_command)

    def __create_branch(self, branch_name):
        git_command = GitCommands.CREATE_NEW_BRANCH.format(branch_name=branch_name)
        self.__run_git_command(git_command)

    def __run_git_command(self, command, cwd=None):
        self.__logger.log('running command: {cmd}'.format(cmd=command), should_print=False)

        try:
            # execute command
            output = \
                subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=cwd if cwd is not None else ExperimentConsts.WORKING_DIRECTORY_PATH
                )

            # log command output
            self.__logger.log('command output:', should_print=False)
            has_errors = False
            for line in output.stdout.readlines():
                self.__logger.log(line, should_print=False)
                # check for errors
                if line.lower().find('error') != -1:
                    has_errors = True

            # log return value
            return_value = output.wait()
            self.__logger.log('return value: {return_value}'.format(return_value=return_value), should_print=False)

            # exit if has errors
            if has_errors or return_value != 0:
                raise Exception('Git command failed. see log file for more details.')

        except Exception, ex:
            self.__logger.error('command failed with exception: {ex}'.format(ex=ex))
            self.__logger.error('exiting')
            exit(0)

    def __get_experiment_base_branch_name(self):
        return ExperimentConsts.EXPERIMENT_BASE_BRANCH_NAME_FORMAT.format(
            base_branch_name=ExperimentConsts.BASE_BRANCH_NAME, experiment_type=self.__experiment_type
        )

    def __get_participant_branch_name(self, participant_name):
        return ExperimentConsts.EXPERIMENT_USER_BRANCH_NAME_FORMAT.format(
            user_name=participant_name, experiment_type=self.__experiment_type
        )

    def commit_changes(self, comment=None, working_directory=None):
        if comment is None:
            # ask the user for short description of the changes
            self.__logger.log('Please briefly explain what have you done: ')
            commit_message = raw_input()
        else:
            commit_message = comment

        # add all files
        # self.__run_git_command(GitCommands.ADD_ALL_FILES, cwd=working_directory)

        # commit changes
        self.__run_git_command(GitCommands.COMMIT_CHANGES.format(msg=commit_message), cwd=working_directory)

    def push_branch(self, branch_name=None, working_directory=None, push_all=False):
        if push_all:
            # push all branches
            self.__run_git_command(GitCommands.PUSH_CHANGES.format(branch_name='--all'))

        else:
            # push just current branch
            self.__run_git_command(
                GitCommands.PUSH_CHANGES.format(
                    branch_name=branch_name if branch_name is not None else self.__participant_branch_name
                ),
                cwd=working_directory
            )

    def pull_branch(self, branch_name, working_directory):
        self.__run_git_command(
            GitCommands.PULL_CHANGES.format(branch_name=branch_name),
            cwd=working_directory
        )
