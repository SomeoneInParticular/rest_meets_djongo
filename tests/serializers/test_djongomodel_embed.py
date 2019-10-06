from collections import OrderedDict

from rest_framework.fields import CharField

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
            'control_val': CharField(max_length=7, required=False),
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
            'control_val': CharField(required=False, max_length=7),
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
            'embed_field': EmbedSerializer(),
            'control_val': CharField(max_length=7, required=False),
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
            'control_val': CharField(required=False, max_length=7)
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
            'control_val': CharField(required=False, max_length=7),
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
            'control_val': CharField(required=False, max_length=7),
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

    @fixture
    def deep_container_instance(self, container_instance):
        from collections import namedtuple
        deep_data = {
            'str_id': 'identifier',
            'deep_embed': container_instance.container
        }

        deep_instance = DeepContainerModel.objects.create(**deep_data)

        data_tuple = namedtuple(
            'ModelData', ['embedded', 'container', 'deep_container']
        )

        data = {
            'embedded': container_instance.embedded,
            'container': container_instance.container,
            'deep_container': deep_instance
        }

        return data_tuple(**data)

    # -- Actual Test Code -- #
    @mark.parametrize(
        ["serializer", "expected", "missing"],
        [
            param(
                # Generic test
                {'target': ContainerModel},
                {'control_val': "CONTROL",
                 'embed_field': OrderedDict({
                    'int_field': 1234,
                    'char_field': 'Embed'
                 })},
                None,
                id='basic'
            ),
            param(
                # Fields meta, in the root model, is respected
                {'target': ContainerModel,
                 'meta_fields': ['embed_field']},
                {'embed_field': OrderedDict({
                    'int_field': 1234,
                    'char_field': 'Embed'
                 })},
                {'control_val': 'CONTROL'},
                id='respects_fields'
            ),
            param(
                # Exclude meta, in the root model, is respected
                {'target': ContainerModel,
                 'meta_exclude': ['embed_field']},
                {'control_val': 'CONTROL'},
                {'embed_field': OrderedDict({
                    'int_field': 1234, 'char_field': 'Embed'
                })},
                id='respects_exclude'
            ),
            param(
                # Fields meta, in the contained model, is respected
                {'target': ContainerModel, 'custom_fields': {
                    'embed_field': {
                        'target': EmbedModel,
                        'base_class': EmbeddedModelSerializer,
                        'meta_fields': ['int_field']
                    }
                }},
                {'control_val': "CONTROL",
                 'embed_field': OrderedDict({'int_field': 1234})},
                {'embed_field': OrderedDict({'char_field': 'Embed'})},
                id='respects_nested_fields'
            ),
            param(
                # Exclude meta, in the contained model, is respected
                {'target': ContainerModel, 'custom_fields': {
                    'embed_field': {
                        'target': EmbedModel,
                        'base_class': EmbeddedModelSerializer,
                        'meta_exclude': ['int_field']
                    }
                }},
                {'control_val': "CONTROL",
                 'embed_field': OrderedDict({'char_field': 'Embed'})},
                {'embed_field': OrderedDict({'int_field': 1234})},
                id='respects_nested_exclude'
            )
        ])
    def test_basic_retrieve(self, build_serializer, does_a_subset_b,
                            container_instance, serializer, expected, missing):
        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(container_instance.container)

        # Make sure fields which should exist do
        if expected:
            does_a_subset_b(expected, serializer.data)

        # Make sure fields which should be ignored are
        if missing:
            with raises(AssertionError):
                does_a_subset_b(missing, serializer.data)

    @mark.parametrize(
        ["serializer", "expected", "missing"],
        [
            param(
                # Generic test
                {'target': DeepContainerModel},
                {'control_val': "CONTROL",
                 'deep_embed': OrderedDict({
                    'control_val': "CONTROL",
                    'embed_field': OrderedDict({
                        'int_field': 1234,
                        'char_field': "Embed"
                    })
                 })},
                None,
                id='basic'
            ),
            param(
                # Fields meta, in the topmost model, is respected
                {'target': DeepContainerModel,
                 'meta_fields': ['deep_embed']},
                {'deep_embed': OrderedDict({
                    'control_val': "CONTROL",
                    'embed_field': OrderedDict({
                        'int_field': 1234,
                        'char_field': "Embed"
                    })
                })},
                {'control_val': "CONTROL"},
                id='respects_root_fields'
            ),
            param(
                # Exclude meta, in the topmost model, is respected
                {'target': DeepContainerModel,
                 'meta_exclude': ['deep_embed']},
                {'control_val': "CONTROL"},
                {'deep_embed': OrderedDict({
                    'control_val': "CONTROL",
                    'embed_field': OrderedDict({
                        'int_field': 1234,
                        'char_field': "Embed"
                    })
                })},
                id='respects_root_exclude'
            ),
            param(
                # Fields meta, in the intermediary model, is respected
                {'target': DeepContainerModel,
                 'custom_fields': {
                     'deep_embed': {
                         'target': ContainerModel,
                         'meta_fields': ['embed_field']
                     },
                 }},
                {'control_val': "CONTROL",
                 'deep_embed': OrderedDict({
                     'embed_field': OrderedDict({
                         'int_field': 1234,
                         'char_field': "Embed"
                     })
                 })},
                {'deep_embed': OrderedDict({
                     'control_val': "CONTROL"
                 })},
                id='respects_intermediary_fields'
            ),
            param(
                # Exclude meta, in the intermediary model, is respected
                {'target': DeepContainerModel,
                 'custom_fields': {
                     'deep_embed': {
                         'target': ContainerModel,
                         'meta_exclude': ['embed_field']
                     },
                 }},
                {'deep_embed': OrderedDict({
                    'control_val': "CONTROL"
                })},
                {'control_val': "CONTROL",
                 'deep_embed': OrderedDict({
                     'embed_field': OrderedDict({
                         'int_field': 1234,
                         'char_field': "Embed"
                     })
                 })},
                id='respects_intermediary_exclude'
            ),
            param(
                # Field meta, in the deepest model, is respected
                {'target': DeepContainerModel,
                 'custom_fields': {
                     'deep_embed': {
                         'target': ContainerModel,
                         'custom_fields': {
                             'embed_field': {
                                 'target': EmbedModel,
                                 'meta_fields': ['char_field']
                             }
                         }
                     },
                 }},
                {'control_val': "CONTROL",
                 'deep_embed': OrderedDict({
                     'control_val': "CONTROL",
                     'embed_field': OrderedDict({
                         'char_field': "Embed"
                     })
                 })},
                {'deep_embed': OrderedDict({
                     'embed_field': OrderedDict({
                         'int_field': 1234,
                     })
                })},
                id='respects_deep_fields'
            ),
            param(
                # Field meta, in the deepest model, is respected
                {'target': DeepContainerModel,
                 'custom_fields': {
                     'deep_embed': {
                         'target': ContainerModel,
                         'custom_fields': {
                             'embed_field': {
                                 'target': EmbedModel,
                                 'meta_exclude': ['char_field']
                             }
                         }
                     },
                 }},
                {'control_val': "CONTROL",
                 'deep_embed': OrderedDict({
                     'control_val': "CONTROL",
                     'embed_field': OrderedDict({
                         'int_field': 1234,
                     })
                 })},
                {'deep_embed': OrderedDict({
                    'embed_field': OrderedDict({
                        'char_field': "Embed",
                    })
                })},
                id='respects_deep_exclude'
            )
        ])
    def test_deep_retrieve(self, build_serializer, does_a_subset_b,
                           deep_container_instance, serializer, expected,
                           missing):
        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(deep_container_instance.deep_container)

        # Make sure fields which should exist do
        if expected:
            does_a_subset_b(expected, serializer.data)

        # Make sure fields which should be ignored are
        if missing:
            with raises(AssertionError):
                does_a_subset_b(missing, serializer.data)

    @mark.parametrize(
        ["initial", "serializer", "expected"],
        [
            param(
                # Basic test (Shallowly nested models)
                {'embed_field': {
                    'int_field': 1357,
                    'char_field': "Bar"
                }},
                {'target': ContainerModel},
                {'control_val': "CONTROL",
                 'embed_field': EmbedModel(
                    int_field=1357,
                    char_field="Bar"
                 )},
                id='basic_root'
            ),
            param(
                # Basic test (deeply nested models)
                {'str_id': "identifier",
                 'deep_embed': {
                    'embed_field': {
                        'int_field': 1357,
                        'char_field': "Bar"
                    }},
                 },
                {'target': DeepContainerModel},
                {'str_id': "identifier",
                 'control_val': "CONTROL",
                 'deep_embed': ContainerModel(
                    control_val="CONTROL",
                    embed_field=EmbedModel(
                        int_field=1357,
                        char_field="Bar"
                    ),
                 )},
                id='basic_deep'
            ),
            param(
                # Custom fields are valid in the root model
                {},
                {'target': ContainerModel,
                 'custom_fields': {
                     'embed_field': {
                         'target': EmbedModel,
                         'required': False,
                     }
                 }},
                {'control_val': "CONTROL"},
                id='custom_field_root'
            ),
            param(
                # Custom fields are valid (intermediary field)
                {'str_id': "identifier"},
                {'target': DeepContainerModel,
                 'custom_fields': {
                     'deep_embed': {
                         'target': ContainerModel,
                         'required': False,
                         'default': {
                             'embed_field': {
                                 'int_field': 1357,
                                 'char_field': "Bar"
                             }
                         }
                     }
                 }},
                {'control_val': "CONTROL",
                 'deep_embed': ContainerModel(
                     control_val="CONTROL",
                     embed_field=EmbedModel(
                         int_field=1357,
                         char_field="Bar"
                     )
                 )},
                id='custom_field_intermediate'
            ),
            param(
                # Custom fields are valid (deeply nested field)
                {'str_id': 'identifier',
                 'deep_embed': {
                     'embed_field': {
                         'int_field': 1357
                     }},
                 },
                {'target': DeepContainerModel,
                 'custom_fields': {
                     'deep_embed': {
                         'target': ContainerModel,
                         'custom_fields': {
                             'embed_field': {
                                 'target': EmbedModel,
                                 'custom_fields': {
                                     'char_field': CharField(default="Foo")
                                 }
                             }
                         }
                     }
                 }},
                {'str_id': 'identifier',
                 'deep_embed': ContainerModel(
                     control_val="CONTROL",
                     embed_field=EmbedModel(
                         int_field=1357,
                         char_field="Foo"
                     ))
                 },
                id='custom_field_deep'
            ),
        ])
    def test_valid_create(self, build_serializer, instance_matches_data,
                          initial, serializer, expected):
        # Test environment preparation
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(data=initial)

        # Confirm that input data is valid
        assert serializer.is_valid(), serializer.errors

        # Make sure the serializer can save the data
        instance = serializer.save()

        # Confirm that the data was saved correctly
        instance_matches_data(instance, expected)

    @mark.parametrize(
        ["initial", "serializer", "error"],
        [
            param(
                # Invalid values in the root model are caught
                {'control_val': "WAY_TOO_LONG"},
                {'target': ContainerModel},
                AssertionError,
                id='root_validation'
            ),
            param(
                # Invalid values in the intermediary model are caught
                {'deep_embed': {
                    'control_val': "WAY_TOO_LONG"
                }},
                {'target': DeepContainerModel},
                AssertionError,
                id='intermediate_validation'
            ),
            param(
                # Invalid values in the deepest model are caught
                {'deep_embed': {
                    'control_val': {
                        'int_val': 1357,
                        'char_val': "TOO_LONG"
                    }
                }},
                {'target': DeepContainerModel},
                AssertionError,
                id='deep_validation'
            ),
            param(
                # Missing values in the deepest model are caught
                {'deep_embed': {
                    'control_val': {
                        'int_val': 1357,
                    }
                }},
                {'target': DeepContainerModel},
                AssertionError,
                id='deep_validation'
            ),
        ])
    def test_invalid_create(self, build_serializer, instance_matches_data,
                            initial, serializer, error):
        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(data=initial)

        # Confirm that the serializer throws the designated error
        with raises(error):
            assert serializer.is_valid(), serializer.errors

            serializer.save()

    @mark.parametrize(
        ["update", "serializer", "expected"],
        [
            param(
                # Generic test
                {'control_val': "NEW_VAL",
                 'embed_field': {
                    'int_field': 2468,
                    'char_field': "Baz"
                 }},
                {'target': ContainerModel},
                {'control_val': "NEW_VAL",
                 'embed_field': EmbedModel(
                    int_field=2468,
                    char_field="Baz"
                 )},
                id='basic'
            ),
            param(
                # Values can be set to null after submission
                {'control_val': "NEW_VAL",
                 'embed_field': None},
                {'target': ContainerModel},
                {'control_val': "NEW_VAL",
                 'embed_field': None},
                id='null_set'
            ),
            param(
                # Meta `fields` functions in root
                {'control_val': "NEW_VAL"},
                {'target': ContainerModel,
                 'meta_fields': ['control_val']},
                {'control_val': "NEW_VAL",
                 'embed_field': EmbedModel(
                     int_field=1234,
                     char_field="Embed"
                 )},
                id='respects_root_fields'
            ),
            param(
                # Meta `fields` functions in a nested model
                {'control_val': "NEW_VAL",
                 'embed_field': {
                     'int_field': 1470
                 }},
                {'target': ContainerModel,
                 'custom_fields': {
                     'embed_field': {
                         'target': EmbedModel,
                         'meta_fields': ['int_field']
                     }
                 }},
                {'control_val': "NEW_VAL",
                 'embed_field': EmbedModel(
                     int_field=1470,
                     char_field="Embed"
                 )},
                id='respects_deep_fields'
            ),
            param(
                # Meta `exclude` functions in root model
                {'embed_field': {
                    'int_field': 1369,
                    'char_field': "Baz",
                }},
                {'target': ContainerModel,
                 'meta_exclude': ['control_val']},
                {'control_val': "CONTROL",
                 'embed_field': EmbedModel(
                     int_field=1369,
                     char_field="Baz"
                 )},
                id='respects_root_exclude'
            ),
            param(
                # Meta `exclude` functions in a nested model
                {'control_val': "NEW_VAL",
                 'embed_field': {
                     'char_field': "Baz"
                 }},
                {'target': ContainerModel,
                 'custom_fields': {
                     'embed_field': {
                         'target': EmbedModel,
                         'meta_exclude': ['int_field']
                     }
                 }},
                {'control_val': "NEW_VAL",
                 'embed_field': EmbedModel(
                     int_field=1234,
                     char_field="Baz"
                 )},
                id='respects_deep_exclude'
            ),
        ])
    def test_valid_basic_update(self, build_serializer, instance_matches_data,
                                container_instance, update, serializer, expected):
        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(container_instance.container, data=update)

        # Confirm the serializer is valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer can save the new data
        instance = serializer.save()

        # Confirm that the update went as planned
        instance_matches_data(instance, expected)

    @mark.parametrize(
        ['update', 'serializer', 'error'],
        [
            param(
                # Missing value caught in root model
                {'embed_field': {
                    'int_field': 1357,
                    'char_field': "Bar"
                 }},
                {'target': ContainerModel,
                 'custom_fields': {
                     'control_val': CharField(required=True)
                 }},
                AssertionError,
                id='missing_root_value'
            ),
            param(
                # Missing value caught in deep model
                {'embed_field': {
                    'char_field': "Bar"
                }},
                {'target': ContainerModel},
                AssertionError,
                id='missing_deep_value'
            ),
            param(
                # Invalid values in the root model are caught
                {'control_val': "WAY_TOO_LONG",
                 'embed_field': {
                    'int_field': 1357,
                    'char_field': "Bar"
                 }},
                {'target': ContainerModel},
                AssertionError,
                id='invalid_root_value'
            ),
            param(
                # Invalid values in nested models are caught
                {'embed_field': {
                     'int_field': "Not_An_Int",
                     'char_field': "Bar"
                 }},
                {'target': ContainerModel},
                AssertionError,
                id='invalid_deep_value'
            ),
        ])
    def test_invalid_basic_update(self, build_serializer, instance_matches_data,
                                  container_instance, update, serializer, error):
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(container_instance.container, data=update)

        # Confirm that the serializer throws the designated error
        with raises(error):
            assert serializer.is_valid(), serializer.errors

            serializer.save()

    @mark.parametrize(
        ["update", "serializer", "expected"],
        [
            param(
                # Generic test
                {'str_id': "new_id",
                 'deep_embed': {
                    'embed_field': {
                        'int_field': 1357,
                        'char_field': "Bar"
                    }
                 }},
                {'target': DeepContainerModel},
                {'str_id': "new_id",
                 'deep_embed': ContainerModel(
                    control_val="CONTROL",
                    embed_field=EmbedModel(
                        int_field=1357,
                        char_field="Bar"
                    )
                 )},
                id='basic'
            ),
            param(
                # Intermediate `fields` respected
                {'str_id': "new_id",
                 'deep_embed': {
                     'control_val': "NEW_VAL"
                 }},
                {'target': DeepContainerModel,
                 'custom_fields': {
                     'deep_embed': {
                         'target': ContainerModel,
                         'meta_fields': ['control_val']
                     }
                 }},
                {'str_id': "new_id",
                 'deep_embed': ContainerModel(
                     control_val="NEW_VAL",
                     embed_field=EmbedModel(
                         int_field=1234,
                         char_field="Embed"
                     )
                 )},
                id='respects_intermediate_fields'
            ),
            param(
                # Intermediate `exclude` respected
                {'str_id': "new_id",
                 'deep_embed': {
                     'control_val': "NEW_VAL"
                 }},
                {'target': DeepContainerModel,
                 'custom_fields': {
                     'deep_embed': {
                         'target': ContainerModel,
                         'meta_exclude': ['embed_field']
                     }
                 }},
                {'str_id': "new_id",
                 'deep_embed': ContainerModel(
                     control_val="NEW_VAL",
                     embed_field=EmbedModel(
                         int_field=1234,
                         char_field="Embed"
                     )
                 )},
                id='respects_intermediate_exclude'
            ),
        ])
    def test_valid_deep_update(self, build_serializer, instance_matches_data,
                               deep_container_instance, update, serializer,
                               expected):
        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(deep_container_instance.deep_container,
                                    data=update)

        # Confirm that serializer data is valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer can save the data
        instance = serializer.save()

        # Confirm that the update went as planned
        instance_matches_data(instance, expected)

    @mark.parametrize(
        ["update", "serializer", "error"],
        [
            param(
                # Missing fields are caught (root field)
                {'deep_embed': {
                    'embed_field': {
                        'int_field': 1357,
                        'char_field': "Bar"
                    }
                }},
                {'target': DeepContainerModel},
                AssertionError,
                id="root_missing"
            ),
            param(
                # Missing fields are caught (intermediate field)
                {'str_id': "identifier",
                 'deep_embed': {
                     'embed_field': {
                         'int_field': 1357,
                         'char_field': "Baz"
                     }
                 }},
                {'target': DeepContainerModel,
                 'custom_fields': {
                     'control_val': CharField(required=True)
                 }},
                AssertionError,
                id="intermediate_missing"
            ),
            param(
                # Missing fields are caught (deep field)
                {'str_id': "identifier",
                 'deep_embed': {
                     'embed_field': {
                         'char_field': "Baz"
                     }
                 }},
                {'target': DeepContainerModel},
                AssertionError,
                id="deep_missing"
            ),
            param(
                # Invalid fields are caught (root field)
                {'str_id': "very_very_very_long",
                 'deep_embed': {
                     'embed_field': {
                         'int_field': 1324,
                         'char_field': "Baz"
                     }
                 }},
                {'target': DeepContainerModel},
                AssertionError,
                id="root_invalid"
            ),
            param(
                # Invalid fields are caught (intermediate field)
                {'str_id': "identifier",
                 'deep_embed': {
                     'embed_field': 1324
                 }},
                {'target': DeepContainerModel},
                AssertionError,
                id="intermediate_invalid"
            ),
            param(
                # Invalid fields are caught (deep field)
                {'str_id': "intermediate",
                 'deep_embed': {
                     'embed_field': {
                         'int_field': "Wrong",
                         'char_field': "Baz"
                     }
                 }},
                {'target': DeepContainerModel},
                AssertionError,
                id="deep_invalid"
            ),
        ])
    def test_invalid_update(self, build_serializer, instance_matches_data,
                            deep_container_instance, update, serializer, error):
        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(deep_container_instance.deep_container,
                                    data=update)

        with raises(error):
            # Confirm that serializer data is valid
            assert serializer.is_valid(), serializer.errors

            # Confirm that the serializer can save the data
            serializer.save()

    @mark.parametrize(
        ["update", "serializer", "expected"],
        [
            param(
                # Generic test (root fields)
                {'embed_field': {
                    'char_field': "Baz",
                    'int_field': 1324
                }},
                {'target': ContainerModel},
                {'control_val': "CONTROL",
                 'embed_field': EmbedModel(
                     int_field=1324,
                     char_field="Baz"
                 )},
                id="basic_root"
            ),
            param(
                # Generic test (deep fields)
                {'embed_field': {
                    'int_field': 1324
                }},
                {'target': ContainerModel},
                {'control_val': "CONTROL",
                 'embed_field': EmbedModel(
                     int_field=1324,
                     char_field='Embed'
                 )},
                id="basic_root"
            ),
        ])
    def test_valid_basic_partial_update(self, build_serializer,
                                        instance_matches_data,
                                        container_instance,
                                        update, serializer, expected):
        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(container_instance.container,
                                    data=update, partial=True)

        # Confirm that serializer data is valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer can save the data
        instance = serializer.save()

        # Confirm that the update went as planned
        instance_matches_data(instance, expected)

    @mark.parametrize(
        ["update", "serializer", "expected"],
        [
            param(
                # Generic test (root fields)
                {'deep_embed': {
                    'embed_field': {
                        'char_field': "Baz",
                        'int_field': 1324
                    }
                }},
                {'target': DeepContainerModel},
                {'control_val': "CONTROL",
                 'deep_embed': ContainerModel(
                     control_val="CONTROL",
                     embed_field=EmbedModel(
                         int_field=1324,
                         char_field="Baz"
                     )
                 )},
                id="basic_root"
            ),
            param(
                # Generic test (intermediate fields)
                {'deep_embed': {
                    'control_val': "NEW_VAL"
                }},
                {'target': DeepContainerModel},
                {'control_val': "CONTROL",
                 'deep_embed': ContainerModel(
                     control_val="NEW_VAL",
                     embed_field=EmbedModel(
                         int_field=1234,
                         char_field='Embed'
                     )
                 )},
                id="basic_intermediate"
            ),
            param(
                # Generic test (intermediate fields)
                {'deep_embed': {
                    'embed_field': {
                        'int_field': 1324
                    }
                }},
                {'target': DeepContainerModel},
                {'control_val': "CONTROL",
                 'deep_embed': ContainerModel(
                     control_val="CONTROL",
                     embed_field=EmbedModel(
                         int_field=1324,
                         char_field='Embed'
                     )
                 )},
                id="basic_deep"
            ),
        ])
    def test_valid_deep_partial_update(self, build_serializer,
                                        instance_matches_data,
                                        deep_container_instance,
                                        update, serializer, expected):
        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(deep_container_instance.deep_container,
                                    data=update, partial=True)

        # Confirm that serializer data is valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer can save the data
        instance = serializer.save()

        # Confirm that the update went as planned
        instance_matches_data(instance, expected)

    @mark.parametrize(
        ['update', 'serializer', 'error'],
        [
            param(
                # Invalid fields are caught (root field)
                {'str_id': "very_very_very_long"},
                {'target': DeepContainerModel},
                AssertionError,
                id="root_invalid"
            ),
            param(
                # Invalid fields are caught (intermediate field)
                {'deep_embed': {
                    'control_field': "NEW_VAL",
                    'embed_field': 1324,
                }},
                {'target': DeepContainerModel},
                AssertionError,
                id="intermediate_invalid"
            ),
            param(
                # Invalid fields are caught (deep field)
                {'deep_embed': {
                    'control_field': "NEW_VAL",
                    'embed_field': {
                        'int_field': "NOT_AN_INT",
                        'char_field': "Foo"
                    },
                }},
                {'target': DeepContainerModel},
                AssertionError,
                id="deep_invalid"
            ),
        ]
    )
    def test_invalid_partial_update(self, build_serializer,
                                    instance_matches_data,
                                    deep_container_instance,
                                    update, serializer, error):
        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(deep_container_instance.deep_container,
                                    data=update, partial=True)

        with raises(error):
            assert serializer.is_valid(), serializer.errors

            # Confirm that the serializer can save the data
            serializer.save()
