from testingSystem import models
import subprocess
from SchoolTestingSystem import settings
import os
import shutil
import psutil
import threading
from concurrent import futures
import time
from importlib import import_module
from .postProcessors.simple_post_processor import processor \
    as simple_post_processor

REAL_TIME_LIMIT = 5  # seconds


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
    attempt.score = post_processor(checked_tests, models.Status)
    for test in checked_tests:
        test.save()
    attempt.checked_tests.add(*checked_tests)
    attempt.save()


def check_resources(process: psutil.Process):
    with process.oneshot():
        user_time_used = process.cpu_times().user
        system_time_used = process.cpu_times().system
        cpu_time_used = (user_time_used + system_time_used) * 1000
        real_time_used = process.create_time()
        memory_used = process.memory_info().rss // 1024
    return memory_used, cpu_time_used, time.time() - real_time_used


def test_program(task, start_program, test):
    process = psutil.Popen(start_program,
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    process.suspend()

    with futures.ThreadPoolExecutor() as executor:
        tested = executor.submit(
            lambda: process.communicate(input=str.encode(test.input))
        )
        try:
            while not tested.done():
                try:
                    memory_used, cpu_time_used, real_time_used = \
                        check_resources(process)
                except ProcessLookupError:
                    break
                test.memory_used = max(test.memory_used, memory_used)

                if memory_used > task.memory_limit:
                    test.status = models.Status.ML
                    process.kill()

                if cpu_time_used > task.time_limit:
                    test.status = models.Status.TL
                    process.kill()

                if real_time_used > REAL_TIME_LIMIT + task.time_limit:
                    test.status = models.Status.IL
                    process.kill()

                process.resume()
                time.sleep(0.020)
                process.suspend()
            process.resume()
        except ProcessLookupError:
            pass
        output, errors = [s.decode() for s in tested.result()]

    test.message = errors
    if test.status == models.Status.OK:
        if process.returncode != 0:
            test.status = models.Status.RE
        elif not invoke_checker(task, test, output):
            test.status = models.Status.WA


def compile_python(folder_path, code):
    path = os.path.join(folder_path, "main.py")
    with open(path, 'w') as f:
        f.write(code)
    return "main.py"


def test_python(task, _, program_path, test):
    test_program(task, ['python3', program_path], test)


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


def test_cpp(task, _, program_path, test):
    test_program(task, [program_path], test)


def test_attempt(attempt, folder_path, compiler, tester):
    tests = [models.CheckedTest.objects.create(
        input=test.input, output=test.output,
        status=models.Status.OK, memory_used=0, time_used=0
    ) for test in attempt.task.testset.tests.all()]
    try:
        program_path = os.path.join(folder_path,
                                    compiler(folder_path, attempt.solution))
    except CompilationError as e:
        for test in tests:
            test.status = models.Status.CE
            test.message = e.msg
    else:
        with futures.ThreadPoolExecutor() as executor:
            executor.map(lambda test: tester(attempt.task, folder_path,
                                             program_path, test),
                         tests)
    invoke_post_processor(attempt, tests)
    return attempt


def submit_attempt(attempt: models.Attempt):
    compiler, tester = {
        str(models.Language.PYTHON): (compile_python, test_python),
        str(models.Language.CPP): (compile_cpp, test_cpp),
    }.get(str(attempt.language))

    folder_path = os.path.join(settings.BASE_DIR, "testingSystem",
                               "testSolution", "attempts",
                               f"attempt_{attempt.id}")

    try:
        os.makedirs(folder_path, exist_ok=True)
        test_attempt(attempt, folder_path, compiler, tester)
    except Exception as e:
        attempt.status = models.Status.SE
        raise e
    finally:
        shutil.rmtree(folder_path, ignore_errors=True)

    return attempt


def submit_attempt_async(attempt):
    threading.Thread(target=submit_attempt, args=[attempt]).start()
