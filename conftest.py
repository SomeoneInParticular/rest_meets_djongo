import pytest


# def pytest_collection_modifyitems(items):
#     for item in items:
#         print(item)


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
