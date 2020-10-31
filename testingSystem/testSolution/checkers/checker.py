def check(test, output, strip_answer):
    """Возвращает True, если ответ на тест правильный, иначе False"""
    return strip_answer(output) == strip_answer(test.input)[::-1]
