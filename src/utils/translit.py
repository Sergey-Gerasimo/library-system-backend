TRANSLIT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
    "А": "A",
    "Б": "B",
    "В": "V",
    "Г": "G",
    "Д": "D",
    "Е": "E",
    "Ё": "Yo",
    "Ж": "Zh",
    "З": "Z",
    "И": "I",
    "Й": "Y",
    "К": "K",
    "Л": "L",
    "М": "M",
    "Н": "N",
    "О": "O",
    "П": "P",
    "Р": "R",
    "С": "S",
    "Т": "T",
    "У": "U",
    "Ф": "F",
    "Х": "Kh",
    "Ц": "Ts",
    "Ч": "Ch",
    "Ш": "Sh",
    "Щ": "Shch",
    "Ъ": "",
    "Ы": "Y",
    "Ь": "",
    "Э": "E",
    "Ю": "Yu",
    "Я": "Ya",
}


def translit(string: str) -> str:
    """
    Транслитерирует русский текст в латинский с использованием стандартных правил.

    :param string: Исходная строка на русском языке.
    :type string: str
    :return: Строка с замененными русскими символами на латинские.
    :rtype: str

    Пример::
        >>> translit("Привет, мир!")
        'Privet, mir!'
    """
    tbl = string.maketrans(TRANSLIT)
    return string.translate(tbl)


def translit_dict(d: dict) -> dict:
    """
    Транслитерирует **значения** переданного словаря, сохраняя ключи неизменными.

    :param d: Словарь, значения которого требуется транслитерировать.
    :type d: dict
    :return: Новый словарь с транслитерированными значениями.
    :rtype: dict

    Пример::
        >>> translit_dict({"name": "Иван", "city": "Москва"})
        {'name': 'Ivan', 'city': 'Moskva'}
    """
    new_dict = {}
    for key, value in d.items():  # Исправлено: было .values()
        new_dict[key] = translit(str(value)) if isinstance(value, str) else value
    return new_dict
