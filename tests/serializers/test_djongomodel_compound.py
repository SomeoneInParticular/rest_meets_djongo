from collections import namedtuple

from rest_framework import fields as drf_fields

from rest_meets_djongo.serializers import DjongoModelSerializer

from pytest import fixture, mark, param, raises

from tests.models import ListModel, DictModel


@mark.compound
@mark.serializer
@mark.mapping
@mark.core
class TestMapping(object):
    def test_list_mapping(self, assert_dict_equals):
        """
        Serializer with a control field (CharField) and a ListField
        """
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = ListModel
                fields = '__all__'

        expected_dict = {
            'id': drf_fields.IntegerField(label='ID', read_only=True),
            'char_field': drf_fields.CharField(max_length=16),
            'list_field': drf_fields.ListField()
        }

        assert_dict_equals(TestSerializer().get_fields(), expected_dict)

    def test_dict_mapping(self, assert_dict_equals):
        """
        Serializer with a control field (IntField) and a DictField
        """
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = DictModel
                fields = '__all__'

        expected_dict = {
            'id': drf_fields.IntegerField(label='ID', read_only=True),
            'int_field': drf_fields.IntegerField(
                max_value=2147483647, min_value=-2147483648
            ),
            'dict_field': drf_fields.DictField()
        }
        assert_dict_equals(TestSerializer().get_fields(), expected_dict)


