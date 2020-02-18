from setuptools import setup

from rest_meets_djongo import __version__


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='rest_meets_djongo',
    version=__version__,
    packages=['rest_meets_djongo'],

    install_requires=[
        'Django<3',
        'djangorestframework<4',
        'djongo>=1.3.0,<1.3.1',
    ],

    setup_requires=['pytest-runner'],
    test_suite='tests',
    test_requires=['pytest', 'pytest-django'],

    author='Kalum J. Ost',
    author_email='kalumost@gmail.com',
    description=(
        "Allows for automatic serialization of Djongo fields w/ Django REST"
    ),
    long_description=readme(),
    keywords="mongodb djongo rest_framework rest apis fields",
    url="https://gitlab.com/SomeoneInParticular/rest_meets_djongo",
    long_description_content_type="text/markdown",
    license='MIT',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    zip_safe=False,
)
