
import os
import subprocess
from logger import Logger
from java_execution_manager_consts import JavaExecutionManagerConsts


class JavaExecutionManager:

    def __init__(self, p_logger):
        self.__logger = p_logger

    def run_code(self, source_dir_path):
        # build output dirs
        user_results_dir_name = os.path.basename(os.path.dirname(source_dir_path))
        user_id = user_results_dir_name.split('_')[0]
        run_type = '_'.join(user_results_dir_name.split('_')[1:])

        class_files_dir_path = \
            os.path.join(
                JavaExecutionManagerConsts.OUTPUT_DIR_PATH,
                user_id,
                run_type,
                'compiled_code'
            )
        try:
            os.makedirs(class_files_dir_path)
        except WindowsError, ex:
            if ex.winerror != 183:
                raise ex

        logs_dir_path = \
            os.path.join(
                JavaExecutionManagerConsts.OUTPUT_DIR_PATH,
                user_id,
                run_type,
                JavaExecutionManagerConsts.EXECUTION_LOGS_FOLDER_NAME
            )
        try:
            os.makedirs(logs_dir_path)
        except WindowsError, ex:
            if ex.winerror != 183:
                raise ex

        # compile code
        self.__compile_code(source_dir_path, class_files_dir_path)

        # run compiled code
        self.__run_compiled_code(class_files_dir_path)

    def __run_compiled_code(self, class_files_dir_path):
        # build run command
        command = \
            JavaExecutionManagerConsts.RUN_COMMAND_TEMPLATE.format(
                execute_file_path=os.path.join(
                    JavaExecutionManagerConsts.JDK_PATH,
                    JavaExecutionManagerConsts.EXECUTE_FILE_NAME
                ),
                dependencies=';'.join([class_files_dir_path] + JavaExecutionManagerConsts.DEPENDENCY_FILE_PATHS),
                main_class_name=JavaExecutionManagerConsts.MAIN_CLASS_NAME
            )

        # run command
        self.__run_executable(command, cwd=os.path.dirname(class_files_dir_path))

    def __compile_code(self, source_dir_path, class_files_dir_path):
        # build params list
        command = \
            JavaExecutionManagerConsts.COMPILE_COMMAND_TEMPLATE.format(
                compiler_path=os.path.join(
                    JavaExecutionManagerConsts.JDK_PATH,
                    JavaExecutionManagerConsts.COMPILER_FILE_NAME
                ),
                dependencies=';'.join(JavaExecutionManagerConsts.DEPENDENCY_FILE_PATHS),
                output_path=class_files_dir_path,
                source_path=' '.join(
                    map(
                        lambda name: os.path.join(source_dir_path, name),
                        JavaExecutionManagerConsts.SOURCE_FILES
                    )
                )
            )

        # run command
        self.__run_executable(command)

    def __run_executable(self, command, cwd=None):
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

            # log return value
            return_value = output.wait()
            self.__logger.log('return value: {return_value}'.format(return_value=return_value), should_print=False)

            # exit if has errors
            if has_errors or return_value != 0:
                raise Exception(JavaExecutionManagerConsts.COMMAND_FAILED_EXCEPTION_STRING)

        except Exception, ex:
            self.__logger.error('command failed with exception: {ex}'.format(ex=ex))
            raise ex


if __name__ == '__main__':
    logger = Logger()
    compiler = JavaExecutionManager(logger)
    compiler.run_code(r'c:\exp\predator_experiment_3')
