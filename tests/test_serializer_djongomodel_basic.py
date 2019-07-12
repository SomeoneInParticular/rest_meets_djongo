from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured
import rest_framework.fields as drf_fields
import rest_framework.serializers as drf_ser
import pytest

from rest_meets_djongo import fields as rmd_fields
from rest_meets_djongo import serializers as rmd_ser

from tests import models as test_models
from .utils import expect_dict_to_str


class TestMapping(TestCase):
    # --- Serializer construction tests --- #
    def test_basic_mapping(self):
        """
        Confirm that the serializer can still handle models w/o other
        embedded models as fields, w/o custom field selection

        (ObjectID is also tested here)
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

        expected_str = expect_dict_to_str(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        # String comparision prevents the fields being different (identical)
        # objects from now counting as the same
        assert expected_str == observed_str

    def test_embedded_model_mapping(self):
        """
        Confirm that the serializer handles embedded models as intended

        Test done without explicit embedded model serialization, and thus
        parses the EmbeddedModelField to a ReadOnlyFields. This is
        because it does not know how to handle creation without an
        explicit serializer
        """

        class ContainerSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ContainerModel
                fields = '__all__'

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'embed_field': drf_fields.ReadOnlyField()
        }

        expected_str = expect_dict_to_str(expected_dict)
        observed_str = str(ContainerSerializer().get_fields())

        assert expected_str == observed_str

    def test_respects_fields(self):
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ObjIDModel
                fields = ['int_field']

        expected_dict = {
            'int_field': drf_fields.IntegerField(max_value=2147483647,
                                                 min_value=-2147483648),
        }

        expected_str = expect_dict_to_str(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_respects_exclude(self):
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ObjIDModel
                exclude = ['int_field']

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'char_field': drf_fields.CharField(max_length=5),
        }

        expected_str = expect_dict_to_str(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_invalid_field_caught(self):
        """
        Confirm that field names not found in the model are caught
        with a configuration error
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
        Confirm the fields declared in a serializer that another serializer
        inherits from can be safely ignored
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
        Confirm the fields declared in a serializer that another serializer
        inherits from can be set to none to ignore it
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
            'float_field': drf_fields.FloatField(),
            'date_field': drf_fields.DateField()
        }

        expected_str = expect_dict_to_str(expected_dict)
        observed_str = str(ChildSerializer().get_fields())

        assert expected_str == observed_str


class TestIntegration(TestCase):
    # --- Serializer integration tests --- #
    def test_retrieve(self):
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
        # Initial (to-be-updated) instance instantiation
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


