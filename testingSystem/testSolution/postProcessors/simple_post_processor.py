def processor(checked_tests, statuses):
    """
    Возвращает оценку в процентах
    (0% - ничего не сделано, 100% - все правильно)
    """
    return len([test for test in checked_tests
                if test.status == statuses.OK]) / len(checked_tests) * 100
