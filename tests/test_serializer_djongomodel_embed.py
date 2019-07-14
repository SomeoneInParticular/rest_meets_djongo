from bson import ObjectId
from collections import OrderedDict

from django.test import TestCase
from rest_framework import fields as drf_fields

from rest_meets_djongo import fields as rmd_fields
from rest_meets_djongo import serializers as rmd_ser

from tests import models as test_models
from .utils import expect_dict_to_str


class TestMapping(TestCase):
    def test_generic_embed(self):
        """
        Confirm that the serializer handles embedded models as intended

        By default, a generic serializer called 'EmbeddedSerializer' is
        generated if no explicit serializer is provided; this serializer
        uses all fields of the embedded model and 0 kwargs
        """

        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ContainerModel
                fields = '__all__'

        class EmbeddedSerializer(rmd_ser.EmbeddedModelSerializer):
            class Meta:
                model = test_models.EmbedModel
                fields = '__all__'

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'embed_field': EmbeddedSerializer()
        }

        expected_str = expect_dict_to_str(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_deep_embed(self):
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.DeepContainerModel
                fields = '__all__'

        # The nested serializer which should be generated therein
        class EmbeddedSerializer(rmd_ser.EmbeddedModelSerializer):
            class Meta:
                model = test_models.ContainerModel
                fields = '__all__'

        expected_dict = {
            'str_id': ("CharField("
                       "validators=[<django.core.validators.MaxLengthValidator object>, "
                       "<UniqueValidator(queryset=DeepContainerModel.objects.all())>])"),
            'deep_embed': EmbeddedSerializer()
        }

        expected_str = expect_dict_to_str(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        print(expected_str + '\n\n' + observed_str)

        assert expected_str == observed_str

    def test_explicit_serializer_embed(self):
        """
        Confirm that serializers can handle other nested serializers for
        embedded models
        """
        # Class to use as a serializer field
        class EmbedSerializer(rmd_ser.EmbeddedModelSerializer):
            class Meta:
                model = test_models.EmbedModel
                fields = '__all__'

        class TestSerializer(rmd_ser.DjongoModelSerializer):
            embed_field = EmbedSerializer()

            class Meta:
                model = test_models.ContainerModel
                fields = '__all__'

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'embed_field': EmbedSerializer()
        }

        expected_str = expect_dict_to_str(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_respects_fields(self):
        """
        Confirm that serializers can be ignored by not adding them to
        the fields attribute
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ContainerModel
                fields = ['_id']

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
        }

        expected_str = expect_dict_to_str(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_respects_exclude(self):
        """
        Confirm that implicitly created serializers can be ignored by
        naming their associated field in 'exclude'
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ContainerModel
                exclude = ['embed_field']

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
        }

        expected_str = expect_dict_to_str(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_respects_no_depth(self):
        """
        Confirm that implicitly created serializers will not be generated
        if the user specifies 0 depth
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.DeepContainerModel
                fields = '__all__'
                embed_depth = 0

        expected_dict = {
            'str_id': ("CharField(validators=[<django.core.validators.MaxLengthValidator object>, "
                       "<UniqueValidator(queryset=DeepContainerModel.objects.all())>])"),
            'deep_embed': ("EmbeddedModelField("
                           "model_field=<djongo.models.fields.EmbeddedModelField: deep_embed>, "
                           "read_only=True)")
        }

        expected_str = expect_dict_to_str(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_respects_partial_depth(self):
        """
        Confirm that implicitly created serializers will stop being
        generated when the user designated depth is reached
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.DeepContainerModel
                fields = '__all__'
                embed_depth = 1

        # The nested serializer which should be generated therein
        class EmbeddedSerializer(rmd_ser.EmbeddedModelSerializer):
            class Meta:
                model = test_models.ContainerModel
                fields = '__all__'
                embed_depth = 0

        expected_dict = {
            'str_id': ("CharField("
                       "validators=[<django.core.validators.MaxLengthValidator object>, "
                       "<UniqueValidator(queryset=DeepContainerModel.objects.all())>])"),
            'deep_embed': EmbeddedSerializer()
        }

        expected_str = expect_dict_to_str(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        print(expected_str + '\n\n' + observed_str)

        assert expected_str == observed_str


class TestEmbeddingIntegration(TestCase):
    def test_generic_retrieve(self):
        class TestSerializer(rmd_ser.EmbeddedModelSerializer):
            class Meta:
                model = test_models.ContainerModel
                fields = '__all__'

        embed_data = {
            '_id': ObjectId(),
            'int_field': 1234,
            'char_field': 'Embed'
        }

        embed_instance = test_models.EmbedModel(**embed_data)

        instance = test_models.ContainerModel.objects.create(
            embed_field=embed_instance
        )
        serializer = TestSerializer(instance)

        expected_data = {
            'embed_field': OrderedDict({
                '_id': str(embed_data['_id']),
                'int_field': embed_data['int_field'],
                'char_field': embed_data['char_field']
            })
        }

        expected_str = expect_dict_to_str(expected_data)
        observed_str = str(serializer.data)

        assert expected_str == observed_str

    def test_generic_create(self):
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ContainerModel
                fields = '__all__'

        embed_data = {
            '_id': str(ObjectId()),
            'int_field': 1234,
            'char_field': 'Embed'
        }

        instance_data = {'embed_field': embed_data}

        serializer = TestSerializer(data=instance_data)
        serializer.is_valid()

        assert serializer.is_valid(), serializer.errors

        instance = serializer.save()

        assert isinstance(instance, test_models.ContainerModel)
        # Confirm the embedded model is saved correctly
        # ObjectID fields are currently locked as read_only, and thus not
        # shown by default
        assert instance.embed_field.int_field == embed_data['int_field']
        assert instance.embed_field.char_field == embed_data['char_field']

    # def test_generic_update(self):
    #     class TestSerializer(rmd_ser.DjongoModelSerializer):
    #         class Meta:
    #             model = test_models.ContainerModel
    #             fields = '__all__'
    #
    #     initial_embed_data = {
    #         '_id': str(ObjectId()),
    #         'int_field': 1234,
    #         'char_field': 'Embed'
    #     }
    #
    #     new_embed_data = {
    #         'char_field': 'abcde',
    #         'int_field': 4321
    #     }
    #
    #     modifying_data = {
    #         'embed_field': new_embed_data
    #     }
    #
    #     embed_instance = test_models.EmbedModel(**initial_embed_data)
    #     instance = test_models.ContainerModel(embed_field=embed_instance)
    #     serializer = TestSerializer(instance, data=modifying_data)
    #
    #     assert serializer.is_valid(), serializer.errors
    #
    #     serializer.save()  # Should automatically update the instance
    #     assert isinstance(instance.embed_field, test_models.EmbedModel)
    #     assert instance.embed_field.int_field == new_embed_data['int_field']
    #     assert instance.embed_field.char_field == new_embed_data['char_field']

    def test_generic_partial_update(self):
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ContainerModel
                fields = '__all__'

        initial_embed_data = {
            '_id': str(ObjectId()),
            'int_field': 1234,
            'char_field': 'Embed'
        }

        new_embed_data = {
            'int_field': 4321
        }

        modifying_data = {
            'embed_field': new_embed_data
        }

        embed_instance = test_models.EmbedModel(**initial_embed_data)
        instance = test_models.ContainerModel(embed_field=embed_instance)
        serializer = TestSerializer(instance, data=modifying_data, partial=True)

        assert serializer.is_valid(), serializer.errors

        serializer.save()  # Should automatically update the instance
        assert isinstance(instance.embed_field, test_models.EmbedModel)
        assert instance.embed_field.int_field == new_embed_data['int_field']
        assert instance.embed_field.char_field == initial_embed_data['char_field']
