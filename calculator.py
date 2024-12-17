functions_dict = {
    '+': lambda x, y: x + y,
    '-': lambda x, y: x - y,
    '/': lambda x, y: x / y,
    '*': lambda x, y: x * y
}


def calculator(expression: str) -> float:
    expression = expression.replace(' ', '')
    count = 0
    key = None
    for i in expression:
        if i in functions_dict:
            key = i
            count += 1
    else:
        if count > 1:
            raise ValueError('Оставьте один арифметический знак!')
        if count == 0:
            raise ValueError('Нету арифметического знака')

    expression = expression.split(key)
    if all(expression):
        try:
            return functions_dict[key](float(expression[0]), float(expression[1]))
        except ValueError as e:
            raise ValueError("Нужно ввести число")


if __name__ == '__main__':
    print(calculator(input('Expression: ')))
