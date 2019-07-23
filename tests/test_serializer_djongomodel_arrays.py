from bson import ObjectId
from collections import OrderedDict

from django.test import TestCase

from rest_meets_djongo import serializers as rmd_ser

from .models import ArrayContainerModel, EmbedModel


class TestIntegration(TestCase):
    def test_retrieve(self):
        """
        Confirm that existing instances of models w/ ArrayModelFields can
        still be retrieved and serialized correctly
        """
        # Set up the initial data
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = ArrayContainerModel
                fields = '__all__'

        embed_data_1 = {
            '_id': str(ObjectId()),
            'int_field': 1234,
            'char_field': 'foo'
        }

        embed_data_2 = {
            '_id': str(ObjectId()),
            'int_field': 4321,
            'char_field': 'bar'
        }

        embed_list = [
            EmbedModel(**embed_data_1), EmbedModel(**embed_data_2)
        ]

        # Attempt to serialize an instance of the model using the data above
        instance = ArrayContainerModel.objects.create(embed_list=embed_list)
        serializer = TestSerializer(instance)

        expected_data = {
            '_id': str(instance._id),
            'embed_list': [
                OrderedDict(embed_data_1),
                OrderedDict(embed_data_2)
            ]
        }

        self.assertDictEqual(expected_data, serializer.data)

    def test_create(self):
        """
        Confirm that new instances of models w/ ArrayModelFields fields
        can still be generated and saved correctly from raw data
        """
        # Set up data to use for creation
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = ArrayContainerModel
                fields = '__all__'

        embed_data_1 = {
            '_id': str(ObjectId()),
            'int_field': 1234,
            'char_field': 'foo'
        }

        embed_data_2 = {
            '_id': str(ObjectId()),
            'int_field': 4321,
            'char_field': 'bar'
        }

        embed_list = [
            embed_data_1, embed_data_2
        ]

        data = {
            'embed_list': embed_list
        }

        # Serializer should validate
        serializer = TestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        # Serializer should be able to save data correctly, with the
        # correct order being preserved
        instance = serializer.save()
        assert instance.embed_list[0].int_field == embed_data_1['int_field']
        assert instance.embed_list[1].char_field == embed_data_2['char_field']

    def test_update(self):
        """
        Confirm that existing instances of models w/ ArrayModelFields
        can still be updated when provided with new raw data
        """
        # Set up the initial data
        embed_data_1 = {
            '_id': str(ObjectId()),
            'int_field': 1234,
            'char_field': 'foo'
        }

        embed_data_2 = {
            '_id': str(ObjectId()),
            'int_field': 4321,
            'char_field': 'bar'
        }

        embed_list = [
            EmbedModel(**embed_data_1), EmbedModel(**embed_data_2)
        ]

        instance = ArrayContainerModel.objects.create(embed_list=embed_list)

        initial_data = {
            'pk': instance.pk,
            'embed_list': instance.embed_list
        }

        # Attempt to update the instance above
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = ArrayContainerModel
                fields = '__all__'

        embed_data_1.update({
            'char_field': 'baz'
        })

        new_data = {
            'embed_list': [embed_data_1, embed_data_2, embed_data_1]
        }

        serializer = TestSerializer(instance, data=new_data)

        # Confirm that the update is valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves the updated instance correctly
        serializer.save()
        assert instance.pk == initial_data['pk']
        assert instance.embed_list[0].int_field == embed_data_1['int_field']
        assert instance.embed_list[0].char_field == embed_data_1['char_field']
        assert instance.embed_list[1].int_field == embed_data_2['int_field']
        assert instance.embed_list[2].char_field == embed_data_1['char_field']
