from bson import ObjectId

from django.test import TestCase
import rest_framework.fields as drf_fields
import rest_framework.serializers as drf_ser

from rest_meets_djongo import fields as rmd_fields
from rest_meets_djongo import serializers as rmd_ser

from tests import models as test_models
from .utils import expect_dict_to_str


class TestMapping(TestCase):
    # --- Serializer construction tests --- #
    def test_fwd_relation_mapping(self):
        """
        Confirm that the serializer still handles models which have
        relations to other models, w/o custom field selection
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            # DRF usually expects explicit field declaration:
            # Just to check, however, we'll try auto-building the fields

            class Meta:
                model = test_models.RelationContainerModel
                fields = '__all__'

        expected_dict = {
            'id': drf_fields.IntegerField(label='ID', read_only=True),
            'fk_field': 'PrimaryKeyRelatedField(queryset=GenericModel.objects.all())',
            'mfk_field': ('ManyRelatedField(child_relation='
                          'PrimaryKeyRelatedField(queryset='
                          'ReverseRelatedModel.objects.all(), '
                          'required=False), '
                          'required=False)'),
        }

        expect_str = expect_dict_to_str(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expect_str == observed_str

    def test_rvs_relation_mapping(self):
        class TestSerializer(rmd_ser.DjongoModelSerializer):

            class Meta:
                model = test_models.ReverseRelatedModel
                fields = '__all__'

        expect_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            # Reverse models are excluded by default (as they are difficult
            # to predict how they should be parsed)
        }

        expected_str = expect_dict_to_str(expect_dict)

        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_respects_fields(self):
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.RelationContainerModel
                fields = ['fk_field']

        expected_dict = {
            'fk_field': 'PrimaryKeyRelatedField(queryset=GenericModel.objects.all())',
        }

        expected_str = expect_dict_to_str(expected_dict)

        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_respects_exclude(self):
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.RelationContainerModel
                exclude = ['fk_field']

        expected_dict = {
            'id': drf_fields.IntegerField(label='ID', read_only=True),
            'mfk_field': ('ManyRelatedField(child_relation='
                          'PrimaryKeyRelatedField(queryset='
                          'ReverseRelatedModel.objects.all(), '
                          'required=False), '
                          'required=False)'),
        }

        expected_str = expect_dict_to_str(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str


class TestIntegration(TestCase):
    # --- Serializer integration tests --- #
    def test_retrieve_root(self):
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

    def test_retrieve_deep(self):
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

    def test_create(self):
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

    def test_update(self):
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
            #   this may change in the future (they're read only)
        }

        serializer = TestSerializer(instance, data=new_data, partial=True)

        # Serializer should be valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves this correctly
        serializer.save()
        assert instance.pk == instance_pk
        assert instance.fk_field.pk == new_generic_instance.pk
        assert [e.pk for e in instance.mfk_field.all()] == [mtm_model_instance.pk]
