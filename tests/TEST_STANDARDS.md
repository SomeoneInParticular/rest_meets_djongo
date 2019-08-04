Test Design and Standards (rest-meets-djongo)
===================================
Test design standards for `rest-meets-djongo` test case construction and modification.

This document exists as more of a guideline; use this to remind yourself if you've missed adding/modifying/removing any tests relevant to the changes you've made, and to make sure where you placed said code is sensible. When in doubt, follow [PEP8](https://www.python.org/dev/peps/pep-0008/) style guidelines.

## Table of Contents
- [When to Test](#when-to-test)
- [File Structure](#file-structure)
- [Test Case and Fixture Formatting](#test-case-and-fixture-formatting)
- [Documentation](#documentation)

## When to Test
New tests should be created when any of the following occurs:
* A new package feature is added
* `djongo`/`django-rest-framework`/`mongodb` is updated to a version w/ a new feature
* An issue which occurs under specific circumstances is resolved via special treatment

Existing tests should be modified under the following circumstances:
* A previous feature is modified (ex. a custom field's expected input data format changes)
* `djongo`/`django-rest-framework`/`mongodb` is updated to a version w/ existing features having different expected inputs/outputs

Existing tests should be removed under the following circumstances:
* A feature was removed during the latest change
* `djongo`/`django`/`mongodb` drops support for a feature
* A previous issue test's specific circumstance(s) are no longer possible as a result of the change

## File Structure
Files containing non-test contents (testing utilities, configuration, basic models, readme text, etc.) should be placed in the base `tests` package for ease of access.

All files containing test cases should be placed in the package corresponding to the test case's intended target. For example, tests intended to confirm intended functionality of the `serializers.py` file should be placed in the `serializer` package within the `tests` package.

Tests involving specific cases for issue resolution or unique scenarios involving specific scenario setup should be placed in the `tests.complex` package. This also goes for tests where more than one target file is being tested (this might occur during integration testing).

For packages corresponding to files, a file should exist for every publicly accessible class/function within the target file; this file will contain all test cases for this object, and should be named, in lowercase, `test_<object_name>.py` (I.E. `test_objectidfield.py`). For `complex` test files, each file should correspond to one scenario of use; this file should contain all test cases for this scenario, and should be named, in lowercase, `test_<scenario_name>.py` (I.E. `test_custom_field_override.py`).

## Test Case, Fixture, and Test Formatting
Test cases should inherit from `object` and, if database usage is required, be marked with the [`@pytest.mark.django_db`](https://pytest-django.readthedocs.io/en/latest/database.html#enabling-database-access-in-tests) mark, modified appropriately should transactions be required. Avoid `django.TestCase` usage unless multi-database functionality testing is required; this may also be prohibited if `pytest-django` updates to support the feature natively.

Multiple test cases can exist within a file, and should be used to help categorize tests for similar applications of the target code (mapping, integration, option parsing, etc.). These should be named in a way which describes the facet being tested (I.E. a test case for integration of a serializer with the Djongo and Django-REST could be called `Integration`). Remember that our file structure also provides information regarding the test; avoid naming redundancy where possible.

[PyTest fixtures](https://docs.pytest.org/en/latest/fixture.html) should also be used when set up is required for a given test or set of tests. Such fixture's should be placed at the top of the file (if intended for use with an entire test case) or test case (if intended for use with a subset of tests within the test case). Like test cases, these should be named in a way which describes their intended use. Use a test-case fixture in place of the `setUp` function wherever possible. Try to avoid package scope.

Standalone tests (those without a test case class) should only be used when the test case which would contain them would contain only that test if it were created. In any other case, the test should be placed within an appropriate test case.

## Documentation
Tests and test cases should all have a brief description of their purpose, along with any quirks/details that may be important to keep in mind if someone else were to modify the test.

Fixtures should also have a short comment explaining what they do, as to allow modification further down the line or re-use. The same goes for utility functions.

Please use docstring (`"""`) style comments for the above scenarios, following [PEP 257](https://www.python.org/dev/peps/pep-0257/) guidelines when possible. Reserve `#` style comments for remarks on specific parts of the code within the test functions themselves (in-line or code block descriptive).