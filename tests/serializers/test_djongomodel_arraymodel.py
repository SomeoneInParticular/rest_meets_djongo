from collections import OrderedDict

from pytest import mark

from rest_meets_djongo import serializers as rmd_ser

from tests.models import ArrayContainerModel, NullArrayContainerModel, EmbedModel
from tests.utils import build_error_dict, format_dict


@mark.django_db
class TestIntegration(object):
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
                embed_data_1,
                embed_data_2
            ]
        }

        expected_str = format_dict(expected_data)
        observed_str = format_dict(serializer.data)

        assert expected_str == observed_str

    def test_null_retrieve_filled(self):
        """
        Test whether nullable lists are possible
        """

        # Set up the initial data
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = NullArrayContainerModel
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
        instance = NullArrayContainerModel.objects.create(nullable_list=embed_list)
        serializer = TestSerializer(instance)

        expected_data = {
            '_id': str(instance._id),
            'nullable_list': [
                embed_data_1,
                embed_data_2
            ]
        }

        expected_str = format_dict(expected_data)
        observed_str = format_dict(serializer.data)

        assert observed_str == expected_str

    def test_null_retrieve_empty(self):
        """
        Test whether nullable lists are possible, empty submitted
        """

        # Set up the initial data
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = NullArrayContainerModel
                fields = '__all__'

        # Attempt to serialize an instance of the model using the data above
        instance = NullArrayContainerModel.objects.create()
        serializer = TestSerializer(instance)

        expected_data = {
            '_id': str(instance._id),
            'nullable_list': None
        }

        expected_str = format_dict(expected_data)
        observed_str = format_dict(serializer.data)

        assert observed_str == expected_str

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

    def test_null_create_filled(self):
        """
        Confirm null fields do not interfere with creation
        """
        # Set up data to use for creation
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = NullArrayContainerModel
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
            'nullable_list': embed_list
        }

        # Serializer should validate
        serializer = TestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        # Serializer should be able to save data correctly, with the
        # correct order being preserved
        instance = serializer.save()
        assert instance.nullable_list[0].int_field == embed_data_1['int_field']
        assert instance.nullable_list[1].char_field == embed_data_2['char_field']

    def test_null_create_empty(self):
        """
        Confirm that objects can be created with null values
        """
        # Set up data to use for creation
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = NullArrayContainerModel
                fields = '__all__'

        data = {}

        # Serializer should validate
        serializer = TestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        # Serializer should be able to save data correctly, with the
        # correct order being preserved
        instance = serializer.save()
        print(instance.nullable_list)

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

    def test_null_update_filled(self):
        """
        Confirm that null fields do not impede updates
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
                model = NullArrayContainerModel
                fields = '__all__'

        embed_data_1.update({
            'char_field': 'baz'
        })

        new_data = {
            'nullable_list': [embed_data_1, embed_data_2, embed_data_1]
        }

        serializer = TestSerializer(instance, data=new_data)

        # Confirm that the update is valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves the updated instance correctly
        serializer.save()
        assert instance.pk == initial_data['pk']
        assert instance.nullable_list[0].int_field == embed_data_1['int_field']
        assert instance.nullable_list[0].char_field == embed_data_1['char_field']
        assert instance.nullable_list[1].int_field == embed_data_2['int_field']
        assert instance.nullable_list[2].char_field == embed_data_1['char_field']

    def test_null_update_empty(self):
        """
        Confirm that null values can be used to update
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
                model = NullArrayContainerModel
                fields = '__all__'

        embed_data_1.update({
            'char_field': 'baz'
        })

        new_data = {
            'nullable_list': None
        }

        serializer = TestSerializer(instance, data=new_data)

        # Confirm that the update is valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves the updated instance correctly
        serializer.save()

        expected_data = {
            '_id': str(instance.pk),
            'nullable_list': None
        }

        expected_str = format_dict(expected_data)
        observed_str = format_dict(serializer.data)

        assert observed_str == expected_str

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

    def test_non_list_field_caught(self):
        """
        Check that single values passed into list fields are caught
        """
        # Set up data to use for creation
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = ArrayContainerModel
                fields = '__all__'

        embed_data_1 = {
            'int_field': 123,
            'char_field': 'foo'
        }

        embed_obj = EmbedModel(**embed_data_1)

        data = {
            'embed_list': embed_obj
        }

        # Serializer should NOT validate correctly
        serializer = TestSerializer(data=data)
        assert not serializer.is_valid()

        # Confirm that the errors caught are correct
        print(serializer.errors)

