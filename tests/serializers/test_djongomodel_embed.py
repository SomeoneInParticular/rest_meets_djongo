from collections import OrderedDict

from rest_meets_djongo import fields as rmd_fields
from rest_meets_djongo.serializers import \
    DjongoModelSerializer, EmbeddedModelSerializer

from tests.models import ContainerModel, EmbedModel, DeepContainerModel

from pytest import fixture, mark, param, raises


@mark.embed
@mark.mapping
@mark.serializer
class TestMapping(object):
    def test_common_embed(self, assert_dict_equals):
        """
        Confirm that the serializer automatically generates embedded
        serializer fields if not otherwise specified. Confirm that this
        created serializer, by default, allows null values
        """
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = ContainerModel
                fields = '__all__'

        class EmbeddedSerializer(EmbeddedModelSerializer):
            class Meta:
                model = EmbedModel
                fields = '__all__'

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'embed_field': EmbeddedSerializer(allow_null=True, required=False)
        }

        assert_dict_equals(TestSerializer().get_fields(), expected_dict)

    def test_nested_embed(self, assert_dict_equals):
        """
        Confirm that embedded models within embedded models are still
        mapped correctly by the serializer
        """
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = DeepContainerModel
                fields = '__all__'

        # The nested serializer which should be automatically generated
        class EmbeddedSerializer(EmbeddedModelSerializer):
            class Meta:
                model = ContainerModel
                fields = '__all__'

        expected_dict = {
            'str_id': ("CharField(max_length=10, "
                       "validators=[<UniqueValidator(queryset=DeepContainerModel.objects.all())>])"),
            'deep_embed': EmbeddedSerializer(allow_null=True, required=False)
        }

        assert_dict_equals(TestSerializer().get_fields(), expected_dict)

    def test_explicit_embed(self, assert_dict_equals):
        """
        Confirm that serializers can handle user specified serializers
        for embedded models
        """
        class EmbedSerializer(EmbeddedModelSerializer):
            class Meta:
                model = EmbedModel
                fields = ['int_field']

        class TestSerializer(DjongoModelSerializer):
            embed_field = EmbedSerializer()

            class Meta:
                model = ContainerModel
                fields = '__all__'

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'embed_field': EmbedSerializer()
        }

        assert_dict_equals(TestSerializer().get_fields(), expected_dict)

    def test_respects_fields(self, assert_dict_equals):
        """
        Confirm that embedded models can be ignored by not specifying
        them in the `fields` Meta parameter
        """
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = ContainerModel
                fields = ['_id']

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
        }

        assert_dict_equals(TestSerializer().get_fields(), expected_dict)

    def test_respects_exclude(self, assert_dict_equals):
        """
        Confirm that embedded models can be ignored by specifying them
        in the `exclude` Meta parameter
        """
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = ContainerModel
                exclude = ['embed_field']

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
        }

        assert_dict_equals(TestSerializer().get_fields(), expected_dict)

    def test_respects_no_depth(self, assert_dict_equals):
        """
        Confirm that embedded models do not have embedded serializers
        constructed if the user specifies `depth = 0` in Meta

        In this case, these fields should be marked as `read_only` as well
        """
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = DeepContainerModel
                fields = '__all__'
                embed_depth = 0

        expected_dict = {
            'str_id': ("CharField(max_length=10, "
                       "validators=[<UniqueValidator(queryset=DeepContainerModel.objects.all())>])"),
            'deep_embed': ("EmbeddedModelField("
                           "model_field=<djongo.models.fields.EmbeddedModelField: deep_embed>, "
                           "read_only=True)")
        }

        assert_dict_equals(TestSerializer().get_fields(), expected_dict)

    def test_respects_partial_depth(self, assert_dict_equals):
        """
        Confirm that embedded models do not have embedded serializers
        constructed after the designated number of levels designated by
        `depth` in the Meta of the original serializer.
        """
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = DeepContainerModel
                fields = '__all__'
                embed_depth = 1

        # The nested serializer which should be generated therein
        class EmbeddedSerializer(EmbeddedModelSerializer):
            class Meta:
                model = ContainerModel
                fields = '__all__'
                embed_depth = 0

        expected_dict = {
            'str_id': ("CharField(max_length=10, "
                       "validators=[<UniqueValidator(queryset=DeepContainerModel.objects.all())>])"),
            'deep_embed': EmbeddedSerializer(allow_null=True, required=False)
        }

        assert_dict_equals(TestSerializer().get_fields(), expected_dict)


