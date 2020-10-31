from testingSystem import models
import subprocess
import signal
from SchoolTestingSystem import settings
import os
from concurrent import futures
import time

REAL_TIME_LIMIT_ADDITION = 5  # seconds


def strip_answer(answer):
    return os.linesep.join(
        line.strip() for line in answer.split(os.linesep)
    ).strip()


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


def test_program(attempt, console_command_and_args, test):
    start_time = time.time()
    process = subprocess.Popen(console_command_and_args,
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
            attempt.memory_used = max(attempt.memory_used, memory_used)
            attempt.time_used = max(attempt.time_used, time_used)

            if memory_used > attempt.task.memory_limit:
                attempt.status = models.Status.ML
                process.send_signal(signal.SIGKILL)

            if time_used > attempt.task.time_limit:
                attempt.status = models.Status.TL
                process.send_signal(signal.SIGKILL)

            if time.time() - start_time > \
                    REAL_TIME_LIMIT_ADDITION + attempt.task.time_limit // 1000:
                attempt.status = models.Status.IL
                process.send_signal(signal.SIGKILL)

            process.send_signal(signal.SIGCONT)
            time.sleep(0.020)
            process.send_signal(signal.SIGSTOP)
        process.send_signal(signal.SIGCONT)
        result = tested.result()

    if attempt.status == models.Status.OK:
        if process.returncode != 0:
            attempt.status = models.Status.RE
        elif strip_answer(test.output) != strip_answer(result.decode()):
            attempt.status = models.Status.WA


def compile_python(folder_path, code):
    path = os.path.join(folder_path, "main.py")
    with open(path, 'w') as f:
        f.write(code)
    return "main.py"


def test_python(_, program_path, test, attempt):
    test_program(attempt, ['python3', program_path], test)


def compile_cpp(folder_path, code):
    source_path = os.path.join(folder_path, "main.cpp")
    with open(source_path, 'w') as f:
        f.write(code)
    compilation = subprocess.run(["g++", source_path,
                                  "-o", os.path.join(folder_path, "main")])
    compilation.check_returncode()
    return "main"


def test_cpp(folder_path, program_path, test, attempt):
    test_program(attempt, [program_path], test)


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

        try:
            program_path = os.path.join(folder_path,
                                        compiler(folder_path, attempt.solution))
        except subprocess.CalledProcessError as e:
            attempt.status = models.Status.CE
            return attempt

        tests = list(attempt.task.testset.tests.all())
        attempt.failed_test_index = 0
        for i, test in zip(range(len(tests)), tests):
            tester(folder_path, program_path, test, attempt)
            if attempt.status != models.Status.OK:
                return attempt
            attempt.failed_test_index += 1
    except Exception as e:
        attempt.status = models.Status.RJ
        raise e
    finally:
        subprocess.run(["rm", "-rf", folder_path])

    return attempt
