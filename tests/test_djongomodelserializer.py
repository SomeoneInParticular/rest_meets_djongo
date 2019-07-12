from bson import ObjectId
from collections import OrderedDict

from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured
import rest_framework.fields as drf_fields
import rest_framework.serializers as drf_ser
import pytest

from rest_meets_djongo import fields as rmd_fields
from rest_meets_djongo import serializers as rmd_ser

from tests import models as test_models


class TestDjongoModelSerializerConstruction(TestCase):
    # --- Serializer construction tests --- #
    def test_basic_model_serializer(self):
        """
        Confirm that the serializer can still handle models w/o other
        embedded models as fields, w/o custom field selection

        (ObjectID is also tested here)
        """
        class ObjIDModelSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ObjIDModel
                fields = '__all__'

        info_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'int_field': drf_fields.IntegerField(max_value=2147483647,
                                                 min_value=-2147483648),
            'char_field': drf_fields.CharField(max_length=5),
        }

        field_dict = ObjIDModelSerializer().get_fields()

        # String comparision prevents the fields being different (identical)
        # objects from now counting as the same
        assert str(info_dict) == str(field_dict)

    def test_fwd_relation_model_serializer(self):
        """
        Confirm that the serializer still handles models which have
        relations to other models, w/o custom field selection
        """
        class RelModelSerializer(rmd_ser.DjongoModelSerializer):
            # Explicit field mapping, as should be done by DRF
            fk_field = drf_ser.PrimaryKeyRelatedField(
                queryset=test_models.GenericModel.objects.all(),
                allow_null=True
            )
            mfk_field = drf_ser.StringRelatedField()

            class Meta:
                model = test_models.RelationContainerModel
                fields = '__all__'

        info_dict = {
            'id': drf_fields.IntegerField(label='ID', read_only=True),
            'fk_field': drf_ser.PrimaryKeyRelatedField(
                queryset=test_models.GenericModel.objects.all(),
                allow_null=True
            ),
            'mfk_field': drf_ser.StringRelatedField(),
        }

        field_dict = RelModelSerializer().get_fields()

        assert str(info_dict) == str(field_dict)

    def test_rvs_relation_model_serializer(self):
        class RVSRelModelSerializer(rmd_ser.DjongoModelSerializer):

            class Meta:
                model = test_models.ReverseRelatedModel
                fields = '__all__'

        info_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            # Reverse models are excluded by default (as they are difficult
            # to predict how they should be parsed)
        }

        field_dict = RVSRelModelSerializer().get_fields()

        assert str(info_dict) == str(field_dict)

    def test_non_serial_embed_model_serializer(self):
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

        info_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'embed_field': drf_fields.ReadOnlyField()
        }

        field_dict = ContainerSerializer().get_fields()

        assert str(info_dict) == str(field_dict)

    def test_serializer_respects_fields(self):
        class ObjIDModelSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ObjIDModel
                fields = ['int_field']

        info_dict = {
            'int_field': drf_fields.IntegerField(max_value=2147483647,
                                                 min_value=-2147483648),
        }

        field_dict = ObjIDModelSerializer().get_fields()

        assert str(info_dict) == str(field_dict)

    def test_serializer_respects_exclude(self):
        class ObjIDModelSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ObjIDModel
                exclude = ['int_field']

        info_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'char_field': drf_fields.CharField(max_length=5),
        }

        field_dict = ObjIDModelSerializer().get_fields()

        assert str(info_dict) == str(field_dict)

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
            TestSerializer().fields

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
            TestSerializer().fields

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

        ChildSerializer().fields

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

        expect_dict = {
            'id': drf_fields.IntegerField(label='ID', read_only=True),
            'float_field': drf_fields.FloatField(),
            'date_field': drf_fields.DateField()
        }

        assert str(expect_dict) == str(ChildSerializer().fields)


