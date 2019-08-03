from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured
import rest_framework.fields as drf_fields
import rest_framework.serializers as drf_ser
import pytest

from rest_meets_djongo import fields as rmd_fields
from rest_meets_djongo import serializers as rmd_ser

from tests import models as test_models
from tests.utilities import format_dict


class TestMapping(TestCase):
    def test_basic_with_object_id(self):
        """
        Confirm that the serializer can still handle models w/o other
        embedded models as fields. We also confirm that ObjectID fields
        can be managed here as well
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ObjIDModel
                fields = '__all__'

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'int_field': drf_fields.IntegerField(max_value=2147483647,
                                                 min_value=-2147483648),
            'char_field': drf_fields.CharField(max_length=5),
        }

        expected_str = format_dict(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        # String comparision prevents the fields being different (identical)
        # objects from now counting as the same
        assert expected_str == observed_str

    def test_field_options(self):
        """
        Confirm that new serializers will catch and correctly manage
        field options for its specified model
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.OptionsModel
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

        expected_str = format_dict(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_respects_fields(self):
        """
        Confirm that basic fields can still be ignored by not specifying
        them in the `fields` Meta parameter
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ObjIDModel
                fields = ['int_field']

        expected_dict = {
            'int_field': drf_fields.IntegerField(max_value=2147483647,
                                                 min_value=-2147483648),
        }

        expected_str = format_dict(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_respects_exclude(self):
        """
        Confirm that basic fields can still be ignored by specifying them
        in the `exclude` Meta parameter
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ObjIDModel
                exclude = ['int_field']

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'char_field': drf_fields.CharField(max_length=5),
        }

        expected_str = format_dict(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_invalid_field_caught(self):
        """
        Confirm that field names not found in the model are still
        caught with a configuration error
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.GenericModel
                fields = ['id', 'invalid']

        with pytest.raises(ImproperlyConfigured) as exc:
            fields = TestSerializer().fields

    def test_missing_field_caught(self):
        """
        Confirm that failing to include explicitly declared fields in
        the serializer will throw and error
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            missing = drf_ser.ReadOnlyField()

            class Meta:
                model = test_models.GenericModel
                fields = ['id']

        with pytest.raises(AssertionError) as exc:
            fields = TestSerializer().fields

    def test_missing_inherited_field_ignorable(self):
        """
        Confirm the fields declared in a serializer that another
        serializer inherits from can be safely ignored in child
        serializers
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            missing = drf_ser.ReadOnlyField()

            class Meta:
                model = test_models.GenericModel
                fields = '__all__'

        class ChildSerializer(TestSerializer):
            missing = drf_ser.ReadOnlyField()

            class Meta:
                model = test_models.GenericModel
                fields = ['id']

        fields = ChildSerializer().fields

    def test_inherited_field_nullable(self):
        """
        Confirm the fields declared in a serializer that another
        serializer inherits from can still be ignored by setting them to
        `None` in the child serializer
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            missing = drf_ser.ReadOnlyField()

            class Meta:
                model = test_models.GenericModel
                fields = '__all__'

        class ChildSerializer(TestSerializer):
            missing = None

            class Meta:
                model = test_models.GenericModel
                fields = '__all__'

        expected_dict = {
            'id': drf_fields.IntegerField(label='ID', read_only=True),
            'big_int': drf_fields.IntegerField(max_value=9223372036854775807,
                                               min_value=-9223372036854775808),
            'bool': drf_fields.BooleanField(),
            'char': ('CharField(validators='
                     '[<django.core.validators.MaxLengthValidator object>])'),
            'comma_int': ("CharField(validators="
                          "[<django.core.validators.RegexValidator object>, "
                          "<django.core.validators.MaxLengthValidator object>])"),
            'date': drf_fields.DateField(),
            'date_time': drf_fields.DateTimeField(),
            'decimal': drf_fields.DecimalField(max_digits=10, decimal_places=5),
            'email': drf_fields.EmailField(max_length=254),
            'float': drf_fields.FloatField(),
            'integer': drf_fields.IntegerField(max_value=2147483647,
                                               min_value=-2147483648),
            'null_bool': drf_fields.NullBooleanField(required=False),
            'pos_int': drf_fields.IntegerField(max_value=2147483647,
                                               min_value=0),
            'pos_small_int': drf_fields.IntegerField(max_value=32767,
                                                     min_value=0),
            'slug': drf_fields.SlugField(allow_unicode=False,
                                         max_length=50),
            'small_int': drf_fields.IntegerField(max_value=32767,
                                                 min_value=-32768),
            'text': drf_fields.CharField(style={'base_template': 'textarea.html'}),
            'time': drf_fields.TimeField(),
            'url': drf_fields.URLField(max_length=200),
            'ip': drf_fields.IPAddressField(),
            'uuid': ("ModelField(model_field="
                     "<django.db.models.fields.UUIDField: uuid>)"),
        }

        expected_str = format_dict(expected_dict)
        observed_str = str(ChildSerializer().get_fields())

        assert expected_str == observed_str


class TestIntegration(TestCase):
    def test_retrieve(self):
        """
        Confirm that existing instances of models with basic fields
        can still be retrieved and serialized correctly
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ObjIDModel
                fields = '__all__'

        data = {
            'int_field': 55,
            'char_field': 'BYEH'
        }

        instance = test_models.ObjIDModel.objects.create(**data)
        serializer = TestSerializer(instance)

        data.update({'_id': str(instance._id)})

        self.assertDictEqual(data, serializer.data)

    def test_create(self):
        """
        Confirm that new instances of models with basic fields can still
        be generated and saved correctly from raw data
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ObjIDModel
                fields = '__all__'

        data = {
            'int_field': 55,
            'char_field': 'Foo'
        }

        # Serializer should validate
        serializer = TestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        # Serializer should be able to save valid data correctly
        instance = serializer.save()
        assert instance.int_field == data['int_field']

    def test_update(self):
        """
        Confirm that existing instances of models with basic fields can
        still be updated when provided with new raw data
        """
        # Initial (to-be-updated) instance instantiation
        initial_data = {
            'int_field': 55,
            'char_field': 'Foo'
        }

        instance = test_models.ObjIDModel.objects.create(**initial_data)

        initial_data.update({'pk': instance.pk})

        # Try and perform a serializer based update
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ObjIDModel
                fields = '__all__'

        new_data = {
            'int_field': 1234,
            'char_field': 'Bar'
        }

        serializer = TestSerializer(instance, data=new_data)

        # Confirm that the partial update data is valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves this updated instance correctly
        serializer.save()
        assert instance.pk == initial_data['pk']
        assert instance.int_field == new_data['int_field']
        assert instance.char_field == new_data['char_field']

    def test_partial_update(self):
        """
        Confirm that existing instances of models with basic fields can
        still be updated when provided with new partial data
        """
        # Initial (to-be-updated) instance creation
        old_data = {
            'int_field': 55,
            'char_field': 'Foo'
        }

        instance = test_models.ObjIDModel.objects.create(**old_data)

        old_data.update({'pk': instance.pk})

        # Try and perform a serializer based update
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ObjIDModel
                fields = '__all__'

        new_data = {
            'int_field': 1234,
        }

        serializer = TestSerializer(instance, data=new_data, partial=True)

        # Confirm that the partial update data is valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves this correctly
        serializer.save()
        assert instance.pk == old_data['pk']
        assert instance.int_field == new_data['int_field']
        assert instance.char_field == old_data['char_field']

        # Confirm that the serializer did not lose data in the update
        expected_data = {
            '_id': str(instance._id),
            'int_field': instance.int_field,
            'char_field': instance.char_field
        }

        self.assertDictEqual(serializer.data, expected_data)

