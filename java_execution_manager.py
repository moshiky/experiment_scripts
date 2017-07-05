
import os
import glob
import shutil
import subprocess
import random
from threading import Lock
from java_execution_manager_consts import JavaExecutionManagerConsts


class JavaExecutionManager:

    def __init__(self, p_logger):
        self.__logger = p_logger
        self.__rand_num = -1
        self.__compile_lock = Lock()

    def run_code(self, source_dir_path, compile_lock=None):
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
        if compile_lock is None:
            compile_lock = self.__compile_lock

        self.__logger.log('waiting for compiling to be available')
        with compile_lock:
            self.__compile_code(source_dir_path, class_files_dir_path)

        # run compiled code
        self.__run_compiled_code(class_files_dir_path)

    def __run_compiled_code(self, class_files_dir_path):
        self.__logger.log('running code')
        class_files_dir_path = os.path.realpath(class_files_dir_path)

        # get all dependency file paths
        dependency_paths = JavaExecutionManagerConsts.DEPENDENCY_FILE_PATHS
        dependency_paths.append(class_files_dir_path)

        # build run command
        command = \
            JavaExecutionManagerConsts.RUN_COMMAND_TEMPLATE.format(
                execute_file_path=os.path.join(
                    JavaExecutionManagerConsts.JDK_PATH,
                    JavaExecutionManagerConsts.EXECUTE_FILE_NAME
                ),
                dependencies=';'.join(dependency_paths),
                main_class_name=JavaExecutionManagerConsts.MAIN_CLASS_NAME
            )

        # run command
        self.__run_executable(command, cwd=os.path.dirname(class_files_dir_path))

    def __get_file_list(self, source_dir_path, extension):
        dir_files = glob.glob(source_dir_path + r'\*')
        java_files = list()
        for file_name in dir_files:
            if os.path.isdir(file_name):
                # java_files.append(file_name + r'\*.java')
                java_files += self.__get_file_list(file_name, extension)
            elif file_name.endswith(extension):
                java_files.append(file_name)
        return java_files

    def __compile_code(self, source_dir_path, class_files_dir_path):
        self.__logger.log('compiling')
        # create source files file
        source_dir_path = os.path.join(source_dir_path, JavaExecutionManagerConsts.SOURCE_BASE_FOLDER)
        source_paths = self.__get_file_list(source_dir_path, '.java')
        source_paths = ['"' + p.replace('\\', '\\\\') + '"' for p in source_paths]
        self.__rand_num = random.randint(1, 9999999)
        sources_file_path = r'c:\exp\sources_{rand_num}.txt'.format(rand_num=self.__rand_num)
        self.__logger.log('sources file: ' + sources_file_path, should_print=False)
        with open(sources_file_path, 'wb') as sources_file:
            sources_file.write('\n'.join(source_paths))

        # get all dependency file paths
        dependency_paths = self.__get_file_list(JavaExecutionManagerConsts.MAVEN_DEPENDENCIES_FOLDER_PATH, '.jar')
        dependency_paths += JavaExecutionManagerConsts.DEPENDENCY_FILE_PATHS
        dependency_paths = [p.replace('\\', '\\\\') for p in dependency_paths]
        dependencies_file_path = r'c:\exp\dependencies_{rand_num}.txt'.format(rand_num=self.__rand_num)
        self.__logger.log('dependencies file: ' + dependencies_file_path, should_print=False)
        with open(dependencies_file_path, 'wb') as dependencies_file:
            dependencies_file.write('"' + (';'.join(dependency_paths)) + '"')

        # build params list
        command = \
            JavaExecutionManagerConsts.COMPILE_COMMAND_TEMPLATE.format(
                compiler_path=os.path.join(
                    JavaExecutionManagerConsts.JDK_PATH,
                    JavaExecutionManagerConsts.COMPILER_FILE_NAME
                ),
                dependencies='@' + dependencies_file_path,
                output_path=class_files_dir_path,
                source_path='@' + sources_file_path
            )

        # run command
        self.__run_executable(command)

        # copy resources folder
        source_path = os.path.join(source_dir_path, JavaExecutionManagerConsts.RESOURCES_DIR_LOCATION)
        destination_path = os.path.join(class_files_dir_path, JavaExecutionManagerConsts.RESOURCES_DIR_LOCATION)
        shutil.copytree(source_path, destination_path)

        # delete tmp files
        os.remove(sources_file_path)
        os.remove(dependencies_file_path)

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
            if has_errors or return_value not in [0, 130]:
                raise Exception(JavaExecutionManagerConsts.COMMAND_FAILED_EXCEPTION_STRING)

        except Exception, ex:
            self.__logger.error('command failed with exception: {ex}'.format(ex=ex))
            raise ex
