import pytest


@pytest.fixture(scope='session')
def build_tuple():
    """Enables automatic building of named tuples for use w/ other fixtures"""
    from collections import namedtuple

    def _build_tuple(name, val_dict):
        val_names = [val for val in val_dict.keys()]
        ValTuple = namedtuple(name, val_names)
        val_tuple = ValTuple(**val_dict)

        return val_tuple

    return _build_tuple


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
