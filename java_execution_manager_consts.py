
import os


class JavaExecutionManagerConsts:

    # need to be verified and configured before each run

    JDK_PATH = r'C:\Program Files\Java\jdk1.8.0_131\bin'

    DEPENDENCY_LIB_PATH = r'C:\exp\jfreechart-1.0.19\jfreechart-1.0.19\lib'

    # custom values for each experiment type

    DEPENDENCY_LIBS = [
        'jfreechart-1.0.19.jar',
        'jcommon-1.0.23.jar'
    ]

    SOURCE_FILES = [
        r'src\main\java\problem\predator\*.java',
        r'src\main\java\problem\learning\*.java',
        r'src\main\java\problem\utils\*.java',
        r'src\main\java\problem\RNG.java'
    ]

    # constants

    CLASS_FILES_DIR_PATH_BASE = os.path.join(os.path.dirname(__file__), '..', 'evaluation_results')

    COMPILER_FILE_NAME = r'javac.exe'

    EXECUTE_FILE_NAME = r'java.exe'

    MAIN_CLASS_NAME = r'problem.predator.Experiments'

    COMPILE_COMMAND_TEMPLATE = '"{compiler_path}" -classpath "{dependencies}" -d "{output_path}" {source_path}'
    RUN_COMMAND_TEMPLATE = '"{execute_file_path}" -classpath "{dependencies}" {main_class_name}'

    def __init__(self):
        pass
