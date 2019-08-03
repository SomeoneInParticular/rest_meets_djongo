from bson import ObjectId
from collections import OrderedDict

from django.test import TestCase

from rest_meets_djongo import serializers as rmd_ser

from tests.models import ArrayContainerModel, EmbedModel
from tests.utilities import build_error_dict


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
            'int_field': 1234,
            'char_field': 'foo'
        }

        embed_data_2 = {
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
            'int_field': 1234,
            'char_field': 'foo'
        }

        embed_data_2 = {
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
            'int_field': 1234,
            'char_field': 'foo'
        }

        embed_data_2 = {
            'int_field': 4321,
            'char_field': 'bar'
        }

        embed_list = [
            EmbedModel(**embed_data_1), EmbedModel(**embed_data_2)
        ]

        initial_data = {
            'embed_list': embed_list
        }

        instance = ArrayContainerModel.objects.create(**initial_data)

        initial_data.update({'pk': instance.pk})

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

    def test_invalid_nest_fields_caught(self):
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
            'int_field': 2147483650,  # Invalid, integer above max
            'char_field': 'foo-fab'  # Invalid, string too large
        }

        embed_data_2 = {
            'int_field': 4321,
            'char_field': 'bar-baz',  # Invalid, string too large
        }

        embed_list = [
            embed_data_1, embed_data_2
        ]

        data = {
            'embed_list': embed_list
        }

        # Serializer should NOT validate correctly
        serializer = TestSerializer(data=data)
        assert not serializer.is_valid()

        # Confirm that the errors caught are correct
        err_dict = build_error_dict(serializer.errors)
        embed_errs = err_dict['embed_list']

        # All errors should be associated with their respective instance
        assert 'max_value' in embed_errs[0]['int_field']
        assert 'max_length' in embed_errs[0]['char_field']
        assert 'max_length' in embed_errs[1]['char_field']

        # Only the three errors we created should be caught
        assert len(err_dict['embed_list']) == 2
