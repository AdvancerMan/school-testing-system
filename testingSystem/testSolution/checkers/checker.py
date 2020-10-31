def check(input, output, strip_answer):
    """Возвращает True, если ответ на тест правильный, иначе False"""
    return strip_answer(output) == strip_answer(input)[::-1]
