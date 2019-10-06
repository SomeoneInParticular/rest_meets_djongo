from bson import ObjectId
from bson.errors import InvalidId

import rest_framework.fields as drf_fields
from rest_framework.serializers import PrimaryKeyRelatedField

from rest_meets_djongo import fields as rmd_fields
from rest_meets_djongo.serializers import DjongoModelSerializer

from tests.models import \
    ManyToManyRelatedModel, RelationContainerModel, ForeignKeyRelatedModel
from pytest import fixture, mark, raises, param


@mark.relation
@mark.mapping
@mark.serializer
class TestMapping(object):
    def test_fwd_relation_mapping(self, assert_dict_equals):
        """
        Confirm that the serializer still handles models which have
        relations to other models, w/o custom field selection
        """
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = RelationContainerModel
                fields = '__all__'

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'control_val': drf_fields.CharField(max_length=10,
                                                required=False),
            'fk_field': ('PrimaryKeyRelatedField('
                         'queryset=ForeignKeyRelatedModel.objects.all())'),
            'mtm_field': ('ManyRelatedField(child_relation='
                          'PrimaryKeyRelatedField(queryset='
                          'ManyToManyRelatedModel.objects.all(), '
                          'required=False), '
                          'required=False)'),
        }

        assert_dict_equals(expected_dict, TestSerializer().get_fields())

    def test_rvs_relation_ignored(self, assert_dict_equals):
        """
        Confirm that the serializer excludes reverse relations by
        default (they are hard to predict and create default uses with)
        """
        class TestSerializer(DjongoModelSerializer):

            class Meta:
                model = ManyToManyRelatedModel
                fields = '__all__'

        expect_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'boolean': drf_fields.BooleanField(required=False),
            'smol_int': drf_fields.IntegerField(
                max_value=32767,
                min_value=-32768
            )
            # Reverse models are excluded by default
        }

        assert_dict_equals(expect_dict, TestSerializer().get_fields())

    def test_respects_fields(self, assert_dict_equals):
        """
        Confirm that relations can still be ignored by not specifying
        them in the `fields` Meta parameter
        """
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = RelationContainerModel
                fields = ['fk_field']

        expected_dict = {
            'fk_field': ('PrimaryKeyRelatedField('
                         'queryset=ForeignKeyRelatedModel.objects.all())'),
        }

        assert_dict_equals(expected_dict, TestSerializer().get_fields())

    def test_respects_exclude(self, assert_dict_equals):
        """
        Confirm that relations can still be ignored by specifying them
        in the `exclude` Meta parameter
        """
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = RelationContainerModel
                exclude = ['fk_field']

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'control_val': drf_fields.CharField(max_length=10,
                                                required=False),
            'mtm_field': ('ManyRelatedField(child_relation='
                          'PrimaryKeyRelatedField(queryset='
                          'ManyToManyRelatedModel.objects.all(), '
                          'required=False), '
                          'required=False)'),
        }

        assert_dict_equals(expected_dict, TestSerializer().get_fields())

    @mark.django_db
    def test_missing_field_caught(self):
        """
        Confirm that failing to include an explicitly declared relation
        field in the serializer will throw an error
        """
        class TestSerializer(DjongoModelSerializer):
            missing = PrimaryKeyRelatedField(
                queryset=RelationContainerModel.objects.all()
            )

            class Meta:
                model = RelationContainerModel
                fields = ['_id']

        with raises(AssertionError):
            field_vals = TestSerializer().get_fields()
            print(field_vals)

    @mark.django_db
    def test_missing_inherited_field_ignorable(self, assert_dict_equals):
        """
        Confirm that fields declared in a parent serializer do not need
        to be declared in child serializers of that parent
        """
        class TestSerializer(DjongoModelSerializer):
            missing = PrimaryKeyRelatedField(
                queryset=RelationContainerModel.objects.all()
            )

            class Meta:
                model = RelationContainerModel
                fields = '__all__'

        class ChildSerializer(TestSerializer):
            class Meta(TestSerializer.Meta):
                fields = ['fk_field']

        expected_dict = {
            'fk_field': ('PrimaryKeyRelatedField('
                         'queryset=ForeignKeyRelatedModel.objects.all())'),
        }

        assert_dict_equals(ChildSerializer().get_fields(), expected_dict)

    @mark.django_db
    def test_inherited_field_nullable(self, assert_dict_equals):
        """
        Confirm that fields declared in a parent serializer can be set
        to null to ignore them in child serializers
        """
        class TestSerializer(DjongoModelSerializer):
            missing = PrimaryKeyRelatedField(
                queryset=RelationContainerModel.objects.all()
            )

            class Meta:
                model = RelationContainerModel
                fields = '__all__'

        class ChildSerializer(TestSerializer):
            missing = None

            class Meta(TestSerializer.Meta):
                pass

        expected_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            'control_val': drf_fields.CharField(max_length=10,
                                                required=False),
            'fk_field': ('PrimaryKeyRelatedField('
                         'queryset=ForeignKeyRelatedModel.objects.all())'),
            'mtm_field': ('ManyRelatedField(child_relation='
                          'PrimaryKeyRelatedField(queryset='
                          'ManyToManyRelatedModel.objects.all(), '
                          'required=False), '
                          'required=False)'),
        }

        assert_dict_equals(ChildSerializer().get_fields(), expected_dict)