@mark.embed
@mark.integration
@mark.serializer
@mark.django_db
class TestEmbeddingIntegration(object):
    # -- DB Setup fixtures -- #
    @fixture
    def embed_instance(self):
        embed_data = {
            'int_field': 1234,
            'char_field': 'Embed'
        }

        embed_instance = EmbedModel(**embed_data)

        return embed_instance

    @fixture
    def container_instance(self, embed_instance):
        """Prepares a default ContainerModel instance in the DB"""
        from collections import namedtuple
        container_data = {
            'embed_field': embed_instance
        }

        container_instance = ContainerModel.objects.create(**container_data)

        data_tuple = namedtuple('ModelData', ['embedded', 'container'])

        data = {
            'embedded': embed_instance,
            'container': container_instance,
        }

        return data_tuple(**data)

    # -- Actual Test Code -- #
    @mark.parametrize(
        ["serializer", "expected", "missing"],
        [
            param(
                # Generic test
                {'target': ContainerModel},
                {'embed_field': OrderedDict({
                    'int_field': 1234, 'char_field': 'Embed'
                })},
                None,
                id='basic'
            ),
            param(
                # Fields meta data is respected
                {'target': ContainerModel,
                 'meta_fields': ['embed_field'],
                 'name': 'MetaFieldSerializer'},
                {'embed_field': OrderedDict({
                    'int_field': 1234, 'char_field': 'Embed'
                })},
                None,
                id='respects_fields'
            ),
            param(
                # Exclude meta data is respected
                {'target': ContainerModel,
                 'meta_exclude': ['embed_field']},
                None,
                {'embed_field': OrderedDict({
                    'int_field': 1234, 'char_field': 'Embed'
                })},
                id='respects_exclude'
            ),
            param(
                # Custom embedded field serializer (fields specified)
                {'target': ContainerModel, 'custom_fields': {
                    'embed_field': {
                        'target': EmbedModel,
                        'base_class': EmbeddedModelSerializer,
                        'meta_fields': ['int_field']
                    }
                }},
                {'embed_field': OrderedDict({'int_field': 1234})},
                {'embed_field': OrderedDict({'char_field': 'Embed'})},
                id='respects_nested_fields'
            )
        ])
    def test_retrieve(self, build_serializer, does_a_subset_b,
                      container_instance, serializer, expected, missing):
        # Prepare the test environment
        TestSerializer = build_serializer(**serializer)
        serializer = TestSerializer(container_instance.container)

        # Make sure fields which should exist do
        if expected:
            does_a_subset_b(expected, serializer.data)

        # Make sure fields which should be ignored are
        if missing:
            with raises(AssertionError):
                does_a_subset_b(missing, serializer.data)

    # def test_root_retrieve_historical(self, assert_dict_equals, container_instance):
    #     class TestSerializer(DjongoModelSerializer):
    #         class Meta:
    #             model = ContainerModel
    #             fields = '__all__'
    #             embed_depth = 0
    #
    #     serializer = TestSerializer(container_instance.container)
    #
    #     # Confirm that the data was correctly serialized
    #     expect_data = {
    #         '_id': container_instance.data['_id'],
    #         'embed_field': dict(container_instance.data['embed_field'])
    #     }
    #
    #     assert_dict_equals(serializer.data, expect_data)
    #
    # def test_deep_retrieve(self, assert_dict_equals, container_instance):
    #     """
    #     Confirm that existing instances of models with other embedded
    #     models can be retrieved and serialized correctly
    #     """
    #     class TestSerializer(DjongoModelSerializer):
    #         class Meta:
    #             model = ContainerModel
    #             fields = '__all__'
    #
    #     serializer = TestSerializer(container_instance.instance)
    #
    #     # Confirm that the data was correctly serialized
    #     assert_dict_equals(serializer.data, container_instance.data)
    #
    # def test_root_create(self, instance_matches_data, container_instance):
    #     """
    #     Confirm that fields at the embed depth are made read-only, and
    #     remain as such without user overrides
    #     """
    #     class TestSerializer(DjongoModelSerializer):
    #         class Meta:
    #             model = ContainerModel
    #             fields = '__all__'
    #             embed_depth = 0
    #
    #     # Serializer should validate
    #     serializer = TestSerializer(data=container_instance.data)
    #     assert serializer.is_valid(), serializer.errors
    #
    #     # Serializer should be able to save valid data correctly
    #     instance = serializer.save()
    #
    #     expect_data = {
    #         'embed_field': container_instance.instance.embed_field
    #     }
    #
    #     instance_matches_data(instance, expect_data)
    #
    # def test_deep_create(self, instance_matches_data, container_instance):
    #     """
    #     Confirm that new instances of models with embedded models can
    #     be generated and saved correctly from raw data
    #     """
    #     class TestSerializer(DjongoModelSerializer):
    #         class Meta:
    #             model = ContainerModel
    #             fields = '__all__'
    #
    #     # Serializer should validate
    #     serializer = TestSerializer(data=container_instance.data)
    #     assert serializer.is_valid(), serializer.errors
    #
    #     # Serializer should be able to save valid data correctly
    #     instance = serializer.save()
    #
    #     expect_data = {
    #         'embed_field': container_instance.instance.embed_field
    #     }
    #
    #     instance_matches_data(instance, expect_data)
    #
    # def test_deep_update(self):
    #     """
    #     Confirm that existing instances of models with embedded models
    #     can be updated when provided with new raw data
    #     """
    #     # Initial (to-be-updated) instance creation
    #     initial_embed_data = {
    #         'int_field': 1234,
    #         'char_field': 'Embed'
    #     }
    #
    #     embed_instance = EmbedModel(**initial_embed_data)
    #
    #     initial_data = {
    #         'embed_field': embed_instance
    #     }
    #
    #     instance = ContainerModel.objects.create(**initial_data)
    #
    #     initial_data.update({'pk': instance.pk})
    #
    #     # Try and perform a serializer based update
    #     class TestSerializer(DjongoModelSerializer):
    #         class Meta:
    #             model = ContainerModel
    #             fields = '__all__'
    #
    #     new_embed_data = {
    #         'char_field': 'abcde',
    #         'int_field': 4321
    #     }
    #
    #     new_data = {
    #         'embed_field': new_embed_data
    #     }
    #
    #     serializer = TestSerializer(instance, data=new_data)
    #
    #     # Confirm that the new data is valid
    #     assert serializer.is_valid(), serializer.errors
    #
    #     # Confirm that the serializer saves this updated instance correctly
    #     serializer.save()
    #     assert instance.pk == initial_data['pk']
    #     assert isinstance(instance.embed_field, EmbedModel)
    #     assert instance.embed_field.int_field == new_embed_data['int_field']
    #     assert instance.embed_field.char_field == new_embed_data['char_field']
    #
    # def test_deep_partial_update(self):
    #     """
    #     Confirm that existing instances of models with embedded models
    #     can be updated when provided with new partial data
    #     """
    #     # Initial (to-be-updated) instance creation
    #     initial_embed_data = {
    #         'int_field': 1234,
    #         'char_field': 'Embed'
    #     }
    #
    #     embed_instance = EmbedModel(**initial_embed_data)
    #
    #     initial_data = {
    #         'embed_field': embed_instance
    #     }
    #
    #     instance = ContainerModel.objects.create(**initial_data)
    #
    #     initial_data.update({'pk': instance.pk})
    #
    #     # Attempt to perform a serializer based update
    #     class TestSerializer(DjongoModelSerializer):
    #         class Meta:
    #             model = ContainerModel
    #             fields = '__all__'
    #
    #     new_embed_data = {
    #         'int_field': 4321
    #     }
    #
    #     new_data = {
    #         'embed_field': new_embed_data
    #     }
    #
    #     serializer = TestSerializer(instance, data=new_data, partial=True)
    #
    #     # Confirm that the partial update data is valid
    #     assert serializer.is_valid(), serializer.errors
    #
    #     # Confirm that the serializer saves this updated instance correctly
    #     serializer.save()
    #     assert instance.pk == initial_data['pk']
    #     assert isinstance(instance.embed_field, EmbedModel)
    #     assert instance.embed_field.int_field == new_embed_data['int_field']
    #     assert instance.embed_field.char_field == initial_embed_data['char_field']