@mark.compound
@mark.serializer
@mark.integration
@mark.core
@mark.django_db
class TestIntegration(object):
    # -- Fixtures -- #
    @fixture
    def prepped_db(self):
        prep_db = {}
        # List object
        list_data = {
            'char_field': "HELLO WORLD!",
            'list_field': ["valA", "valB", "valC"]
        }
        prep_db[ListModel] = ListModel.objects.create(**list_data)
        # Dictionary object
        dict_data = {
            'int_field': 42,
            'dict_field': {
                "valA": 'A',
                "valB": 2
            }
        }
        prep_db[DictModel] = DictModel.objects.create(**dict_data)

        return prep_db

    # -- Tests -- #
    @mark.parametrize(
        ["serializer", "expected", "missing"],
        [
            param(
                # Generic test (list)
                {'target': ListModel},
                {
                    'char_field': "HELLO WORLD!",
                    'list_field': ["valA", "valB", "valC"]
                },
                None,
                id='basic_list'
            ),
            param(
                # Generic test (dict)
                {'target': DictModel},
                {
                    'int_field': 42,
                    'dict_field': {
                        "valA": 'A',
                        "valB": 2
                    }
                },
                None,
                id='basic_dict'
            ),
            param(
                # Respects meta fields (list)
                {'target': ListModel,
                 'meta_fields': ['char_field']},
                {
                    'char_field': "HELLO WORLD!"
                },
                {
                    'list_field': ["valA", "valB", "valC"]
                },
                id='meta_fields_list'
            ),
            param(
                # Respects meta fields (dict)
                {'target': DictModel,
                 'meta_fields': ['int_field']},
                {
                    'int_field': 42,
                },
                {
                    'dict_field': {
                        "valA": 'A',
                        "valB": 2
                    }
                },
                id='meta_fields_dict'
            ),
            param(
                # Respects meta fields (list)
                {'target': ListModel,
                 'meta_exclude': ['char_field']},
                {
                    'list_field': ["valA", "valB", "valC"]
                },
                {
                    'char_field': "HELLO WORLD!"
                },
                id='meta_exclude_list'
            ),
            param(
                # Respects meta fields (dict)
                {'target': DictModel,
                 'meta_exclude': ['int_field']},
                {
                    'dict_field': {
                        "valA": 'A',
                        "valB": 2
                    }
                },
                {
                    'int_field': 42,
                },
                id='meta_exclude_dict'
            ),
        ])
    def test_retrieve(self, build_serializer, does_a_subset_b,
                      prepped_db, serializer, expected, missing):
        """Confirm that the serializer correctly retrieves data"""
        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(prepped_db[serializer['target']])

        # Make sure fields which should exist do
        does_a_subset_b(expected, serializer.data)

        # Make sure fields which should be ignored are
        if missing:
            with raises(AssertionError):
                does_a_subset_b(missing, serializer.data)

    @mark.parametrize(
        ["initial", "serializer", "expected"],
        [
            param(
                # Basic test, list
                {'char_field': "NEW WORLD!",
                 'list_field': ["A", "B", "C"]},
                {'target': ListModel},
                {'char_field': "NEW WORLD!",
                 'list_field': ["A", "B", "C"]},
                id='basic_list'
            ),
            param(
                # Basic test, dict
                {'int_field': 34,
                 'dict_field': {
                     "valA": "A",
                     "valB": 22,
                     "valC": 3.1415
                 }},
                {'target': DictModel},
                {'int_field': 34,
                 'dict_field': {
                     "valA": "A",
                     "valB": 22,
                     "valC": 3.1415
                 }},
                id='basic_dict'
            ),
            param(
                # Custom field, list
                {'char_field': "NEW WORLD!"},
                {'target': ListModel,
                 'custom_fields': {
                     'list_field': drf_fields.ListField(default=["D", "E"])
                 }},
                {'char_field': "NEW WORLD!",
                 'list_field': ["D", "E"]},
                id='custom_field_list'
            ),
            param(
                # Custom field, dict
                {'int_field': 9,
                 'dict_field': {
                     "valA": "A",
                     "valB": 22,
                     "valC": 3.1415
                 }},
                {'target': DictModel,
                 'custom_fields': {
                     'int_field': drf_fields.IntegerField(max_value=10)
                 }},
                {'int_field': 9,
                 'dict_field': {
                     "valA": "A",
                     "valB": 22,
                     "valC": 3.1415
                 }},
                id='custom_field_dict'
            ),
        ])
    def test_valid_create(self, build_serializer, instance_matches_data,
                          initial, serializer, expected):
        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(data=initial)

        # Confirm that input data is valid
        assert serializer.is_valid(), serializer.errors

        # Make sure the serializer can save the data
        instance = serializer.save()

        # Confirm that the data was saved correctly
        instance_matches_data(instance, expected)

    @mark.parametrize(
        ["initial", "serializer", "error"],
        [
            param(
                # Missing values are caught (list)
                {'char_field': "TEST"},
                {'target': ListModel},
                AssertionError,
                id='missing_input_list'
            ),
            param(
                # Missing values are caught (dict)
                {'int_field': 132},
                {'target': DictModel},
                AssertionError,
                id='missing_input_dict'
            ),
            param(
                # Incorrectly typed values are caught (list)
                {'char_field': "TEST",
                 'list_field': "NOT_A_LIST"},
                {'target': ListModel},
                AssertionError,
                id='wrong_input_list'
            ),
            param(
                # Incorrectly typed values are caught (dict)
                {'int_field': 1432,
                 'list_field': "NOT_A_DICT"},
                {'target': DictModel},
                AssertionError,
                id='wrong_input_dict'
            )
        ])
    def test_invalid_create(self, build_serializer, instance_matches_data,
                            initial, serializer, error):
        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(data=initial)

        # Confirm that the serializer throws the designated error
        with raises(error):
            assert serializer.is_valid(), serializer.errors

            serializer.save()

    @mark.parametrize(
        ["update", "serializer", "expected"],
        [
            param(
                # Generic test (list)
                {'char_field': "NEW WORD!",
                 'list_field': ["C", "D"]},
                {'target': ListModel},
                {'char_field': "NEW WORD!",
                 'list_field': ["C", "D"]},
                id='basic_list'
            ),
            param(
                # Generic test (dict)
                {'int_field': 56,
                 'dict_field': {
                     "newA": 123,
                     "newB": "NEW WORLD!"
                 }},
                {'target': DictModel},
                {'int_field': 56,
                 'dict_field': {
                     "newA": 123,
                     "newB": "NEW WORLD!"
                 }},
                id='basic_dict'
            ),
            param(
                # Meta `fields` enables pseudo-partial updates (list)
                {'list_field': ["C", "D"]},
                {'target': ListModel,
                 'meta_fields': ["list_field"]},
                {'char_field': "HELLO WORLD!",
                 'list_field': ["C", "D"]},
                id='meta_fields_list'
            ),
            param(
                # Meta `fields` enables pseudo-partial (dict)
                {'dict_field': {"C": "D"}},
                {'target': DictModel,
                 'meta_fields': ["dict_field"]},
                {'int_field': 42,
                 'dict_field': {"C": "D"}},
                id='meta_fields_dict'
            ),
            param(
                # Custom fields are used (list)
                {'list_field': ["C", "D"]},
                {'target': ListModel,
                 'custom_fields': {
                     "char_field": drf_fields.CharField(default="DEFAULT")}
                 },
                {'char_field': "DEFAULT",
                 'list_field': ["C", "D"]},
                id='custom_fields_list'
            ),
            param(
                # Custom fields are used (dict)
                {'dict_field': {"C": "D"}},
                {'target': DictModel,
                 'custom_fields': {
                     "int_field": drf_fields.IntegerField(default=999)}
                 },
                {'int_field': 999,
                 'dict_field': {"C": "D"}},
                id='custom_fields_dict'
            ),
        ])
    def test_valid_update(self, build_serializer, instance_matches_data,
                          prepped_db, update, serializer, expected):
        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(prepped_db[serializer['target']], data=update)

        # Confirm that serializer data is valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer can save the data
        instance = serializer.save()

        # Confirm that the update went as planned
        instance_matches_data(instance, expected)

    @mark.parametrize(
        ["update", "serializer", "error"],
        [
            param(
                # Partial update attempted (list)
                {'char_field': "VALID"},
                {'target': ListModel},
                AssertionError,
                id='missing_value_list'
            ),
            param(
                # Partial update attempted (dict)
                {'int_field': 14366},
                {'target': DictModel},
                AssertionError,
                id='missing_value_dict'
            ),
            param(
                # Data with invalid value caught (list)
                {'char_field': "VALID",
                 'list_field': {}},
                {'target': ListModel},
                AssertionError,
                id='invalid_value_list'
            ),
            param(
                # Data with invalid value caught (dict)
                {'int_field': 1964,
                 'dict_field': {1, 2}},
                {'target': DictModel},
                AssertionError,
                id='invalid_value_dict'
            ),
        ])
    def test_invalid_update(self, build_serializer, instance_matches_data,
                            prepped_db, update, serializer, error):
        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(prepped_db[serializer['target']], data=update)

        # Confirm that the serializer throws the designated error
        with raises(error):
            assert serializer.is_valid(), serializer.errors

            serializer.save()

    @mark.parametrize(
        ["update", "serializer", "expected"],
        [
            param(
                # Generic test (list)
                {'char_field': "NEW WORD!"},
                {'target': ListModel},
                {'char_field': "NEW WORD!",
                 'list_field': ["valA", "valB", "valC"]},
                id='basic_list'
            ),
            param(
                # Generic test (dict)
                {'int_field': 1469},
                {'target': DictModel},
                {'int_field': 1469,
                 'dict_field': {"valA": "A", "valB": 2}},
                id='basic_dict'
            ),
            param(
                # Defaults are ignored (list)
                {'char_field': "NEW WORD!"},
                {'target': ListModel,
                 'custom_fields': {
                    'list_field': drf_fields.ListField(default=["NOPE"])
                }},
                {'char_field': "NEW WORD!",
                 'list_field': ["valA", "valB", "valC"]},
                id='default_ignored_list'
            ),
            param(
                # Defaults are ignored (dict)
                {'int_field': 1469},
                {'target': DictModel,
                 'custom_fields': {
                     'dict_field': drf_fields.DictField(default={"val": "NOPE"})
                 }},
                {'int_field': 1469,
                 'dict_field': {"valA": "A", "valB": 2}},
                id='basic_dict'
            ),
        ])
    def test_valid_partial_update(self, build_serializer, instance_matches_data,
                                  prepped_db, update, serializer, expected):
        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(prepped_db[serializer['target']], data=update,
                                    partial=True)

        # Confirm that serializer data is valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer can save the data
        instance = serializer.save()

        # Confirm that the update went as planned
        instance_matches_data(instance, expected)

    @mark.parametrize(
        ["update", "serializer", "error"],
        [
            param(
                # Data w/ bad value caught
                {'list_field': "NOTALIST"},
                {'target': ListModel},
                AssertionError,
                id='wrong_type_list'
            ),
            param(
                # Data w/ bad value caught
                {'dict_field': "NOTADICT"},
                {'target': DictModel},
                AssertionError,
                id='wrong_type_dict'
            ),
        ])
    def test_invalid_partial_update(self, build_serializer, instance_matches_data,
                                    prepped_db, update, serializer, error):
        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(prepped_db[serializer['target']], data=update,
                                    partial=True)

        # Confirm that the serializer throws the designated error
        with raises(error):
            assert serializer.is_valid(), serializer.errors

            serializer.save()
