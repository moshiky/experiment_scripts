
import os


class JavaExecutionManagerConsts:

    # need to be verified and configured before each run

    JDK_PATH = r'C:\Program Files\Java\jdk1.8.0_144\bin'
    JRE_PATH = r'C:\Program Files\Java\jdk1.8.0_144\jre\bin'

    # custom values for each experiment type

    MAVEN_DEPENDENCIES_FOLDER_PATH = r'C:\Users\Experiment\.m2\repository'

    DEPENDENCY_FILE_PATHS = [
        r'C:\exp\libs\jfreechart-1.0.19\jfreechart-1.0.19\lib\jfreechart-1.0.19.jar',
        r'C:\exp\libs\jfreechart-1.0.19\jfreechart-1.0.19\lib\jcommon-1.0.23.jar',
        r'C:\exp\libs\commons-lang3-3.6-bin\commons-lang3-3.6\commons-lang3-3.6.jar',
        r'C:\exp\libs\commons-math3-3.6.1-bin\commons-math3-3.6.1\commons-math3-3.6.1.jar',
        r'C:\exp\libs\asm-all-3.3.jar'
    ]

    SOURCE_BASE_FOLDER = r'src\main\java'

    RESOURCES_DIR_LOCATION = r'ch\idsia\benchmark\mario\engine\resources'

    # constants

    DOMAIN_NAME = 'mario'

    OUTPUT_DIR_PATH = os.path.join(os.path.dirname(__file__), '..', 'evaluation_results', DOMAIN_NAME)

    COMPILER_FILE_NAME = r'javac.exe'

    EXECUTE_FILE_NAME = r'java.exe'

    MAIN_CLASS_NAME = r'competition.richmario.SimpleExperiment'

    COMPILE_COMMAND_TEMPLATE = '"{compiler_path}" -classpath {dependencies} -d "{output_path}" {source_path}'

    RUN_COMMAND_TEMPLATE = '"{execute_file_path}" -Xmx4g -classpath {dependencies} {main_class_name}'

    COMMAND_FAILED_EXCEPTION_STRING = 'EXTERNAL_COMMAND_FAILED'

    EXECUTION_LOGS_FOLDER_NAME = 'logs'

    def __init__(self):
        pass
