from collections import OrderedDict

import rest_framework.fields as drf_fields
from rest_framework.serializers import PrimaryKeyRelatedField

from rest_meets_djongo import fields as rmd_fields
from rest_meets_djongo.serializers import DjongoModelSerializer

from tests.models import \
    ManyToManyRelatedModel, RelationContainerModel, ForeignKeyRelatedModel
from pytest import fixture, mark, raises


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
            'control_val': drf_fields.CharField(max_length=20,
                                                required=False),
            'fk_field': ('PrimaryKeyRelatedField('
                         'queryset=ForeignKeyRelatedModel.objects.all())'),
            'mfk_field': ('ManyRelatedField(child_relation='
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
            'control_val': drf_fields.CharField(max_length=20,
                                                required=False),
            'mfk_field': ('ManyRelatedField(child_relation='
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
            'control_val': drf_fields.CharField(max_length=20,
                                                required=False),
            'fk_field': ('PrimaryKeyRelatedField('
                         'queryset=ForeignKeyRelatedModel.objects.all())'),
            'mfk_field': ('ManyRelatedField(child_relation='
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
    # -- DB Setup fixtures -- #
    @fixture
    def foreign_fixture(self):
        """Prepares a default ForeignKeyRelatedModel instance in the DB"""
        init = {
            'null_bool': True,
            'description':
                'A generic instance of the ForeignKeyRelatedModel'
        }

        instance = ForeignKeyRelatedModel.objects.create(**init)
        data = {'_id': str(instance.pk)}
        data.update(init)

        return data, instance

    @fixture
    def manytomany_fixture(self):
        """Prepares a default ForeignKeyRelatedModel instance in the DB"""
        init = {
            'boolean': False,
            'smol_int': 2
        }

        instance = ManyToManyRelatedModel.objects.create(**init)
        data = {'_id': str(instance.pk)}
        data.update(init)

        return data, instance

    @fixture
    def prep_db(self, foreign_fixture, manytomany_fixture):
        """Prepare the database for the classes' database"""
        from collections import namedtuple

        TestTuple = namedtuple('TestTuple', ['data', 'instance'])

        fk_tuple = TestTuple(*foreign_fixture)
        mtm_tuple = TestTuple(*manytomany_fixture)

        return fk_tuple, mtm_tuple

    # -- Actual test code -- #
    def test_root_retrieve(self, assert_dict_equals, prep_db):
        """
        Confirm that existing instances of models with relational fields
        can still be retrieved and serialized correctly when the user
        does not want nested representation (depth = 0)
        """
        fk_tuple, mtm_tuple = prep_db

        instance = RelationContainerModel.objects.create(
            fk_field=fk_tuple.instance,
            # Many-to-Many fields cannot be set at creation; see below
        )

        instance.mfk_field.add(mtm_tuple.instance)

        # Attempt to serialize the instance
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = RelationContainerModel
                fields = '__all__'
                depth = 0

        serializer = TestSerializer(instance)

        expect_data = {
            '_id': str(instance.pk),
            'control_val': 'CONTROL',
            'fk_field': fk_tuple.instance.pk,
            'mfk_field': [mtm_tuple.instance.pk]
        }

        assert_dict_equals(expect_data, serializer.data)

    def test_deep_retrieve(self, assert_dict_equals, prep_db):
        """
        Confirm that existing instances of models with relational fields
        can still be retrieved and serialized correctly, when the user
        wants nested representation (depth > 0)
        """
        fk_tuple, mtm_tuple = prep_db

        # Create the instance to serializer
        instance = RelationContainerModel.objects.create(
            fk_field=fk_tuple.instance,
            # Many-to-Many fields cannot be set at creation; see below
        )

        instance.mfk_field.add(mtm_tuple.instance)

        # Attempt to serialize the instance
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = RelationContainerModel
                fields = '__all__'
                depth = 1

        serializer = TestSerializer(instance)

        # Confirm the data was serialized as expected
        expected_data = {
            '_id': str(instance.pk),
            'control_val': 'CONTROL',
            'fk_field': OrderedDict(fk_tuple.data),
            'mfk_field': [OrderedDict(mtm_tuple.data)]
        }

        assert_dict_equals(serializer.data, expected_data)

    def test_root_create(self, instance_matches_data, prep_db):
        """
        Confirm that new instances of models with relational fields can
        still be generated and saved correctly from raw data, given
        the the user does not want nested representation (depth = 0)
        """
        fk_tuple, mtm_tuple = prep_db

        # Create the serializer and the data it should use to create an object
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = RelationContainerModel
                fields = '__all__'

        data = {
            'fk_field': fk_tuple.instance.pk,
            # Directly setting Many-to-Many fields is prohibited
        }

        # Confirm that the serializer sees valid data as valid
        serializer = TestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        # Serializer should be able to save valid data correctly
        instance = serializer.save()

        expect_dict = {
            'fk_field': fk_tuple.instance,
            'control_val': 'CONTROL',
        }

        # Confirm that the instance contains the correct data
        instance_matches_data(instance, data=expect_dict)

    def test_deep_create(self, instance_matches_data, prep_db):
        """
        Confirm that attempting to save a nested serialization of a
        a relation will fail by default (as is the case in DRF)
        """
        fk_tuple, mtm_tuple = prep_db

        # Create the serializer and data it should use to create an object
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = RelationContainerModel
                fields = '__all__'
                depth = 1

        data = {
            'fk_field': fk_tuple.instance,
            # Directly setting Many-to-Many fields is prohibited
        }

        # Confirm that the serializer sees valid data as valid
        serializer = TestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        # Confirm the serializer still saves, just sans relation value
        instance = serializer.save()

        expect_dict = {
            'control_val': 'CONTROL',
            'fk_field_id': None  # Pointer exists, but points to nothing
        }

        instance_matches_data(instance, expect_dict)

        # fk_field should not exist, as the pk to generate it was not used
        with raises(AssertionError) as err:
            expect_dict = {'fk_field': fk_tuple.instance}
            instance_matches_data(instance, expect_dict)

    def test_custom_create(self, instance_matches_data, prep_db):
        """
        Confirm that default, read-only fields can be overridden by the
        user to allow for writable instances, just like DRF
        """
        fk_tuple, mtm_tuple = prep_db

        # Create the serializer and the data it should use to create an object
        class TestSerializer(DjongoModelSerializer):
            fk_field = PrimaryKeyRelatedField(
                queryset=ForeignKeyRelatedModel.objects.all()
            )

            class Meta:
                model = RelationContainerModel
                fields = '__all__'
                depth = 1

        data = {
            'fk_field': fk_tuple.instance.pk
        }

        # Confirm the serializer still regards this data as valid
        serializer = TestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer now saves w/ relation data
        instance = serializer.save()

        expected_data = {
            'fk_field': fk_tuple.instance
        }

        instance_matches_data(instance, expected_data)

    def test_root_update(self, instance_matches_data, prep_db):
        """
        Confirm that updates to what an object relates too  are allowed
        for depth = 0 level fields, via the user pointing one-to-one/many
        fields to the intended new object
        """
        fk_tuple, mtm_tuple = prep_db

        old_data = {
            'fk_field': fk_tuple.instance
        }

        # Create the initial, to be updated, instance
        instance = RelationContainerModel.objects.create(**old_data)

        instance.mfk_field.add(mtm_tuple.instance)

        old_data.update({
            '_id': instance.pk,
            'mfk_field': list(instance.mfk_field.all())
        })

        # Prepare data to update the instance with
        new_fk_data = fk_tuple.data.copy()
        new_fk_data.update({
            'null_bool': None,
            'description': "An alternative instance"
        })
        new_fk_data.pop('_id')

        new_fk_instance = ForeignKeyRelatedModel.objects.create(
            **new_fk_data
        )

        new_data = {
            'fk_field': new_fk_instance.pk,
            # Many-to-one/many cannot be updated directly by default
        }

        # Try to perform an instance update
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = RelationContainerModel
                fields = '__all__'

        serializer = TestSerializer(instance, data=new_data)

        # Serializer should be valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves this correctly
        instance = serializer.save()

        expected_data = {
            '_id': old_data['_id'],
            'fk_field': new_fk_instance,
            'control_val': 'CONTROL'
        }

        instance_matches_data(instance, expected_data)

        # Special case: Many-to-Many fields are auto-generated managers
        assert list(instance.mfk_field.all()) == old_data['mfk_field']

    def test_deep_update(self, instance_matches_data, prep_db):
        """
        Confirm that updates are NOT allowed for depth > 0 level fields
        by default, though non-relational fields remain able to update
        """
        # Set up the referenced model instances in the database
        fk_tuple, mtm_tuple = prep_db

        old_data = {
            'fk_field': fk_tuple.instance
        }

        # Create the initial, to be updated, instance
        instance = RelationContainerModel.objects.create(**old_data)

        instance.mfk_field.add(mtm_tuple.instance)

        old_data.update({
            '_id': instance.pk,
            'mfk_field': list(instance.mfk_field.all())
        })

        # Prepare data to update the instance with
        new_fk_data = fk_tuple.data.copy()
        new_fk_data.update({
            'null_bool': None,
            'description': "An alternative instance"
        })
        new_fk_data.pop('_id')

        new_fk_instance = ForeignKeyRelatedModel.objects.create(
            **new_fk_data
        )

        new_data = {
            'fk_field': new_fk_instance.pk,
            'control_val': "NEW CONTROL"
        }

        # Try to perform an instance update
        class TestSerializer(DjongoModelSerializer):
            class Meta:
                model = RelationContainerModel
                fields = '__all__'
                depth = 1

        serializer = TestSerializer(instance, data=new_data)

        # Serializer should be valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves updated data
        instance = serializer.save()

        expected_data = {
            '_id': old_data['_id'],
            'fk_field_id': str(fk_tuple.instance.pk),
            'control_val': 'NEW CONTROL'
        }

        instance_matches_data(instance, expected_data)

        # Confirm that fk_field was NOT updated
        with raises(AssertionError):
            expected_data = {'fk_field': new_fk_instance}
            instance_matches_data(instance, expected_data)

    def test_custom_update(self, instance_matches_data, prep_db):
        """
        Confirm that default, read-only fields can be overridden by the
        user to allow for updating instances, just like DRF
        """
        fk_tuple, mtm_tuple = prep_db

        old_data = {
            'fk_field': fk_tuple.instance
        }

        # Create the initial, to be updated, instance
        instance = RelationContainerModel.objects.create(**old_data)

        instance.mfk_field.add(mtm_tuple.instance)

        old_data.update({
            '_id': instance.pk,
            'mfk_field': list(instance.mfk_field.all())
        })

        # Prepare data to update the instance with
        new_fk_data = fk_tuple.data.copy()
        new_fk_data.update({
            'null_bool': None,
            'description': "An alternative instance"
        })
        new_fk_data.pop('_id')

        new_fk_instance = ForeignKeyRelatedModel.objects.create(
            **new_fk_data
        )

        new_data = {
            'fk_field': new_fk_instance.pk,
            'control_val': "NEW CONTROL"
        }

        # Try to perform an instance update
        class TestSerializer(DjongoModelSerializer):
            fk_field = PrimaryKeyRelatedField(
                queryset=ForeignKeyRelatedModel.objects.all()
            )

            class Meta:
                model = RelationContainerModel
                fields = '__all__'
                depth = 1

        serializer = TestSerializer(instance, data=new_data)

        # Serializer should be valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves this correctly
        instance = serializer.save()

        expected_data = {
            '_id': old_data['_id'],
            'fk_field': new_fk_instance,
            'control_val': 'NEW CONTROL'
        }

        instance_matches_data(instance, expected_data)

        # Special case: Many-to-Many fields are auto-generated managers
        assert list(instance.mfk_field.all()) == old_data['mfk_field']
