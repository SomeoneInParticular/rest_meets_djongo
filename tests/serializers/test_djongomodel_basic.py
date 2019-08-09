from django.core.exceptions import ImproperlyConfigured
import rest_framework.fields as drf_fields
import rest_framework.serializers as drf_ser
import pytest

from rest_meets_djongo import fields as rmd_fields
from rest_meets_djongo import serializers as rmd_ser

from tests.models import GenericModel, ObjIDModel, OptionsModel

from pytest import fixture, mark


@mark.basic
@mark.core
@mark.serializer
class TestMapping(object):
    def test_basic_mapping(self, assert_dict_equals):
        """
        Confirm that the serializer can still handle models w/
        standard Django fields
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
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
            'char': "CharField(validators=[<django.core.validators.MaxLengthValidator object>])",
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
        class TestSerializer(rmd_ser.DjongoModelSerializer):
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
        class TestSerializer(rmd_ser.DjongoModelSerializer):
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
        class TestSerializer(rmd_ser.DjongoModelSerializer):
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
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = ObjIDModel
                fields = ['id', 'invalid']

        with pytest.raises(ImproperlyConfigured):
            fields_vals = TestSerializer().get_fields()
            print(fields_vals)

    @mark.error
    def test_missing_field_caught(self):
        """
        Confirm that failing to include explicitly declared fields in
        the serializer will throw an error
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            missing = drf_ser.ReadOnlyField()  # Should be declared

            class Meta:
                model = ObjIDModel
                fields = ['id']

        with pytest.raises(AssertionError):
            field_vals = TestSerializer().get_fields()
            print(field_vals)

    @mark.error
    def test_missing_inherited_field_ignorable(self, assert_dict_equals):
        """
        Confirm the fields declared in a serializer that another
        serializer inherits from can be safely ignored in child
        serializers
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            missing = drf_ser.ReadOnlyField()

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
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            missing = drf_ser.ReadOnlyField()

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
    # Valid, generic data for the ObjectId model
    generic_data = {
        'int_field': 55,
        'char_field': 'Foo'
    }

    @fixture(scope='function')
    def initial_instance(self):
        instance = ObjIDModel.objects.create(**self.generic_data)
        return instance

    def test_retrieve(self, assert_dict_equals, initial_instance):
        """
        Confirm that existing instances of models with basic fields
        can still be retrieved and serialized correctly
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = ObjIDModel
                fields = '__all__'

        serializer = TestSerializer(initial_instance)

        new_data = {'_id': str(initial_instance.pk)}
        new_data.update(self.generic_data.copy())

        assert_dict_equals(new_data, serializer.data)

    def test_create(self, instance_matches_data):
        """
        Confirm that new instances of models with basic fields can still
        be generated and saved correctly from raw data
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = ObjIDModel
                fields = '__all__'

        # Serializer should validate
        serializer = TestSerializer(data=self.generic_data)
        assert serializer.is_valid(), serializer.errors

        # Serializer should be able to save valid data correctly
        instance = serializer.save()

        # Confirm that the instance contains the correct data
        assert instance_matches_data(instance, self.generic_data)

    def test_update(self, instance_matches_data, initial_instance):
        """
        Confirm that existing instances of models with basic fields can
        still be updated when provided with new raw data
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = ObjIDModel
                fields = '__all__'

        new_data = {
            'int_field': 1234,
            'char_field': 'Bar'
        }

        serializer = TestSerializer(initial_instance, data=new_data)

        # Confirm that the partial update data is valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves this updated instance correctly
        serializer.save()
        # Add the pk field to make sure a new instance wasn't created
        new_data.update({'_id': initial_instance.pk})

        # Confirm that the instance contains the correct data
        assert instance_matches_data(initial_instance, new_data)

    def test_partial_update(self, instance_matches_data, initial_instance):
        """
        Confirm that existing instances of models with basic fields can
        still be updated when provided with new partial data
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = ObjIDModel
                fields = '__all__'

        partial_data = {
            'int_field': 1234,
        }

        serializer = TestSerializer(initial_instance, data=partial_data, partial=True)

        # Confirm that the partial update data is valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves this correctly
        new_instance = serializer.save()

        # Confirm that only specified values were changed
        new_data = {'_id': initial_instance.pk}
        new_data.update(self.generic_data)
        new_data.update(partial_data)

        assert instance_matches_data(new_instance, new_data)
