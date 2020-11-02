def check(test, output, strip_answer):
    """Возвращает True, если ответ на тест правильный, иначе False"""
    return len(output.split()) == 2 and sum(
        int(x) for x in strip_answer(output).replace('\n', ' ').split()[:2]
    ) == int(strip_answer(test.input))
