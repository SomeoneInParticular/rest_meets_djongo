from bson import ObjectId
from collections import OrderedDict
import uuid

from django.test import TestCase
import rest_framework.fields as drf_fields
import rest_framework.serializers as drf_ser

from rest_meets_djongo import fields as rmd_fields
from rest_meets_djongo import serializers as rmd_ser

import pytest
from tests import models as test_models
from .utils import expect_dict_to_str


class TestMapping(TestCase):
    def test_fwd_relation_mapping(self):
        """
        Confirm that the serializer still handles models which have
        relations to other models, w/o custom field selection
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            # DRF usually expects explicit field declaration:
            # Just to check, however, we'll try auto-building the fields
            class Meta:
                model = test_models.RelationContainerModel
                fields = '__all__'

        expected_dict = {
            'id': drf_fields.IntegerField(label='ID', read_only=True),
            'fk_field': 'PrimaryKeyRelatedField(queryset=GenericModel.objects.all())',
            'mfk_field': ('ManyRelatedField(child_relation='
                          'PrimaryKeyRelatedField(queryset='
                          'ReverseRelatedModel.objects.all(), '
                          'required=False), '
                          'required=False)'),
        }

        expect_str = expect_dict_to_str(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expect_str == observed_str

    def test_rvs_relation_mapping(self):
        """
        Confirm that the serializer still excludes reverse relations by
        default (they are hard to predict and create default uses for)
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):

            class Meta:
                model = test_models.ReverseRelatedModel
                fields = '__all__'

        expect_dict = {
            '_id': rmd_fields.ObjectIdField(read_only=True),
            # Reverse models are excluded by default (as they are difficult
            # to predict how they should be parsed)
        }

        expected_str = expect_dict_to_str(expect_dict)

        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_respects_fields(self):
        """
        Confirm that relations can still be ignored by not specifying
        them in the `fields` Meta parameter
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.RelationContainerModel
                fields = ['fk_field']

        expected_dict = {
            'fk_field': 'PrimaryKeyRelatedField(queryset=GenericModel.objects.all())',
        }

        expected_str = expect_dict_to_str(expected_dict)

        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str

    def test_respects_exclude(self):
        """
        Confirm that relations can still be ignored by specifying them
        in the `exclude` Meta parameter
        """
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.RelationContainerModel
                exclude = ['fk_field']

        expected_dict = {
            'id': drf_fields.IntegerField(label='ID', read_only=True),
            'mfk_field': ('ManyRelatedField(child_relation='
                          'PrimaryKeyRelatedField(queryset='
                          'ReverseRelatedModel.objects.all(), '
                          'required=False), '
                          'required=False)'),
        }

        expected_str = expect_dict_to_str(expected_dict)
        observed_str = str(TestSerializer().get_fields())

        assert expected_str == observed_str


class TestIntegration(TestCase):
    def test_root_retrieve(self):
        """
        Confirm that existing instances of models with relational fields
        can still be retrieved and serialized correctly when the user
        does not want nested representation (depth = 0)
        """
        # Set up the referenced model instances in the database
        relation_data = OrderedDict({
            'id': 999,
            'big_int': 1234567890,
            'bool': True,
            'char': 'Hello World',
            'comma_int': '1,234',
            'date': '1997-01-01',
            'date_time': '1997-01-01 12:34:05',
            'decimal': 1.2345,
            'email': 'generic@gen.gen',
            'float': 5.4321,
            'integer': -32145,
            'null_bool': None,
            'pos_int': 15423,
            'pos_small_int': 2,
            'slug': "HEADLINE: HELLO WORLD",
            'small_int': -1,
            'text': ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                     "Suspendisse blandit, lectus vitae hendrerit lacinia, ex "
                     "enim congue purus, efficitur suscipit mauris ligula vitae "
                     "nunc. Curabitur ultrices in elit in ornare. Aenean sit "
                     "amet ipsum in nulla tincidunt egestas. Suspendisse "
                     "convallis metus id nunc scelerisque condimentum. Vivamus "
                     "gravida hendrerit eleifend. Duis interdum orci sit amet "
                     "tortor sodales pulvinar. Pellentesque habitant morbi "
                     "tristique senectus et netus et malesuada fames ac turpis "
                     "egestas. Praesent pulvinar urna eget condimentum lacinia. "
                     "Praesent venenatis nisi sit amet ex hendrerit, quis "
                     "elementum augue condimentum. Fusce sed tortor et sem "
                     "ullamcorper viverra."),
            'time': '12:34:05',
            'url': 'https://lipsum.com/feed/html',
            'ip': '127.01.01',
            'uuid': uuid.uuid1(),
        })

        basic_instance = test_models.GenericModel.objects.create(
            **relation_data
        )

        mtm_instance = test_models.ReverseRelatedModel.objects.create(
            _id=ObjectId()
        )

        instance = test_models.RelationContainerModel.objects.create(
            fk_field=basic_instance,
            # Many-to-Many fields cannot be set at creation; see below
        )

        instance.mfk_field.add(mtm_instance)

        # Attempt to serialize the instance
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.RelationContainerModel
                fields = '__all__'
                depth = 0

        serializer = TestSerializer(instance)

        expect_data = {
            'id': instance.pk,
            'fk_field': basic_instance.pk,
            'mfk_field': [mtm_instance._id]
        }

        self.assertDictEqual(expect_data, serializer.data)

    def test_deep_retrieve(self):
        """
        Confirm that existing instances of models with relational fields
        can still be retrieved and serialized correctly, when the user
        wants nested representation (depth > 0)
        """
        # Set up the referenced model instances in the database
        generic_model_data = OrderedDict({
            'id': 999,
            'big_int': 1234567890,
            'bool': True,
            'char': 'Hello World',
            'comma_int': '1,234',
            'date': '1997-01-01',
            'date_time': '1997-01-01 12:34:05',
            'decimal': 1.2345,
            'email': 'generic@gen.gen',
            'float': 5.4321,
            'integer': -32145,
            'null_bool': None,
            'pos_int': 15423,
            'pos_small_int': 2,
            'slug': "HEADLINE: HELLO WORLD",
            'small_int': -1,
            'text': ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                     "Suspendisse blandit, lectus vitae hendrerit lacinia, ex "
                     "enim congue purus, efficitur suscipit mauris ligula vitae "
                     "nunc. Curabitur ultrices in elit in ornare. Aenean sit "
                     "amet ipsum in nulla tincidunt egestas. Suspendisse "
                     "convallis metus id nunc scelerisque condimentum. Vivamus "
                     "gravida hendrerit eleifend. Duis interdum orci sit amet "
                     "tortor sodales pulvinar. Pellentesque habitant morbi "
                     "tristique senectus et netus et malesuada fames ac turpis "
                     "egestas. Praesent pulvinar urna eget condimentum lacinia. "
                     "Praesent venenatis nisi sit amet ex hendrerit, quis "
                     "elementum augue condimentum. Fusce sed tortor et sem "
                     "ullamcorper viverra."),
            'time': '12:34:05',
            'url': 'https://lipsum.com/feed/html',
            'ip': '127.01.01',
            'uuid': uuid.uuid1(),
        })

        generic_instance = test_models.GenericModel.objects.create(
            **generic_model_data
        )

        generic_model_data.update({'id': generic_instance.pk})

        mtm_model_data = OrderedDict({
            '_id': str(ObjectId())
        })

        mtm_model_instance = test_models.ReverseRelatedModel.objects.create(
            **mtm_model_data
        )

        # Create the instance to serializer
        instance = test_models.RelationContainerModel.objects.create(
            fk_field=generic_instance,
            # Many-to-Many fields cannot be set at creation; see below
        )

        instance.mfk_field.add(mtm_model_instance)

        # Attempt to serialize the instance
        class RelModelSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.RelationContainerModel
                fields = '__all__'
                depth = 1

        serializer = RelModelSerializer(instance)

        # Rewrite the expected data in the serialized form, for comparision
        generic_model_data.update({
            'decimal': '1.23450',
            'uuid': str(generic_model_data['uuid']),
        })

        # Confirm the data was serialized as expected
        expected_data = {
            'id': instance.pk,
            'fk_field': generic_model_data,
            'mfk_field': [mtm_model_data]
        }

        expected_str = expect_dict_to_str(expected_data)
        observed_str = str(serializer.data)

        assert expected_str == observed_str

    def test_root_create(self):
        """
        Confirm that new instances of models with relational fields can
        still be generated and saved correctly from raw data, given
        the the user does not want nested representation (depth = 0)
        """
        # Set up the referenced model instances in the database
        generic_data = {
            'big_int': 1234567890,
            'bool': True,
            'char': 'Hello World',
            'comma_int': '1,234',
            'date': '1997-01-01',
            'date_time': '1997-01-01 12:34:05',
            'decimal': 12.345,
            'email': 'generic@gen.gen',
            'float': 5.4321,
            'integer': -32145,
            'null_bool': None,
            'pos_int': 15423,
            'pos_small_int': 2,
            'slug': "HEADLINE: HELLO WORLD",
            'small_int': -1,
            'text': ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                     "Suspendisse blandit, lectus vitae hendrerit lacinia, ex "
                     "enim congue purus, efficitur suscipit mauris ligula vitae "
                     "nunc. Curabitur ultrices in elit in ornare. Aenean sit "
                     "amet ipsum in nulla tincidunt egestas. Suspendisse "
                     "convallis metus id nunc scelerisque condimentum. Vivamus "
                     "gravida hendrerit eleifend. Duis interdum orci sit amet "
                     "tortor sodales pulvinar. Pellentesque habitant morbi "
                     "tristique senectus et netus et malesuada fames ac turpis "
                     "egestas. Praesent pulvinar urna eget condimentum lacinia. "
                     "Praesent venenatis nisi sit amet ex hendrerit, quis "
                     "elementum augue condimentum. Fusce sed tortor et sem "
                     "ullamcorper viverra."),
            'time': '12:34:05',
            'url': 'https://lipsum.com/feed/html',
            'ip': '127.01.01',
            'uuid': uuid.uuid1(),
        }

        generic_instance = test_models.GenericModel.objects.create(**generic_data)

        generic_data.update({'pk': generic_instance.pk})

        # Create the serializer and the data it should use to create an object
        class RelModelSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.RelationContainerModel
                fields = '__all__'

        data = {
            'fk_field': generic_instance.pk,
            # Directly setting Many-to-Many fields is prohibited
            #  we test this field later, in test_relation_update
        }

        # Confirm that the serializer sees valid data as valid
        serializer = RelModelSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        # Confirm that this data can be saved
        instance = serializer.save()
        assert instance.fk_field.pk == generic_data['pk']
        assert instance.fk_field.comma_int == generic_data['comma_int']

    def test_deep_create(self):
        """
        Confirm that attempting to save a nested serialization of a
        a relation will fail by default (as is the case in DRF), but
        providing an explicit serializer overrides this
        """
        # Set up the referenced model instances in the database
        generic_data = {
            'big_int': 1234567890,
            'bool': True,
            'char': 'Hello World',
            'comma_int': '1,234',
            'date': '1997-01-01',
            'date_time': '1997-01-01 12:34:05',
            'decimal': 12.345,
            'email': 'generic@gen.gen',
            'float': 5.4321,
            'integer': -32145,
            'null_bool': None,
            'pos_int': 15423,
            'pos_small_int': 2,
            'slug': "HEADLINE: HELLO WORLD",
            'small_int': -1,
            'text': ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                     "Suspendisse blandit, lectus vitae hendrerit lacinia, ex "
                     "enim congue purus, efficitur suscipit mauris ligula vitae "
                     "nunc. Curabitur ultrices in elit in ornare. Aenean sit "
                     "amet ipsum in nulla tincidunt egestas. Suspendisse "
                     "convallis metus id nunc scelerisque condimentum. Vivamus "
                     "gravida hendrerit eleifend. Duis interdum orci sit amet "
                     "tortor sodales pulvinar. Pellentesque habitant morbi "
                     "tristique senectus et netus et malesuada fames ac turpis "
                     "egestas. Praesent pulvinar urna eget condimentum lacinia. "
                     "Praesent venenatis nisi sit amet ex hendrerit, quis "
                     "elementum augue condimentum. Fusce sed tortor et sem "
                     "ullamcorper viverra."),
            'time': '12:34:05',
            'url': 'https://lipsum.com/feed/html',
            'ip': '127.01.01',
            'uuid': uuid.uuid1(),
        }

        generic_instance = test_models.GenericModel.objects.create(**generic_data)

        generic_data.update({'pk': generic_instance.pk})

        mfk_data = {'_id': ObjectId()}

        mfk_instance = test_models.ReverseRelatedModel.objects.create(**mfk_data)

        mfk_data.update({'pk': mfk_instance.pk})

        # Initial serializer with read-only default
        class InitialTestSerializer(rmd_ser.DjongoModelSerializer):
            # Writable relation fields require explicit field creation in DRF
            class Meta:
                model = test_models.RelationContainerModel
                fields = '__all__'
                depth = 1

        data = {
            'fk_field': generic_instance.pk,
            'mfk_field': [mfk_instance.pk]
        }

        # Confirm that the serializer sees valid data as valid
        serializer = InitialTestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        # Foreign keys should have been stripped during validation
        self.assertDictEqual(serializer.validated_data, {})

        # Confirm that the data can still be saved, just without
        # reference data
        instance = serializer.save()

        # Confirm that the instance does not, in fact, have those fields
        # One-to-one/many fields do not get object managers
        assert getattr(instance, 'fk_field', None) is None

        # Many-to-one/many fields get object managers
        assert list(instance.mfk_field.all()) == []

        # Confirm that this default read-only setup can be overridden
        class NewTestSerializer(rmd_ser.DjongoModelSerializer):
            fk_field = drf_ser.PrimaryKeyRelatedField(
                queryset=test_models.GenericModel.objects.all()
            )

            class Meta:
                model = test_models.RelationContainerModel
                fields = '__all__'
                depth = 1

        # Confirm the serializer still regards this data as valid
        serializer = NewTestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer can still be saved correctly
        instance = serializer.save()

        # Confirm that the instance now has an updated fk_field
        assert instance.fk_field == generic_instance

    def test_root_update(self):
        """
        Confirm that updates are allowed for depth = 0 level fields, via
        the user pointing one-to-one/many fields to the intended new
        object (which should be updated and managed directly by
        another serializer)
        """
        # Set up the referenced model instances in the database
        old_generic_data = OrderedDict({
            'id': 999,
            'big_int': 1234567890,
            'bool': True,
            'char': 'Hello World',
            'comma_int': '1,234',
            'date': '1997-01-01',
            'date_time': '1997-01-01 12:34:05',
            'decimal': 1.2345,
            'email': 'generic@gen.gen',
            'float': 5.4321,
            'integer': -32145,
            'null_bool': None,
            'pos_int': 15423,
            'pos_small_int': 2,
            'slug': "HEADLINE: HELLO WORLD",
            'small_int': -1,
            'text': ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                     "Suspendisse blandit, lectus vitae hendrerit lacinia, ex "
                     "enim congue purus, efficitur suscipit mauris ligula vitae "
                     "nunc. Curabitur ultrices in elit in ornare. Aenean sit "
                     "amet ipsum in nulla tincidunt egestas. Suspendisse "
                     "convallis metus id nunc scelerisque condimentum. Vivamus "
                     "gravida hendrerit eleifend. Duis interdum orci sit amet "
                     "tortor sodales pulvinar. Pellentesque habitant morbi "
                     "tristique senectus et netus et malesuada fames ac turpis "
                     "egestas. Praesent pulvinar urna eget condimentum lacinia. "
                     "Praesent venenatis nisi sit amet ex hendrerit, quis "
                     "elementum augue condimentum. Fusce sed tortor et sem "
                     "ullamcorper viverra."),
            'time': '12:34:05',
            'url': 'https://lipsum.com/feed/html',
            'ip': '127.01.01',
            'uuid': uuid.uuid1(),
        })

        generic_instance = test_models.GenericModel.objects.create(
            **old_generic_data
        )

        # Preserve the pk for later checks
        old_generic_data.update({
            'pk': generic_instance.pk
        })

        mfk_data = {
            '_id': ObjectId()
        }

        mfk_instance = test_models.ReverseRelatedModel.objects.create(**mfk_data)

        old_data = {
            'fk_field': generic_instance
        }

        # Create the initial, to be updated, instance
        instance = test_models.RelationContainerModel.objects.create(**old_data)

        instance.mfk_field.add(mfk_instance)

        old_data.update({
            'pk': instance.pk,
            'mfk_field': list(instance.mfk_field.all())
        })

        # Try to perform an instance update
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.RelationContainerModel
                fields = '__all__'

        new_generic_data = old_generic_data.copy()
        new_generic_data.update({
            'id': 123,
            'float': 3.141392,
            'date': '2019-06-11'
        })
        new_generic_data.pop('pk')

        new_generic_instance = test_models.GenericModel.objects.create(
            **new_generic_data
        )

        new_generic_data.update({
            'pk': new_generic_instance.pk
        })

        new_data = {
            'fk_field': new_generic_instance.pk,
            # Many-to-one/many cannot be updated directly; trying to do
            # so will throw an error
        }

        serializer = TestSerializer(instance, data=new_data)

        # Serializer should be valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves this correctly
        serializer.save()
        assert instance.pk == old_data['pk']
        assert instance.fk_field.pk == new_generic_data['pk']
        assert instance.fk_field.float == new_generic_data['float']
        assert [e.pk for e in instance.mfk_field.all()] == [mfk_instance.pk]

    def test_nest_update(self):
        """
        Confirm that updates are NOT allowed for depth > 0 level fields
        by default, though the user can specify an override which would
        allow them to be
        """
        # Set up the referenced model instances in the database
        old_generic_data = OrderedDict({
            'id': 999,
            'big_int': 1234567890,
            'bool': True,
            'char': 'Hello World',
            'comma_int': '1,234',
            'date': '1997-01-01',
            'date_time': '1997-01-01 12:34:05',
            'decimal': 1.2345,
            'email': 'generic@gen.gen',
            'float': 5.4321,
            'integer': -32145,
            'null_bool': None,
            'pos_int': 15423,
            'pos_small_int': 2,
            'slug': "HEADLINE: HELLO WORLD",
            'small_int': -1,
            'text': ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                     "Suspendisse blandit, lectus vitae hendrerit lacinia, ex "
                     "enim congue purus, efficitur suscipit mauris ligula vitae "
                     "nunc. Curabitur ultrices in elit in ornare. Aenean sit "
                     "amet ipsum in nulla tincidunt egestas. Suspendisse "
                     "convallis metus id nunc scelerisque condimentum. Vivamus "
                     "gravida hendrerit eleifend. Duis interdum orci sit amet "
                     "tortor sodales pulvinar. Pellentesque habitant morbi "
                     "tristique senectus et netus et malesuada fames ac turpis "
                     "egestas. Praesent pulvinar urna eget condimentum lacinia. "
                     "Praesent venenatis nisi sit amet ex hendrerit, quis "
                     "elementum augue condimentum. Fusce sed tortor et sem "
                     "ullamcorper viverra."),
            'time': '12:34:05',
            'url': 'https://lipsum.com/feed/html',
            'ip': '127.01.01',
            'uuid': uuid.uuid1(),
        })

        generic_instance = test_models.GenericModel.objects.create(
            **old_generic_data
        )

        # Preserve the pk for later checks
        old_generic_data.update({
            'pk': generic_instance.pk
        })

        mfk_data = {
            '_id': ObjectId()
        }

        mfk_instance = test_models.ReverseRelatedModel.objects.create(**mfk_data)

        old_data = {
            'fk_field': generic_instance
        }

        # Create the initial, to be updated, instance
        instance = test_models.RelationContainerModel.objects.create(**old_data)

        instance.mfk_field.add(mfk_instance)

        old_data.update({
            'pk': instance.pk,
            'mfk_field': list(instance.mfk_field.all())
        })

        # Try to perform an instance update
        class OldTestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.RelationContainerModel
                fields = '__all__'
                depth = 1

        new_generic_data = old_generic_data.copy()
        new_generic_data.update({
            'id': 123,
            'float': 3.141392,
            'date': '2019-06-11'
        })
        new_generic_data.pop('pk')

        new_generic_instance = test_models.GenericModel.objects.create(
            **new_generic_data
        )

        new_generic_data.update({
            'pk': new_generic_instance.pk
        })

        new_data = {
            'fk_field': new_generic_instance.pk,
            # Many-to-one/many cannot be updated directly; trying to do
            # so will throw an error
        }

        serializer = OldTestSerializer(instance, data=new_data)

        # Serializer should be valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves this correctly, without
        # updating fk_field
        serializer.save()
        assert instance.pk == old_data['pk']
        assert instance.fk_field.pk == old_generic_data['pk']
        assert instance.fk_field.float == old_generic_data['float']
        assert [e.pk for e in instance.mfk_field.all()] == [mfk_instance.pk]

        # Try to update again, with an explicitly declared field which
        # is writable
        class NewTestSerializer(rmd_ser.DjongoModelSerializer):
            fk_field = drf_ser.PrimaryKeyRelatedField(
                queryset=test_models.GenericModel.objects.all(),
                read_only=False
            )

            class Meta:
                model = test_models.RelationContainerModel
                fields = '__all__'
                depth = 1

        serializer = NewTestSerializer(instance, data=new_data)

        # Serializer should be valid
        assert serializer.is_valid(), serializer.errors

        # Confirm that the serializer saves this correctly, without
        # updating fk_field
        serializer.save()
        assert instance.pk == old_data['pk']
        assert instance.fk_field.pk == new_generic_data['pk']
        assert instance.fk_field.float == new_generic_data['float']
        assert [e.pk for e in instance.mfk_field.all()] == [mfk_instance.pk]
