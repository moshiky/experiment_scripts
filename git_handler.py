
import subprocess
from evaluation_consts import EvaluationConsts
from git_commands import GitCommands


class GitHandler:

    def __init__(self, logger):
        self.__logger = logger
        self.__last_output = None

    def checkout_branch(self, branch_name, working_directory):
        git_command = GitCommands.CHECKOUT_BRANCH.format(branch_name=branch_name)
        try:
            self.__run_git_command(git_command, cwd=working_directory)
        except Exception, ex:
            if self.__last_output.find('did not match any file(s) known to git') > -1:
                raise Exception(EvaluationConsts.BRANCH_NOT_FOUND_EXCEPTION_STRING)
            else:
                raise ex

    def __run_git_command(self, command, cwd=None):
        self.__logger.log('running command: {cmd}, on: {cwd}'.format(cmd=command, cwd=cwd), should_print=False)

        try:
            # execute command
            output = \
                subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=cwd
                )

            # log command output
            has_errors = False
            output_lines = 'command output:'
            for line in output.stdout.readlines():
                output_lines += '\n' + line
                # check for errors
                if line.lower().find('error') != -1:
                    has_errors = True
            self.__logger.log(output_lines, should_print=False)
            self.__last_output = output_lines

            # log return value
            return_value = output.wait()
            self.__logger.log('return value: {return_value}'.format(return_value=return_value), should_print=False)

            # exit if has errors
            if has_errors or return_value != 0:
                raise Exception('Git command failed. see log file for more details.')

        except Exception, ex:
            self.__logger.error('command failed with exception: {ex}'.format(ex=ex))
            raise ex
