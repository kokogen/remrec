# exceptions.py

class PermanentError(Exception):
    """Ошибка, которая не исправится повторной попыткой (например, битый файл)."""
    pass

class TransientError(Exception):
    """Временная ошибка (например, сбой сети), которая может исчезнуть при повторной попытке."""
    pass
