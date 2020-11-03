from testingSystem import models
import subprocess
from SchoolTestingSystem import settings
import os
import traceback
import shutil
import psutil
import threading
from concurrent import futures
import time
from importlib import import_module
from .postProcessors.simple_post_processor import processor \
    as simple_post_processor

IDLENESS_TIME_LIMIT = 5000  # ms
RESOURCES_CHECK_PERIOD = 20  # ms


def strip_answer(answer):
    return os.linesep.join(
        line.strip() for line in answer.split(os.linesep)
    ).strip()


def check_contents_are_equal(test, output, *args, **kwargs):
    return strip_answer(test.output) == strip_answer(output)


def get_checker(name):
    try:
        return import_module("testingSystem.testSolution."
                             "checkers." + name).check
    except (ModuleNotFoundError, AttributeError):
        return check_contents_are_equal


def get_post_processor(name):
    try:
        return import_module("testingSystem.testSolution."
                             "postProcessors." + name).processor
    except (ModuleNotFoundError, AttributeError):
        return simple_post_processor


def invoke_checker(task, test, output):
    return get_checker(task.checker_name)(test, output, strip_answer)


def invoke_post_processor(attempt, checked_tests):
    post_processor = get_post_processor(attempt.task.post_processor_name)
    return post_processor(checked_tests, models.Status)


def check_resources(process: psutil.Process):
    with process.oneshot():
        user_time_used = process.cpu_times().user
        system_time_used = process.cpu_times().system
        cpu_time_used = (user_time_used + system_time_used) * 1000
        memory_used = process.memory_info().rss // 1024
    return memory_used, cpu_time_used


def execute_and_track_process(task, test, process):
    idle_time_used = 0
    while process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
        memory_used, cpu_time_used = check_resources(process)
        worked = cpu_time_used - test.time_used

        idle_time_used += RESOURCES_CHECK_PERIOD - worked
        test.memory_used = max(test.memory_used, memory_used)
        test.time_used = cpu_time_used

        if memory_used > task.memory_limit:
            test.status = models.Status.ML
            process.kill()

        if cpu_time_used > task.time_limit:
            test.status = models.Status.TL
            process.kill()

        if idle_time_used > IDLENESS_TIME_LIMIT:
            test.status = models.Status.IL
            process.kill()

        process.resume()
        time.sleep(RESOURCES_CHECK_PERIOD / 1000)
        process.suspend()
    process.resume()


def test_program(task, start_program, test):
    process = psutil.Popen(start_program,
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    process.suspend()

    with futures.ThreadPoolExecutor() as executor:
        tested = executor.submit(
            lambda: process.communicate(input=str.encode(test.test.input))
        )
        try:
            execute_and_track_process(task, test, process)
        except psutil.NoSuchProcess:
            pass
    output, errors = [s.decode() for s in tested.result()]

    test.message = errors
    if test.status == models.Status.TS:
        if process.returncode != 0:
            test.status = models.Status.RE
        elif invoke_checker(task, test.test, output):
            test.status = models.Status.OK
        else:
            test.status = models.Status.WA
    test.save()


def compile_python(folder_path, code):
    path = os.path.join(folder_path, "main.py")
    with open(path, 'w') as f:
        f.write(code)
    return "main.py"


def get_python_command(_, program_path):
    return 'python3', program_path


class CompilationError(Exception):
    def __init__(self, msg):
        self.msg = msg


def compile_cpp(folder_path, code):
    source_path = os.path.join(folder_path, "main.cpp")
    with open(source_path, 'w') as f:
        f.write(code)
    compilation = psutil.Popen(["g++", source_path,
                                "-o", os.path.join(folder_path, "main")],
                               stderr=subprocess.PIPE)
    error = compilation.communicate()[1]
    if compilation.returncode != 0:
        raise CompilationError(error.decode())
    return "main"


def get_cpp_command(_, program_path):
    return program_path


def test_attempt(attempt, folder_path, compiler, commander):
    tests = [models.CheckedTest.objects.create(
        test=test, status=models.Status.TS, memory_used=0, time_used=0
    ) for test in attempt.task.testset.tests.all()]
    attempt.checked_tests.add(*tests)
    attempt.save()

    try:
        program_path = os.path.join(folder_path,
                                    compiler(folder_path, attempt.solution))
    except CompilationError as e:
        for test in tests:
            test.status = models.Status.CE
            test.message = e.msg
            test.save()
    else:
        def test_program_on(test):
            try:
                test_program(attempt.task, command, test)
            except Exception as exc:
                traceback.print_exc()
                test.status = models.Status.SE
                test.save()
                raise exc

        with futures.ThreadPoolExecutor() as executor:
            command = commander(folder_path, program_path)
            executor.map(test_program_on, tests)
    attempt.score = invoke_post_processor(attempt, tests)
    attempt.save()
    return attempt


def submit_attempt(attempt):
    compiler, commander = {
        str(models.Language.PYTHON): (compile_python, get_python_command),
        str(models.Language.CPP): (compile_cpp, get_cpp_command),
    }.get(str(attempt.language))

    folder_path = os.path.join(settings.BASE_DIR, "testingSystem",
                               "testSolution", "attempts",
                               f"attempt_{attempt.id}")

    try:
        os.makedirs(folder_path, exist_ok=True)
        test_attempt(attempt, folder_path, compiler, commander)
    finally:
        shutil.rmtree(folder_path, ignore_errors=True)

    return attempt


def submit_attempt_async(attempt):
    threading.Thread(target=submit_attempt, args=[attempt]).start()
