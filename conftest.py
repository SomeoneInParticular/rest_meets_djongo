import pytest


@pytest.fixture(scope='session')
def error_raised():
    """Builds a raise instance for use w/ error checks"""
    from rest_framework.exceptions import ValidationError
    from pytest import raises

    return raises(ValidationError)


@pytest.fixture(scope='session')
def assert_dict_equals():
    from tests.utils import format_dict

    def _compare_data(dict1, dict2):
        assert format_dict(dict1) == format_dict(dict2)

    return _compare_data


@pytest.fixture(scope='session')
def instance_matches_data():

    def _does_instance_match_data(instance, data):
        for field in data.keys():
            if getattr(instance, field) != data[field]:
                return False
        return True

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