@mark.relation
@mark.integration
@mark.serializer
@mark.django_db
class TestIntegration(object):
    # -- DB Setup Fixtures -- #
    @fixture
    def foreign_key_instance(self):
        """Prepares a default ForeignKeyRelatedModel instance in the DB"""
        foreign_key_data = {
            'null_bool': True,
            'description': 'A generic instance'
        }

        instance = ForeignKeyRelatedModel.objects.create(**foreign_key_data)
        return instance

    @fixture
    def alt_foreign_key_instance(self):
        """Prepares an alternative ForeignKeyRelatedModel instance"""
        foreign_key_data = {
            'null_bool': False,
            'description': 'An alternative instance'
        }

        instance = ForeignKeyRelatedModel.objects.create(**foreign_key_data)
        return instance

    @fixture
    def many_to_many_instances(self):
        """Prepares default ManyToManyRelatedModels instances in the DB"""
        many_to_many_data_1 = {
            'boolean': False,
            'smol_int': 2
        }
        many_to_many_data_2 = {
            'boolean': True,
            'smol_int': 4
        }

        instance1 = ManyToManyRelatedModel.objects.create(**many_to_many_data_1)
        instance2 = ManyToManyRelatedModel.objects.create(**many_to_many_data_2)
        return [instance1, instance2]

    @fixture
    def alt_many_to_many_instances(self):
        """Prepares alternative ManyToManyRelatedModels instances"""
        many_to_many_data_1 = {
            'boolean': False,
            'smol_int': 5
        }
        many_to_many_data_2 = {
            'boolean': False,
            'smol_int': 7
        }

        instance1 = ManyToManyRelatedModel.objects.create(**many_to_many_data_1)
        instance2 = ManyToManyRelatedModel.objects.create(**many_to_many_data_2)
        return [instance1, instance2]

    @fixture
    def container_instance(self, foreign_key_instance, many_to_many_instances):
        """Prepare the database for the test class"""
        container_instance = RelationContainerModel.objects.create(
            fk_field=foreign_key_instance,
        )

        container_instance.mtm_field.add(*many_to_many_instances)

        return container_instance

    @fixture
    def alt_container_instance(self, alt_foreign_key_instance,
                               alt_many_to_many_instances):
        """Prepare alternative entries in the database (for update testing)"""
        container_instance = RelationContainerModel.objects.create(
            fk_field=alt_foreign_key_instance,
        )

        container_instance.mtm_field.add(*alt_many_to_many_instances)

        return container_instance

    # -- Actual test code -- #
    @mark.parametrize(
        ["serializer", "expected", "missing"],
        [
            param(
                # Basic, root, retrieval test
                {'target': RelationContainerModel},
                {'control_val': "CONTROL",
                 'fk_field': "PK",
                 'mtm_field': "PK"},
                None,
                id='basic_root'
            ),
            param(
                # Basic, deep, retrieval test
                {'target': RelationContainerModel,
                 'relate_depth': 1},
                {'control_val': "CONTROL",
                 'fk_field': {
                     'null_bool': True,
                     'description': 'A generic instance'
                 },
                 'mtm_field': [
                     {
                         'boolean': False,
                         'smol_int': 2
                     },
                     {
                         'boolean': True,
                         'smol_int': 4
                     },
                 ]},
                None,
                id='basic_deep'
            ),
            param(
                # Meta Fields respected, root serialization
                {'target': RelationContainerModel,
                 'meta_fields': ['fk_field']},
                {'fk_field': "PK"},
                {'control_val': "CONTROL",
                 'mtm_field': "PK"},
                id='root_respects_fields'
            ),
            param(
                # Meta Fields respected, deep serialization
                {'target': RelationContainerModel,
                 'relate_depth': 1,
                 'meta_fields': ['fk_field']},
                {'fk_field': {
                     'null_bool': True,
                     'description': 'A generic instance'
                 }},
                {'control_val': "CONTROL",
                 'mtm_field': [
                     {
                         'boolean': False,
                         'smol_int': 2
                     },
                     {
                         'boolean': True,
                         'smol_int': 4
                     },
                 ]},
                id='deep_respects_fields'
            ),
            param(
                # Meta Exclude respected, root serialization
                {'target': RelationContainerModel,
                 'meta_exclude': ['fk_field']},
                {'control_val': "CONTROL",
                 'mtm_field': "PK"},
                {'fk_field': "PK"},
                id='root_respects_exclude'
            ),
            param(
                # Meta Fields respected, deep serialization
                {'target': RelationContainerModel,
                 'relate_depth': 1,
                 'meta_exclude': ['fk_field']},
                {'control_val': "CONTROL",
                 'mtm_field': [
                     {
                         'boolean': False,
                         'smol_int': 2
                     },
                     {
                         'boolean': True,
                         'smol_int': 4
                     },
                 ]},
                {'fk_field': {
                    'null_bool': True,
                    'description': 'A generic instance'
                }},
                id='deep_respects_exclude'
            ),
        ])
    def test_retrieve(self, build_serializer, does_a_subset_b,
                      container_instance, update_mono_relation,
                      update_many_relation, serializer, expected,
                      missing):
        # Insert instance data, if requested
        update_mono_relation(expected, ['fk_field'], container_instance)
        update_many_relation(expected, ['mtm_field'], container_instance)

        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(container_instance)

        # Make sure fields which should exist do
        if expected:
            does_a_subset_b(expected, serializer.data)

        # Make sure fields which should be ignored, are
        if missing:
            with raises(AssertionError):
                does_a_subset_b(missing, serializer.data)

    @mark.parametrize(
        ["initial", "serializer", "expected"],
        [
            param(
                # Basic test, root serializer
                # (many-to-many values, by default, are ignored)
                {'control_val': "NEW_VAL",
                 'fk_field': "PK"},
                # 'mtm_field' = "PK",
                {'target': RelationContainerModel},
                {'control_val': "NEW_VAL",
                 'fk_field': "PK"},
                id='basic_root'
            ),
            param(
                # Basic test, deep serializer
                {'control_val': "NEW_VAL",
                 'fk_field': "PK",  # Stripped during creation
                 'mtm_field': "PK"},
                {'target': RelationContainerModel,
                 'relate_depth': 1},
                {'control_val': "NEW_VAL",
                 'mtm_field': "RAW"},
                id='basic_deep'
            ),
            param(
                # Custom field test, w/ root serialization
                {'control_val': "NEW_VAL",
                 'fk_field': None},
                {'target': RelationContainerModel,
                 'custom_fields': {
                     'fk_field': PrimaryKeyRelatedField(
                         queryset=ForeignKeyRelatedModel.objects.all(),
                         allow_null=True
                     )
                 }},
                {'control_val': "NEW_VAL"},
                id='custom_root'
            ),
            param(
                # Custom field test, w/ deep serialization
                {'control_val': "NEW_VAL",
                 'fk_field': "PK",
                 'mtm_field': "PK"},
                {'target': RelationContainerModel,
                 'relate_depth': 1,
                 'custom_fields': {
                     'fk_field': PrimaryKeyRelatedField(
                         queryset=ForeignKeyRelatedModel.objects.all()
                     )}
                 },
                {'control_val': "NEW_VAL",
                 'fk_field': "PK",
                 'mtm_field': "RAW"},
                id='custom_deep'
            ),
        ])
    def test_valid_create(self, build_serializer, instance_matches_data,
                          container_instance, update_mono_relation,
                          update_many_relation, initial, serializer,
                          expected):
        # Prep data with DB values, if requested
        update_mono_relation(initial, ['fk_field'], container_instance)
        update_many_relation(initial, ['mtm_field'], container_instance)
        update_mono_relation(expected, ['fk_field'], container_instance)
        update_many_relation(expected, ['mtm_field'], container_instance)

        # Prepare the test environment
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
                # Fields of the wrong type are caught (root serialization)
                {'control_val': "NEW_VAL",
                 'fk_field': "INVALID"},
                # 'mtm_field' = "PK",
                {'target': RelationContainerModel},
                InvalidId,
                id='bad_type_root'
            ),
            # Deep serialization w/ DRF simply strips values;
            # it will NOT throw an error by default
            param(
                # Incorrect PK (root serialization)
                {'control_val': "NEW_VAL",
                 'fk_field': ObjectId()},
                # 'mtm_field' = "PK",
                {'target': RelationContainerModel},
                AssertionError,
                id='bad_pk_root'
            ),
            param(
                # Incorrect PK (deep custom serialization)
                {'control_val': "NEW_VAL",
                 'fk_field': ObjectId()},
                # 'mtm_field' = "PK",
                {'target': RelationContainerModel,
                 'relate_depth': 1,
                 'custom_fields': {
                     'fk_field': PrimaryKeyRelatedField(
                         queryset=ForeignKeyRelatedModel.objects.all()
                     )}
                 },
                AssertionError,
                id='bad_pk_deep_custom'
            ),
        ]
    )
    def test_invalid_create(self, build_serializer, instance_matches_data,
                            container_instance, initial, serializer, error):
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
                # Generic test (root)
                {'control_val': "NEW_VAL",
                 'fk_field': "PK"},
                # 'mtm_field': "PK"
                {'target': RelationContainerModel},
                {'control_val': "NEW_VAL",
                 'fk_field': "PK"},
                id='basic_root'
            ),
            param(
                # Generic test (root)
                {'control_val': "NEW_VAL",
                 # 'fk_field': "PK",
                 'mtm_field': "PK"},
                {'target': RelationContainerModel,
                 'relate_depth': 1},
                {'control_val': "NEW_VAL",
                 'mtm_field': "RAW"},
                id='basic_deep'
            ),
        ]
    )
    def test_valid_update(self, build_serializer, instance_matches_data,
                          container_instance, alt_container_instance,
                          update_mono_relation, update_many_relation,
                          update, serializer, expected):
        # Prep data with DB values, if requested
        update_mono_relation(update, ['fk_field'], alt_container_instance)
        update_many_relation(update, ['mtm_field'], alt_container_instance)
        update_mono_relation(expected, ['fk_field'], alt_container_instance)
        update_many_relation(expected, ['mtm_field'], alt_container_instance)

        # Prepare the test environment
        TestSerializer, _ = build_serializer(**serializer)
        serializer = TestSerializer(container_instance, data=update)

        # Confirm the serializer is valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer can save the new data
        instance = serializer.save()

        # Confirm that the update went as planned
        instance_matches_data(instance, expected)

    # def test_root_update(self, instance_matches_data, prep_db):
    #     """
    #     Confirm that updates to what an object relates too  are allowed
    #     for depth = 0 level fields, via the user pointing one-to-one/many
    #     fields to the intended new object
    #     """
    #     fk_tuple, mtm_tuple = prep_db
    #
    #     old_data = {
    #         'fk_field': fk_tuple.instance
    #     }
    #
    #     # Create the initial, to be updated, instance
    #     instance = RelationContainerModel.objects.create(**old_data)
    #
    #     instance.mfk_field.add(mtm_tuple.instance)
    #
    #     old_data.update({
    #         '_id': instance.pk,
    #         'mfk_field': list(instance.mfk_field.all())
    #     })
    #
    #     # Prepare data to update the instance with
    #     new_fk_data = fk_tuple.data.copy()
    #     new_fk_data.update({
    #         'null_bool': None,
    #         'description': "An alternative instance"
    #     })
    #     new_fk_data.pop('_id')
    #
    #     new_fk_instance = ForeignKeyRelatedModel.objects.create(
    #         **new_fk_data
    #     )
    #
    #     new_data = {
    #         'fk_field': new_fk_instance.pk,
    #         # Many-to-one/many cannot be updated directly by default
    #     }
    #
    #     # Try to perform an instance update
    #     class TestSerializer(DjongoModelSerializer):
    #         class Meta:
    #             model = RelationContainerModel
    #             fields = '__all__'
    #
    #     serializer = TestSerializer(instance, data=new_data)
    #
    #     # Serializer should be valid
    #     assert serializer.is_valid(), serializer.errors
    #
    #     # Confirm that the serializer saves this correctly
    #     instance = serializer.save()
    #
    #     expected_data = {
    #         '_id': old_data['_id'],
    #         'fk_field': new_fk_instance,
    #         'control_val': 'CONTROL'
    #     }
    #
    #     instance_matches_data(instance, expected_data)
    #
    #     # Special case: Many-to-Many fields are auto-generated managers
    #     assert list(instance.mfk_field.all()) == old_data['mfk_field']
    #
    # def test_deep_update(self, instance_matches_data, prep_db):
    #     """
    #     Confirm that updates are NOT allowed for depth > 0 level fields
    #     by default, though non-relational fields remain able to update
    #     """
    #     # Set up the referenced model instances in the database
    #     fk_tuple, mtm_tuple = prep_db
    #
    #     old_data = {
    #         'fk_field': fk_tuple.instance
    #     }
    #
    #     # Create the initial, to be updated, instance
    #     instance = RelationContainerModel.objects.create(**old_data)
    #
    #     instance.mfk_field.add(mtm_tuple.instance)
    #
    #     old_data.update({
    #         '_id': instance.pk,
    #         'mfk_field': list(instance.mfk_field.all())
    #     })
    #
    #     # Prepare data to update the instance with
    #     new_fk_data = fk_tuple.data.copy()
    #     new_fk_data.update({
    #         'null_bool': None,
    #         'description': "An alternative instance"
    #     })
    #     new_fk_data.pop('_id')
    #
    #     new_fk_instance = ForeignKeyRelatedModel.objects.create(
    #         **new_fk_data
    #     )
    #
    #     new_data = {
    #         'fk_field': new_fk_instance.pk,
    #         'control_val': "NEW CONTROL"
    #     }
    #
    #     # Try to perform an instance update
    #     class TestSerializer(DjongoModelSerializer):
    #         class Meta:
    #             model = RelationContainerModel
    #             fields = '__all__'
    #             depth = 1
    #
    #     serializer = TestSerializer(instance, data=new_data)
    #
    #     # Serializer should be valid
    #     assert serializer.is_valid(), serializer.errors
    #
    #     # Confirm that the serializer saves updated data
    #     instance = serializer.save()
    #
    #     expected_data = {
    #         '_id': old_data['_id'],
    #         'fk_field_id': str(fk_tuple.instance.pk),
    #         'control_val': 'NEW CONTROL'
    #     }
    #
    #     instance_matches_data(instance, expected_data)
    #
    #     # Confirm that fk_field was NOT updated
    #     with raises(AssertionError):
    #         expected_data = {'fk_field': new_fk_instance}
    #         instance_matches_data(instance, expected_data)
    #
    # def test_custom_update(self, instance_matches_data, prep_db):
    #     """
    #     Confirm that default, read-only fields can be overridden by the
    #     user to allow for updating instances, just like DRF
    #     """
    #     fk_tuple, mtm_tuple = prep_db
    #
    #     old_data = {
    #         'fk_field': fk_tuple.instance
    #     }
    #
    #     # Create the initial, to be updated, instance
    #     instance = RelationContainerModel.objects.create(**old_data)
    #
    #     instance.mfk_field.add(mtm_tuple.instance)
    #
    #     old_data.update({
    #         '_id': instance.pk,
    #         'mfk_field': list(instance.mfk_field.all())
    #     })
    #
    #     # Prepare data to update the instance with
    #     new_fk_data = fk_tuple.data.copy()
    #     new_fk_data.update({
    #         'null_bool': None,
    #         'description': "An alternative instance"
    #     })
    #     new_fk_data.pop('_id')
    #
    #     new_fk_instance = ForeignKeyRelatedModel.objects.create(
    #         **new_fk_data
    #     )
    #
    #     new_data = {
    #         'fk_field': new_fk_instance.pk,
    #         'control_val': "NEW CONTROL"
    #     }
    #
    #     # Try to perform an instance update
    #     class TestSerializer(DjongoModelSerializer):
    #         fk_field = PrimaryKeyRelatedField(
    #             queryset=ForeignKeyRelatedModel.objects.all()
    #         )
    #
    #         class Meta:
    #             model = RelationContainerModel
    #             fields = '__all__'
    #             depth = 1
    #
    #     serializer = TestSerializer(instance, data=new_data)
    #
    #     # Serializer should be valid
    #     assert serializer.is_valid(), serializer.errors
    #
    #     # Confirm that the serializer saves this correctly
    #     instance = serializer.save()
    #
    #     expected_data = {
    #         '_id': old_data['_id'],
    #         'fk_field': new_fk_instance,
    #         'control_val': 'NEW CONTROL'
    #     }
    #
    #     instance_matches_data(instance, expected_data)
    #
    #     # Special case: Many-to-Many fields are auto-generated managers
    #     assert list(instance.mfk_field.all()) == old_data['mfk_field']
