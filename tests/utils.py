

def expect_dict_to_str(expect_dict):
    """
    Helper function to allow the user to provide a string depicting
    exactly what is expected

    This allows for very unusual cases or otherwise tricky-to-test cases
    to still be tested easily via string comparision
    """

    expect_list = []

    for name, val in expect_dict.items():
        str_val = "'" + name + "': "
        if isinstance(val, str):
            str_val += val
        else:
            str_val += str(val)
        expect_list.append(str_val)

    return '{' + ', '.join(expect_list) + '}'
