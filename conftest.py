import pytest


@pytest.fixture(scope='session')
def error_raised():
    """Builds a raise instance for use w/ error checks"""
    from rest_framework.exceptions import ValidationError
    from pytest import raises

    return raises(ValidationError)


@pytest.fixture(scope='session')
def assert_dict_equals():
    """Compare two dictionaries to one another"""
    from tests.utils import format_dict

    def _compare_data(dict1, dict2):
        assert format_dict(dict1) == format_dict(dict2)

    return _compare_data


@pytest.fixture(scope='session')
def instance_matches_data():
    """Confirm that all data in a dictionary is present in an instance"""
    def _does_instance_match_data(instance, data):
        err_list = {}
        for field in data.keys():
            # Common error types
            try:
                if not hasattr(instance, field):
                    msg = f"Field `{field}` not found in model instance!"
                    err_list[field] = msg
                if not getattr(instance, field).__eq__(data[field]):
                    msg = (f"Field `{field}` has a value of " 
                           f"'{getattr(instance, field)}', but a value of "
                           f"'{data[field]}' was expected")
                    err_list[field] = msg
            # Rarer error types
            except Exception as err:
                err_list[field] = err

        if err_list:
            raise AssertionError(str(err_list))

    return _does_instance_match_data


def pytest_configure():
    from django.conf import settings

    settings.configure(
        DEBUG=True,
        TEMPLATE_DEBUG=True,
        SECRET_KEY='T35TK3Y',
        DATABASES={
            'default': {
                'ENGINE': 'djongo',
                'NAME': 'test_db'
            }
        },
        INSTALLED_APPS=(
            'rest_framework',
            'rest_meets_djongo',
            'tests'
        )
    )

    try:
        import django
        django.setup()
    except AttributeError:
        pass
