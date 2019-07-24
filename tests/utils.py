from rest_framework.exceptions import ErrorDetail


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


def build_error_dict(errors):
    """
    Take serializers thrown by an error and parse them to an easy to
    interpret dictionary
    """
    err_set = {}

    for field_name, error_list in errors.items():
        err_set.update({field_name: _interpret_error_list(error_list)})

    return err_set


def _interpret_error_list(error_list):
    """
    Chain recursion function for `build_error_list`

    Used to handle the list of errors produced when interpreting
    an error dictionary
    """
    ret_list = []

    for val in error_list:
        if isinstance(val, dict):
            new_code = build_error_dict(val)
        elif isinstance(val, ErrorDetail):
            new_code = val.code
        else:
            raise TypeError("The error dictionary has an invalidly typed"
                            "entry;\n Found `{}` type, should be a list or "
                            "`ErrorDetail` type.")
        ret_list.append(new_code)

    return ret_list
