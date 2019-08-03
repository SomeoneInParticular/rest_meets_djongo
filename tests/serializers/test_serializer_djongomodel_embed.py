from bson import ObjectId
from collections import OrderedDict

from django.test import TestCase

from rest_meets_djongo import fields as rmd_fields
from rest_meets_djongo import serializers as rmd_ser

from tests import models as test_models
from tests.utilities import format_dict


class TestMapping(TestCase):
    def test_common_embed(self):
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
            'embed_field': EmbeddedSerializer(allow_null=True, required=False)
        }

        expected_str = format_dict(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_nested_embed(self):
        """
        Confirm that embedded models within embedded models are still
        mapped correctly by the serializer
        """
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
            'deep_embed': EmbeddedSerializer(allow_null=True, required=False)
        }

        expected_str = format_dict(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_explicit_embed(self):
        """
        Confirm that serializers can handle user specified serializers
        for embedded models
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

        expected_str = format_dict(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_respects_fields(self):
        """
        Confirm that embedded models can be ignored by not specifying
        them in the `fields` Meta parameter
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ContainerModel
                fields = ['_id']

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
        }

        expected_str = format_dict(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_respects_exclude(self):
        """
        Confirm that embedded models can be ignored by specifying them
        in the `exclude` Meta parameter
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ContainerModel
                exclude = ['embed_field']

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
        }

        expected_str = format_dict(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_respects_no_depth(self):
        """
        Confirm that embedded models do not have embedded serializers
        constructed if the user specifies `depth = 0` in Meta

        In this case, these fields should be marked as `read_only` as well
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

        expected_str = format_dict(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_respects_partial_depth(self):
        """
        Confirm that embedded models do not have embedded serializers
        constructed after the designated number of levels designated by
        `depth` in the Meta of the original serializer.
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
            'deep_embed': EmbeddedSerializer(allow_null=True, required=False)
        }

        expected_str = format_dict(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str


class TestEmbeddingIntegration(TestCase):
    def test_deep_retrieve(self):
        """
        Confirm that existing instances of models with other embedded
        models can be retrieved and serialized correctly
        """
        # Create the instance to attempt to serialize
        embed_data = {
            'int_field': 1234,
            'char_field': 'Embed'
        }

        embed_instance = test_models.EmbedModel(**embed_data)

        data = {
            'embed_field': embed_instance
        }

        instance = test_models.ContainerModel.objects.create(**data)

        # Attempt to serialize the instance
        class TestSerializer(rmd_ser.EmbeddedModelSerializer):
            class Meta:
                model = test_models.ContainerModel
                fields = '__all__'

        serializer = TestSerializer(instance)

        # Confirm that the data was correctly serialized
        expected_data = {
            'embed_field': OrderedDict({
                'int_field': embed_data['int_field'],
                'char_field': embed_data['char_field']
            })
        }

        expected_str = format_dict(expected_data)
        observed_str = str(serializer.data)

        assert expected_str == observed_str

    def test_deep_create(self):
        """
        Confirm that new instances of models with embedded models can
        be generated and saved correctly from raw data
        """
        embed_data = {
            '_id': str(ObjectId()),
            'int_field': 1234,
            'char_field': 'Embed'
        }

        data = {'embed_field': embed_data}

        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ContainerModel
                fields = '__all__'

        # Serializer should validate
        serializer = TestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        # Sereializer should be able to save valid data correctly
        instance = serializer.save()
        assert isinstance(instance, test_models.ContainerModel)
        # ObjectID fields are currently non-modifiable
        assert instance.embed_field.int_field == embed_data['int_field']
        assert instance.embed_field.char_field == embed_data['char_field']

    def test_deep_update(self):
        """
        Confirm that existing instances of models with embedded models
        can be updated when provided with new raw data
        """
        # Initial (to-be-updated) instance creation
        initial_embed_data = {
            'int_field': 1234,
            'char_field': 'Embed'
        }

        embed_instance = test_models.EmbedModel(**initial_embed_data)

        initial_data = {
            'embed_field': embed_instance
        }

        instance = test_models.ContainerModel.objects.create(**initial_data)

        initial_data.update({'pk': instance.pk})

        # Try and perform a serializer based update
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ContainerModel
                fields = '__all__'

        new_embed_data = {
            'char_field': 'abcde',
            'int_field': 4321
        }

        new_data = {
            'embed_field': new_embed_data
        }

        serializer = TestSerializer(instance, data=new_data)

        # Confirm that the new data is valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves this updated instance correctly
        serializer.save()
        assert instance.pk == initial_data['pk']
        assert isinstance(instance.embed_field, test_models.EmbedModel)
        assert instance.embed_field.int_field == new_embed_data['int_field']
        assert instance.embed_field.char_field == new_embed_data['char_field']

    def test_deep_partial_update(self):
        """
        Confirm that existing instances of models with embedded models
        can be updated when provided with new partial data
        """
        # Initial (to-be-updated) instance creation
        initial_embed_data = {
            'int_field': 1234,
            'char_field': 'Embed'
        }

        embed_instance = test_models.EmbedModel(**initial_embed_data)

        initial_data = {
            'embed_field': embed_instance
        }

        instance = test_models.ContainerModel.objects.create(**initial_data)

        initial_data.update({'pk': instance.pk})

        # Attempt to perform a serializer based update
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.ContainerModel
                fields = '__all__'

        new_embed_data = {
            'int_field': 4321
        }

        new_data = {
            'embed_field': new_embed_data
        }

        serializer = TestSerializer(instance, data=new_data, partial=True)

        # Confirm that the partial update data is valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves this updated instance correctly
        serializer.save()
        assert instance.pk == initial_data['pk']
        assert isinstance(instance.embed_field, test_models.EmbedModel)
        assert instance.embed_field.int_field == new_embed_data['int_field']
        assert instance.embed_field.char_field == initial_embed_data['char_field']