class TestDjongoModelSerializerIntegration(TestCase):
    # --- Serializer serialization tests --- #
    def test_basic_retrieve(self):
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

    def test_relation_retrieve_base(self):
        # Set up the referenced model instances in the database
        generic_model_instance = test_models.GenericModel.objects.create(
            float_field=0.12345,
            date_field='1997-01-01'
        )

        mtm_model_instance = test_models.ReverseRelatedModel.objects.create(
            _id=ObjectId()
        )

        # Create the serializer instance
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.RelationContainerModel
                fields = '__all__'
                depth = 0

        instance = test_models.RelationContainerModel.objects.create(
            fk_field=generic_model_instance,
            # Many-to-Many fields cannot be set at creation; see below
        )

        instance.mfk_field.add(mtm_model_instance)

        serializer = TestSerializer(instance)

        expect_data = {
            'id': instance.pk,
            'fk_field': generic_model_instance.pk,
            'mfk_field': [mtm_model_instance._id]  # References via list of pk
        }

        self.assertDictEqual(expect_data, serializer.data)

    def test_relation_retrieve_deep(self):
        # Set up the referenced model instances in the database
        generic_model_data = {
            'float_field': 0.12345,
            'date_field': '1997-01-01'
        }

        generic_model_instance = test_models.GenericModel.objects.create(
            **generic_model_data
        )

        generic_model_data.update({'id': generic_model_instance.pk})

        mtm_model_data = {
            '_id': str(ObjectId())
        }

        mtm_model_instance = test_models.ReverseRelatedModel.objects.create(
            **mtm_model_data
        )

        # Create the instance to serializer
        instance = test_models.RelationContainerModel.objects.create(
            fk_field=generic_model_instance,
            # Many-to-Many fields cannot be set at creation; see below
        )

        instance.mfk_field.add(mtm_model_instance)

        # Create the serializer and serialize our instance
        class RelModelSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.RelationContainerModel
                fields = '__all__'
                depth = 1

        serializer = RelModelSerializer(instance)

        # Confirm the data was serialized as expected
        expect_data = {
            'id': instance.pk,
            'fk_field': generic_model_data,
            'mfk_field': [mtm_model_data]
        }

        self.assertDictEqual(expect_data, serializer.data)

    def test_basic_create(self):
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

    def test_relation_create(self):
        # Set up the referenced model instances in the database
        generic_model_data = {
            'float_field': 0.12345,
            'date_field': '1997-01-01'
        }

        generic_model_instance = test_models.GenericModel.objects.create(
            **generic_model_data
        )

        generic_model_data.update({'id': generic_model_instance.pk})

        # Create the serializer and the data it should use to create an object
        class RelModelSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.RelationContainerModel
                fields = '__all__'

        data = {
            'fk_field': generic_model_instance.pk,
            # Directly setting Many-to-Many fields is prohibited
            #  we test this field later, in test_relation_update
        }

        # Confirm that the serializer sees valid data as valid
        serializer = RelModelSerializer(data=data)
        assert serializer.is_valid()

        # Confirm that this data can be saved
        instance = serializer.save()
        assert instance.fk_field.pk == generic_model_instance.pk
        assert instance.fk_field.float_field == generic_model_data['float_field']

    def test_basic_update(self):
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

    def test_relation_update(self):
        # Set up the referenced model instances in the database
        generic_model_instance = test_models.GenericModel.objects.create(
            float_field=0.12345,
            date_field='1997-01-01'
        )

        ref_pk = generic_model_instance.pk

        mtm_model_instance = test_models.ReverseRelatedModel.objects.create(
            _id=ObjectId()
        )

        # Create the initial, to be updated, instance
        instance = test_models.RelationContainerModel.objects.create(
            fk_field=generic_model_instance
        )

        instance.mfk_field.add(mtm_model_instance)

        instance_pk = instance.pk

        # Try to perform an instance update
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.RelationContainerModel
                fields = '__all__'

        new_generic_instance = test_models.GenericModel.objects.create(
            float_field=3.141392,
            date_field='2019-06-11'
        )

        new_generic_instance.save()

        new_data = {
            'fk_field': new_generic_instance.pk,
            # By default, Many-toMany fields cannot be updated via serializer
            #   this may change in the future
        }

        serializer = TestSerializer(instance, data=new_data, partial=True)

        # Serializer should be valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves this correctly
        serializer.save()
        assert instance.pk == instance_pk
        assert instance.fk_field.pk == new_generic_instance.pk
        assert [e.pk for e in instance.mfk_field.all()] == [mtm_model_instance.pk]


