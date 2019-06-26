from tests.test_settings import config_django


def pytest_configure():
    config_django()
