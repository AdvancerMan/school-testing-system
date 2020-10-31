from testingSystem import models
import subprocess
import signal
from SchoolTestingSystem import settings
import os
from concurrent import futures
import time
from importlib import import_module
from .postProcessors.simple_post_processor import processor \
    as simple_post_processor

REAL_TIME_LIMIT_ADDITION = 5  # seconds


def strip_answer(answer):
    return os.linesep.join(
        line.strip() for line in answer.split(os.linesep)
    ).strip()


def check_contents_are_equal(input, output, *args, **kwargs):
    return strip_answer(input) == strip_answer(output)


def get_checker(name):
    try:
        return import_module("testingSystem.testSolution."
                             "checkers." + name).check
    except AttributeError or ModuleNotFoundError:
        return check_contents_are_equal


def get_post_processor(name):
    try:
        return import_module("testingSystem.testSolution."
                             "postProcessors." + name).processor
    except AttributeError or ImportError:
        return simple_post_processor


def invoke_checker(task, input, output):
    return get_checker(task.checker_name)(input, output, strip_answer)


def invoke_post_processor(attempt, checked_tests):
    post_processor = get_post_processor(attempt.task.post_processor_name)
    attempt.score = post_processor(checked_tests, models.Status)
    for test in checked_tests:
        test.save()
    attempt.checked_tests.add(*checked_tests)
    attempt.save()


def check_resources(pid):
    with open(f'/proc/{pid}/status', 'r') as f:
        status_file = f.read().split(os.linesep)
    memory_used = [s for s in status_file if s.startswith('VmRSS')]
    if len(memory_used) == 0:
        raise FileNotFoundError()
    memory_used = int([s for s in memory_used[0].split() if s][1])

    with open(f'/proc/{pid}/schedstat', 'r') as f:
        time_used = int(f.read().split()[0]) // 10 ** 6
    return memory_used, time_used


def test_program(task, start_program, test):
    start_time = time.time()
    process = subprocess.Popen(start_program,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE)
    process.send_signal(signal.SIGSTOP)

    with futures.ThreadPoolExecutor() as executor:
        tested = executor.submit(
            lambda: process.communicate(input=str.encode(test.input))[0]
        )
        while not tested.done():
            try:
                memory_used, time_used = check_resources(process.pid)
            except FileNotFoundError:
                break
            test.memory_used = max(test.memory_used, memory_used)
            test.time_used = max(test.time_used, time_used)

            if memory_used > task.memory_limit:
                test.status = models.Status.ML
                process.send_signal(signal.SIGKILL)

            if time_used > task.time_limit:
                test.status = models.Status.TL
                process.send_signal(signal.SIGKILL)

            if time.time() - start_time > \
                    REAL_TIME_LIMIT_ADDITION + task.time_limit // 1000:
                test.status = models.Status.IL
                process.send_signal(signal.SIGKILL)

            process.send_signal(signal.SIGCONT)
            time.sleep(0.020)
            process.send_signal(signal.SIGSTOP)
        process.send_signal(signal.SIGCONT)
        result = tested.result()

    if test.status == models.Status.OK:
        if process.returncode != 0:
            test.status = models.Status.RE
        elif not invoke_checker(task, test.input, result.decode()):
            test.status = models.Status.WA


def compile_python(folder_path, code):
    path = os.path.join(folder_path, "main.py")
    with open(path, 'w') as f:
        f.write(code)
    return "main.py"


def test_python(task, _, program_path, test):
    test_program(task, ['python3', program_path], test)


def compile_cpp(folder_path, code):
    source_path = os.path.join(folder_path, "main.cpp")
    with open(source_path, 'w') as f:
        f.write(code)
    compilation = subprocess.run(["g++", source_path,
                                  "-o", os.path.join(folder_path, "main")])
    compilation.check_returncode()
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
    except subprocess.CalledProcessError:
        for test in tests:
            test.status = models.Status.CE
        invoke_post_processor(attempt, tests)
        return attempt

    for i, test in zip(range(len(tests)), tests):
        tester(attempt.task, folder_path, program_path, test)
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
        subprocess.run(["mkdir", "-p", folder_path])
        test_attempt(attempt, folder_path, compiler, tester)
    except Exception as e:
        attempt.status = models.Status.SE
        raise e
    finally:
        subprocess.run(["rm", "-rf", folder_path])

    return attempt
