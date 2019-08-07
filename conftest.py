import pytest


@pytest.fixture(scope='session')
def raises():
    """Builds a named tuple of error raising cases for use in tests"""
    from bson.errors import InvalidId
    from collections import namedtuple
    from django.core.exceptions import FieldDoesNotExist
    from django.core.exceptions import ValidationError as ModelValidationError
    from rest_framework.exceptions import ValidationError as SerializerValidationError
    from pytest import raises

    # Easy to manage error types
    error_type_list = [FieldDoesNotExist, AssertionError, TypeError, InvalidId]
    error_name_list = [err.__name__ for err in error_type_list]

    # Name conflict handling error types
    error_type_list = error_type_list + [ModelValidationError, SerializerValidationError]
    error_name_list = error_name_list + ["ModelValidationError", "SerializerValidationError"]

    # Convert them to 'raise' use cases
    error_raise_list = [raises(err) for err in error_type_list]

    # Build the error tuple for use
    ErrorTuple = namedtuple('ErrorRaises', error_name_list)
    return ErrorTuple(*error_raise_list)


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
