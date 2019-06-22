from setuptools import setup, find_packages

version = '0.0.1'


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='rest_meets_djongo',
    version=version,
    packages=find_packages(),
    url="https://gitlab.com/SomeoneInParticular/rest_meets_djongo",
    author='Kalum J. Ost',
    author_email='kalumost@gmail.com',
    description="Allows for automatic serialization of Djongo fields w/ Django REST",
    long_description=readme(),
    long_description_content_type="test/",
    license='MIT',
    install_requires=[
        'Django',
        'djangorestframework',
        'djongo',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    zip_safe=False,
)
