from collections import namedtuple

from django.core.exceptions import ImproperlyConfigured
import rest_framework.fields as drf_fields
from rest_framework.serializers import (
    BooleanField, CharField, ReadOnlyField, SerializerMethodField
)

from rest_meets_djongo import fields as rmd_fields
from rest_meets_djongo.serializers import DjongoModelSerializer

from tests.models import GenericModel, ObjIDModel, OptionsModel

from pytest import fixture, mark, param, raises


@mark.basic
@mark.core
@mark.serializer
class TestMapping(object):
    def test_basic_mapping(self, assert_dict_equals):
        """
        Confirm that the serializer can still handle models w/
        standard Django fields
        """
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = GenericModel
                fields = '__all__'

        expected_dict = {
            'id': drf_fields.IntegerField(label='ID', read_only=True),
            'big_int': drf_fields.IntegerField(
                max_value=9223372036854775807,
                min_value=-9223372036854775808
            ),
            'bool': drf_fields.BooleanField(),
            'char': drf_fields.CharField(max_length=20),
            'comma_int': (
                "CharField(validators=[<django.core.validators.RegexValidator "
                "object>, <django.core.validators.MaxLengthValidator object>])"
            ),
            'date': drf_fields.DateField(),
            'date_time': drf_fields.DateTimeField(),
            'decimal': drf_fields.DecimalField(
                decimal_places=5,
                max_digits=10
            ),
            'email': drf_fields.EmailField(
                max_length=254
            ),
            'float': drf_fields.FloatField(),
            'integer': drf_fields.IntegerField(
                max_value=2147483647,
                min_value=-2147483648
            ),
            'null_bool': drf_fields.NullBooleanField(required=False),
            'pos_int': drf_fields.IntegerField(
                max_value=2147483647,
                min_value=0
            ),
            'pos_small_int': drf_fields.IntegerField(
                max_value=32767,
                min_value=0
            ),
            'slug': drf_fields.SlugField(
                allow_unicode=False,
                max_length=50
            ),
            'small_int': drf_fields.IntegerField(
                max_value=32767,
                min_value=-32768
            ),
            'text': "CharField(style={'base_template': 'textarea.html'})",
            'time': drf_fields.TimeField(),
            'url': drf_fields.URLField(max_length=200),
            'ip': drf_fields.IPAddressField(),
            'uuid': "ModelField(model_field=<django.db.models.fields.UUIDField: uuid>)",
        }

        assert_dict_equals(TestSerializer().get_fields(), expected_dict)

    def test_options_mapping(self, assert_dict_equals):
        """
        Confirm that new serializers will catch and correctly manage
        field options for its specified model, for non-embedded models
        """
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = OptionsModel
                fields = '__all__'

        expected_dict = {
            # Primary keys should be made read-only, with the db column being
            # ignored entirely
            "db_column_id": rmd_fields.ObjectIdField(read_only=True),
            # Nullable and blank values should have required=False appended.
            # The prior requires a unique validator as well, the text requires
            # templates
            "null_char": ("CharField(allow_null=True, "
                          "required=False, "
                          "validators=[<django.core.validators.MaxLengthValidator object>])"),
            "blank_char": drf_fields.CharField(allow_blank=True, required=False,
                                               style={'base_template': 'textarea.html'}),
            # Fields with choices should be coerced into that form of field
            "choice_char": "ChoiceField(choices=['Foo', 'Bar', 'Baz'], "
                           "validators=[<django.core.validators.MaxLengthValidator object>])",
            # Defaults are handled by Django, not DRF, so the argument should
            # be stripped implicitly (though it still is in use during save!)
            # This will set required=False, however
            "default_email": drf_fields.EmailField(max_length=254,
                                                   required=False),
            # Read only fields should be marked as such
            "read_only_int": drf_fields.IntegerField(read_only=True),
            # Errors, by default, should be distinct between DRF and Djongo;
            # Therefore, it should be stripped unless explicitly set in the
            # serializer by the user
            "custom_error": drf_fields.IntegerField(max_value=2147483647,
                                                    min_value=-2147483648),
            # Help text should be conserved
            "help_char": ("CharField(help_text='Super helpful text', "
                          "validators=[<django.core.validators.MaxLengthValidator object>])"),
            # Fields designated as unique should have a validator stating
            # such added
            "unique_int": ("IntegerField(max_value=2147483647, "
                           "min_value=-2147483648, "
                           "validators=[<UniqueValidator(queryset=OptionsModel.objects.all())>])"),
        }

        assert_dict_equals(TestSerializer().get_fields(), expected_dict)

    def test_respects_fields(self, assert_dict_equals):
        """
        Confirm that basic fields can still be ignored by not specifying
        them in the `fields` Meta parameter
        """
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = ObjIDModel
                fields = ['int_field']

        expected_dict = {
            'int_field': drf_fields.IntegerField(max_value=2147483647,
                                                 min_value=-2147483648),
        }

        assert_dict_equals(TestSerializer().get_fields(), expected_dict)

    def test_respects_exclude(self, assert_dict_equals):
        """
        Confirm that basic fields can still be ignored by specifying them
        in the `exclude` Meta parameter
        """
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = ObjIDModel
                exclude = ['int_field']

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'char_field': drf_fields.CharField(max_length=5),
        }

        assert_dict_equals(TestSerializer().get_fields(), expected_dict)

    @mark.error
    def test_invalid_field_caught(self):
        """
        Confirm that field names not found in the model are still
        caught with a configuration error
        """
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = ObjIDModel
                fields = ['id', 'invalid']

        with raises(ImproperlyConfigured):
            fields_vals = TestSerializer().get_fields()
            print(fields_vals)

    @mark.error
    def test_missing_field_caught(self):
        """
        Confirm that failing to include explicitly declared fields in
        the serializer will throw an error
        """
        class TestSerializer(DjongoModelSerializer):
            missing = ReadOnlyField()  # Should be declared

            class Meta:
                model = ObjIDModel
                fields = ['id']

        with raises(AssertionError):
            field_vals = TestSerializer().get_fields()
            print(field_vals)

    @mark.error
    def test_missing_inherited_field_ignorable(self, assert_dict_equals):
        """
        Confirm the fields declared in a serializer that another
        serializer inherits from can be safely ignored in child
        serializers
        """
        class TestSerializer(DjongoModelSerializer):
            missing = ReadOnlyField()

            class Meta:
                model = ObjIDModel
                fields = '__all__'

        class ChildSerializer(TestSerializer):
            class Meta(TestSerializer.Meta):
                fields = ['_id']

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
        }

        assert_dict_equals(ChildSerializer().get_fields(), expected_dict)

    @mark.error
    def test_inherited_field_nullable(self, assert_dict_equals):
        """
        Confirm the fields declared in a serializer that another
        serializer inherits from can still be ignored by setting them to
        `None` in the child serializer
        """
        class TestSerializer(DjongoModelSerializer):
            missing = ReadOnlyField()

            class Meta:
                model = ObjIDModel
                fields = '__all__'

        class ChildSerializer(TestSerializer):
            missing = None

            class Meta(TestSerializer.Meta):
                pass

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'int_field': drf_fields.IntegerField(max_value=2147483647,
                                                 min_value=-2147483648),
            'char_field': drf_fields.CharField(max_length=5),
        }

        assert_dict_equals(ChildSerializer().get_fields(), expected_dict)


