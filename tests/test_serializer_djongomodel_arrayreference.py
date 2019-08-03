from bson import ObjectId
from collections import OrderedDict

from django.test import TestCase
from rest_framework import serializers as drf_ser

from rest_meets_djongo import serializers as rmd_ser

from .models import ArrayRelatedModel, ArrayRelationModel
from .utils import format_dict, object_id_to_serial_string


class TestIntegration(TestCase):
    def test_root_retrieve(self):
        """
        Confirm that existing instances of models w/ ArrayModelFields can
        still be retrieved and serialized correctly
        """
        # Set up the initial data
        rel_data_1 = {
            'email': 'jojo@gmail.com'
        }

        rel_instance_1 = ArrayRelatedModel.objects.create(**rel_data_1)

        rel_data_1.update({'pk': rel_instance_1.pk})

        rel_data_2 = {
            'email': 'gogo@gmail.com'
        }

        rel_instance_2 = ArrayRelatedModel.objects.create(**rel_data_2)

        rel_data_2.update({'pk': rel_instance_2.pk})

        rel_list = [rel_instance_1, rel_instance_2]

        instance = ArrayRelationModel.objects.create()
        instance.arr_relation.add(*rel_list)

        # Attempt to serialize an instance of the model using the data above
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = ArrayRelationModel
                fields = '__all__'

        serializer = TestSerializer(instance)

        # Compare observed serialization to what we would expect
        expected_data = {
            '_id': str(instance._id),
            'int_val': instance.int_val,
            'arr_relation': [
                rel_data_1['pk'],
                rel_data_2['pk']
            ]
        }

        self.assertDictEqual(expected_data, serializer.data)

    def test_deep_retrieve(self):
        """
        Confirm that existing instances of models w/ ArrayModelFields can
        still be retrieved and serialized correctly
        """
        # Set up the initial data
        rel_data_1 = {
            'email': 'jojo@gmail.com'
        }

        rel_instance_1 = ArrayRelatedModel.objects.create(**rel_data_1)

        rel_data_2 = {
            'email': 'gogo@gmail.com'
        }

        rel_instance_2 = ArrayRelatedModel.objects.create(**rel_data_2)

        rel_list = [rel_instance_1, rel_instance_2]

        instance = ArrayRelationModel.objects.create()
        instance.arr_relation.add(*rel_list)

        # Attempt to serialize an instance of the model using the data above
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = ArrayRelationModel
                fields = '__all__'
                depth = 1

        serializer = TestSerializer(instance)

        # Compare observed serialization with expected serialization
        expected_data = {
            '_id': str(instance._id),
            'int_val': instance.int_val,
            'arr_relation': [
                OrderedDict({
                    '_id': str(rel_instance_1.pk),
                    'email': rel_instance_1.email
                }),
                OrderedDict({
                    '_id': str(rel_instance_2.pk),
                    'email': rel_instance_2.email
                })
            ]
        }

        expected_str = format_dict(expected_data)
        observed_str = format_dict(serializer.data)

        assert expected_str == observed_str

    def test_root_create(self):
        """
        Confirm that new instances of models w/ ArrayModelFields fields
        can still be generated and saved correctly from raw data
        """
        # Set up the initial data
        rel_data_1 = {
            'email': 'jojo@gmail.com'
        }

        rel_instance_1 = ArrayRelatedModel.objects.create(**rel_data_1)

        rel_data_1.update({'pk': rel_instance_1.pk})

        rel_data_2 = {
            'email': 'gogo@gmail.com'
        }

        rel_instance_2 = ArrayRelatedModel.objects.create(**rel_data_2)

        rel_data_2.update({'pk': rel_instance_2.pk})

        data = {
            'int_val': -4321,
            # Default create is read_only
        }

        # Serializer should validate
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = ArrayRelationModel
                fields = '__all__'

        serializer = TestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        # Serializer should be able to save the data, sans relations
        instance = serializer.save()

        assert list(instance.arr_relation.all()) == []

        # Confirm that this default read-only setup can be overridden
        class NewTestSerializer(rmd_ser.DjongoModelSerializer):
            arr_relation = drf_ser.PrimaryKeyRelatedField(
                queryset=ArrayRelatedModel.objects.all(),
                many=True
            )

            def create(self, validated_data):
                rel_pks = validated_data.pop('arr_relation', [])
                obj = ArrayRelationModel.objects.create(**validated_data)
                obj.arr_relation.add(*rel_pks)
                obj.save()
                return obj

            class Meta:
                model = ArrayRelationModel
                fields = '__all__'

        data.update({
            'arr_relation': [rel_instance_1.pk, rel_instance_2.pk]
        })

        serializer = NewTestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        # Serializer should be able to save the data
        instance = serializer.save()

        expected_data = {
            '_id': str(instance.pk),
            'arr_relation': [rel_instance_1.pk, rel_instance_2.pk],
            'int_val': instance.int_val
        }

        assert format_dict(serializer.data) == format_dict(expected_data)

    def test_deep_create(self):
        """
        Confirm that new instances of models w/ ArrayModelFields fields
        can still be generated and saved correctly from raw data
        """
        # Set up the initial data
        rel_data_1 = {
            'email': 'jojo@gmail.com'
        }

        rel_instance_1 = ArrayRelatedModel.objects.create(**rel_data_1)

        rel_data_1.update({'pk': rel_instance_1.pk})

        rel_data_2 = {
            'email': 'gogo@gmail.com'
        }

        rel_instance_2 = ArrayRelatedModel.objects.create(**rel_data_2)

        rel_data_2.update({'pk': rel_instance_2.pk})

        data = {
            'int_val': -4321,
        }

        # Serializer should validate
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = ArrayRelationModel
                fields = '__all__'
                depth = 1

        serializer = TestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        # Serializer should be able to save the data, sans relations
        instance = serializer.save()

        assert list(instance.arr_relation.all()) == []

        # Confirm that this default read-only setup can be overridden
        class NewTestSerializer(rmd_ser.DjongoModelSerializer):
            arr_relation_pks = drf_ser.PrimaryKeyRelatedField(
                queryset=ArrayRelatedModel.objects.all(),
                many=True,
                write_only=True
            )

            def create(self, validated_data):
                rel_pks = validated_data.pop('arr_relation_pks', [])
                obj = ArrayRelationModel.objects.create(**validated_data)
                obj.arr_relation.add(*rel_pks)
                obj.save()
                return obj

            class Meta:
                model = ArrayRelationModel
                fields = '__all__'
                depth = 1

        data.update({
            'arr_relation_pks': [rel_instance_1.pk, rel_instance_2.pk]
        })

        serializer = NewTestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        # Serializer should be able to save the data
        instance = serializer.save()

        expected_data = {
            '_id': str(instance.pk),
            'int_val': instance.int_val,
            'arr_relation': [
                OrderedDict({
                    '_id': str(rel_instance_1.pk),
                    'email': rel_instance_1.email
                }),
                OrderedDict({
                    '_id': str(rel_instance_2.pk),
                    'email': rel_instance_2.email
                })],
        }

        assert format_dict(serializer.data) == format_dict(expected_data)

    def test_root_update(self):
        """
        Confirm that existing instances of models w/ ArrayReferenceFields
        can still be updated when provided with new raw data
        """
        # Set up the initial data
        rel_data_1 = {
            'email': 'jojo@gmail.com'
        }

        rel_instance_1 = ArrayRelatedModel.objects.create(**rel_data_1)

        rel_data_1.update({'pk': rel_instance_1.pk})

        rel_data_2 = {
            'email': 'gogo@gmail.com'
        }

        rel_instance_2 = ArrayRelatedModel.objects.create(**rel_data_2)

        rel_data_2.update({'pk': rel_instance_2.pk})

        old_data = {
            'int_val': -4321,
        }

        instance = ArrayRelationModel.objects.create(**old_data)
        instance.arr_relation.add(rel_instance_1, rel_instance_2)

        # Try to perform an instance update
        new_rel_data = {
            'email': 'new_user@new.com',
        }

        new_rel_instance = ArrayRelatedModel.objects.create(**new_rel_data)

        new_data = {
            'int_val': 999,
            'arr_relation': [new_rel_instance.pk]
        }

        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = ArrayRelationModel
                fields = '__all__'

        serializer = TestSerializer(instance, data=new_data)

        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer can still save w/ the updated
        # relations
        serializer.save()

        expected_data = {
            '_id': str(instance.pk),
            'int_val': '999',
            'arr_relation': [
                ObjectId(new_rel_instance.pk)
            ]
        }

        assert format_dict(serializer.data) == format_dict(expected_data)

    def test_deep_update(self):
        """
        Confirm that existing instances of models w/ ArrayReferenceFields
        can still be updated when provided with new raw data
        """
        # Set up the initial data
        rel_data_1 = {
            'email': 'jojo@gmail.com'
        }

        rel_instance_1 = ArrayRelatedModel.objects.create(**rel_data_1)

        rel_data_1.update({'pk': rel_instance_1.pk})

        rel_data_2 = {
            'email': 'gogo@gmail.com'
        }

        rel_instance_2 = ArrayRelatedModel.objects.create(**rel_data_2)

        rel_data_2.update({'pk': rel_instance_2.pk})

        old_data = {
            'int_val': -4321,
        }

        instance = ArrayRelationModel.objects.create(**old_data)
        instance.arr_relation.add(rel_instance_1, rel_instance_2)

        # Try to perform an instance update
        new_rel_data = {
            'email': 'new_user@new.com',
        }

        new_rel_instance = ArrayRelatedModel.objects.create(**new_rel_data)

        new_data = {
            'int_val': 999,
            'arr_relation': [new_rel_instance.pk]
        }

        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = ArrayRelationModel
                fields = '__all__'
                depth = 1

        # Confirm that the serializer can save, but strips reference data
        serializer = TestSerializer(instance, data=new_data)

        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer can still save w/ the updated relations
        serializer.save()

        expected_data = {
            '_id': str(instance.pk),
            'int_val': '999',
            'arr_relation': [
                OrderedDict({
                    '_id': str(rel_instance_1.pk),
                    'email': rel_instance_1.email,
                }),
                OrderedDict({
                    '_id': str(rel_instance_2.pk),
                    'email': rel_instance_2.email
                })
            ]
        }

        assert format_dict(serializer.data) == format_dict(expected_data)

        # Confirm that this default format can be overridden
        class NewTestSerializer(rmd_ser.DjongoModelSerializer):
            arr_relation = drf_ser.PrimaryKeyRelatedField(
                queryset=ArrayRelatedModel.objects.all(),
                read_only=False,
                many=True
            )

            class Meta:
                model = ArrayRelationModel
                fields = '__all__'
                depth = 1

            def update(self, inst, validated_data):
                rel_pks = validated_data.pop('arr_relation')
                inst.arr_relation.add(*rel_pks)
                inst.save()
                return inst

        serializer = NewTestSerializer(instance, data=new_data)

        assert serializer.is_valid(), serializer.errors

        instance = serializer.save()

        print(instance)