@mark.basic
@mark.core
@mark.integration
@mark.serializer
@mark.django_db
class TestIntegration(object):
    # -- Fixtures -- #
    @fixture
    def prepped_db(self):
        obj_data = {'int_field': 55, 'char_field': 'Foo'}

        obj_instance = ObjIDModel.objects.create(**obj_data)

        db_tuple = namedtuple('DBTuple', ['object_id'])

        return db_tuple(obj_instance)

    # -- Tests -- #
    @mark.parametrize(
        ["serializer", "expected", "missing"],
        [
            param(
                # Generic test
                {'target': ObjIDModel},
                {'int_field': 55, 'char_field': 'Foo'},
                None,
                id='basic'
            ),
            param(
                # Serializer w/ specified field list
                {'target': ObjIDModel, 'meta_fields': ['int_field']},
                {'int_field': 55},
                {'char_field': 'Foo'},
                id='respects_fields'
            ),
            param(
                # Serializer w/ specified excluded field
                {'target': ObjIDModel, 'meta_exclude': ['int_field']},
                {'char_field': 'Foo'},
                {'int_field': 55},
                id='respects_exclude'
            ),
            param(
                # Serializer w/ custom user field
                {'target': ObjIDModel, 'custom_fields': {
                    'str_rep': SerializerMethodField(),
                }, 'custom_methods': {
                    'get_str_rep':
                        (lambda self, obj: f"({obj.int_field}, {obj.char_field})"),
                }},
                {'int_field': 55, 'char_field': 'Foo',
                 'str_rep': '(55, Foo)'},
                None,
                id='custom_field'
            ),
        ])
    def test_retrieve(self, build_serializer, does_a_subset_b,
                      prepped_db, serializer, expected, missing):
        """Confirm that the serializer correctly retrieves data"""
        # Prepare the test environment
        TestSerializer = build_serializer(**serializer)
        serializer = TestSerializer(prepped_db.object_id)

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
                # Generic test
                {'int_field': 55, 'char_field': 'Foo'},
                {'target': ObjIDModel},
                {'int_field': 55, 'char_field': 'Foo'},
                id='basic'
            ),
            param(
                # Confirm that the user can override field functions
                {'int_field': 55},
                {'target': ObjIDModel, 'custom_fields': {
                    'char_field':
                        CharField(default='Bar', max_length=3)
                }},
                {'int_field': 55, 'char_field': 'Bar'},
                id='user_override'
            ),
        ])
    def test_valid_create(self, build_serializer, instance_matches_data,
                          initial, serializer, expected):
        # Prepare the test environment
        TestSerializer = build_serializer(**serializer)
        serializer = TestSerializer(data=initial)

        # Confirm that input data is valid
        assert serializer.is_valid(), serializer.errors

        # Make sure the serializer can save the data
        instance = serializer.save()

        # Confirm that data was saved correctly
        instance_matches_data(instance, expected)

    @mark.parametrize(
        ["initial", "serializer", "error"],
        [
            param(
                # Missing values are caught
                {'int_field': 55},
                {'target': ObjIDModel},
                AssertionError,
                id='missing_input'
            ),
            param(
                # Incorrectly typed values are caught
                {'int_field': 55, 'char_field': True},
                {'target': ObjIDModel},
                AssertionError,
                id='bad_input_type'
            ),
            param(
                # Missing custom values are caught
                {'int_field': 55, 'char_field': 'Bar'},
                {'target': ObjIDModel, 'custom_fields': {
                    'bool_field': BooleanField()
                }},
                AssertionError,
                id='missing_custom_field'
            ),
            param(
                # Custom fields w/o a corresponding model field are caught
                {'int_field': 55, 'char_field': 'Foo', 'bool_field': True},
                {'target': ObjIDModel, 'custom_fields': {
                    'bool_field': BooleanField()
                }},
                TypeError,
                id='bad_custom_field'
            ),
            param(
                # Validation error caught
                {'int_field': 55, 'char_field': 'Foo-Bar'},
                {'target': ObjIDModel},
                AssertionError,
                id='invalid_value'
            ),
        ])
    def test_invalid_create(self, build_serializer, instance_matches_data,
                            initial, serializer, error):
        # Prepare the test environment
        TestSerializer = build_serializer(**serializer)
        serializer = TestSerializer(data=initial)

        # Confirm that the serializer throws the designated error
        with raises(error):
            assert serializer.is_valid(), serializer.errors

            serializer.save()

    @mark.parametrize(
        ["update", "serializer", "expected"],
        [
            param(
                # Generic test
                {'int_field': 45, 'char_field': 'Bar'},
                {'target': ObjIDModel},
                {'int_field': 45, 'char_field': 'Bar'},
                id='basic'
            ),
            param(
                # Meta `fields` functions (allows pseudo-partial updates)
                {'int_field': 45},
                {'target': ObjIDModel, 'meta_fields': ['int_field']},
                {'int_field': 45, 'char_field': 'Foo'},
                id='respects_fields'
            ),
            param(
                # Meta `exclude` functions (allows pseudo-partial updates)
                {'char_field': 'Bar'},
                {'target': ObjIDModel, 'meta_exclude': ['int_field']},
                {'int_field': 55, 'char_field': 'Bar'},
                id='respects_exclude'
            ),
            param(
                # Custom field setups are applied
                {'int_field': 45},
                {'target': ObjIDModel, 'custom_fields': {
                    'char_field': CharField(default='Bar', max_length=3)
                }},
                {'int_field': 45, 'char_field': 'Bar'},
                id='custom_field'
            ),
        ])
    def test_valid_update(self, build_serializer, instance_matches_data,
                          prepped_db, update, serializer, expected):
        # Prepare the test environment
        TestSerializer = build_serializer(**serializer)
        serializer = TestSerializer(prepped_db.object_id, data=update)

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
                # Partial update attempted
                {'int_field': 45},
                {'target': ObjIDModel},
                AssertionError,
                id='missing_value'
            ),
            param(
                # Data w/ bad value caught
                {'int_field': 45, 'char_field': True},
                {'target': ObjIDModel},
                AssertionError,
                id='wrong_type'
            ),
            param(
                # Validation error caught
                {'int_field': 45, 'char_field': 'Foo-Bar'},
                {'target': ObjIDModel},
                AssertionError,
                id='invalid_value'
            ),
        ])
    def test_invalid_update(self, build_serializer, instance_matches_data,
                            prepped_db, update, serializer, error):
        # Prepare the test environment
        TestSerializer = build_serializer(**serializer)
        serializer = TestSerializer(prepped_db.object_id, data=update)

        # Confirm that the serializer throws the designated error
        with raises(error):
            assert serializer.is_valid(), serializer.errors

            serializer.save()

    @mark.parametrize(
        ["update", "serializer", "expected"],
        [
            param(
                # Generic test
                {'char_field': 'Bar'},
                {'target': ObjIDModel},
                {'int_field': 55, 'char_field': 'Bar'},
                id='basic'
            ),
            param(
                # Defaults should be ignored during partial updates
                {'int_field': 45},
                {'target': ObjIDModel, 'custom_fields': {
                    'char_field': CharField(default='Bar', max_length=3)
                }},
                {'int_field': 45, 'char_field': 'Foo'},
                id='default_ignored'
            )
        ])
    def test_valid_partial_update(self, build_serializer, instance_matches_data,
                                  prepped_db, update, serializer, expected):
        # Prepare the test environment
        TestSerializer = build_serializer(**serializer)
        serializer = TestSerializer(prepped_db.object_id, data=update,
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
                {'char_field': True},
                {'target': ObjIDModel},
                AssertionError,
                id='wrong_type'
            ),
            param(
                # Validation error caught
                {'char_field': 'Foo-Bar'},
                {'target': ObjIDModel},
                AssertionError,
                id='invalid_value'
            ),
        ])
    def test_invalid_partial_update(self, build_serializer, instance_matches_data,
                                    prepped_db, update, serializer, error):
        # Prepare the test environment
        TestSerializer = build_serializer(**serializer)
        serializer = TestSerializer(prepped_db.object_id, data=update,
                                    partial=True)

        # Confirm that the serializer throws the designated error
        with raises(error):
            assert serializer.is_valid(), serializer.errors

            serializer.save()