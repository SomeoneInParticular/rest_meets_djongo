from django.test import TestCase
from djongo import models as djm_models

from rest_meets_djongo import meta_manager

from tests import models as test_models


class TestMetaManager(TestCase):

    basic_model = test_models.GenericModel()
    obj_id_pk_model = test_models.ObjIDModel()
    relation_model = test_models.RelationContainerModel()
    embed_model = test_models.ContainerModel()

    def test_get_model_meta(self):
        """
        Here just to throw an error if Django changes how meta is accessed
        """
        test_meta = meta_manager.get_model_meta(self.basic_model)
        real_meta = self.basic_model._meta

        assert test_meta.__eq__(real_meta)

    def test_get_generic_model_field_info(self):
        """
        Confirm that models with only basic field types are properly managed
        """
        field_info = meta_manager.get_field_info(self.basic_model)

        # Confirm that the automatically generated 'pk' field was captured
        assert field_info.pk.name == 'id'
        assert isinstance(field_info.pk, djm_models.AutoField)

        # Confirm that the float and date field were both captured correctly
        field_type_dict = {
            'big_int': djm_models.BigIntegerField,
            'bool': djm_models.BooleanField,
            'char': djm_models.CharField,
            'comma_int': djm_models.CommaSeparatedIntegerField,
            'date': djm_models.DateField,
            'date_time': djm_models.DateTimeField,
            'decimal': djm_models.DecimalField,
            'email': djm_models.EmailField,
            'float': djm_models.FloatField,
            'integer': djm_models.IntegerField,
            'null_bool': djm_models.NullBooleanField,
            'pos_int': djm_models.PositiveIntegerField,
            'pos_small_int': djm_models.PositiveSmallIntegerField,
            'slug': djm_models.SlugField,
            'small_int': djm_models.SmallIntegerField,
            'text': djm_models.TextField,
            'time': djm_models.TimeField,
            'url': djm_models.URLField,
            'ip': djm_models.GenericIPAddressField,
            'uuid': djm_models.UUIDField,
        }

        for key, val in field_type_dict.items():
            assert isinstance(field_info.fields[key], val)

        # Confirm that the fields_and_pk parameter is built correctly
        field_and_pk_type_dict = {
            'pk': djm_models.AutoField,
            'id': djm_models.AutoField,
            'big_int': djm_models.BigIntegerField,
            'bool': djm_models.BooleanField,
            'char': djm_models.CharField,
            'comma_int': djm_models.CommaSeparatedIntegerField,
            'date': djm_models.DateField,
            'date_time': djm_models.DateTimeField,
            'decimal': djm_models.DecimalField,
            'email': djm_models.EmailField,
            'float': djm_models.FloatField,
            'integer': djm_models.IntegerField,
            'null_bool': djm_models.NullBooleanField,
            'pos_int': djm_models.PositiveIntegerField,
            'pos_small_int': djm_models.PositiveSmallIntegerField,
            'slug': djm_models.SlugField,
            'small_int': djm_models.SmallIntegerField,
            'text': djm_models.TextField,
            'time': djm_models.TimeField,
            'url': djm_models.URLField,
            'ip': djm_models.GenericIPAddressField,
            'uuid': djm_models.UUIDField,
        }

        for key, val in field_and_pk_type_dict.items():
            assert isinstance(field_info.fields_and_pk[key], val)

    def test_get_field_info_unique_pk(self):
        """
        Confirm that, if the pk is explicitly set in a model, it is caught
        and sorted correctly when fetching field info for said model
        """
        field_info = meta_manager.get_field_info(self.obj_id_pk_model)

        # Confirm that the user specified PK was caught
        assert field_info.pk.name == '_id'  # Custom name specified by user
        assert isinstance(field_info.pk, djm_models.ObjectIdField)

        # Confirm that the unique pk is still excluded from the fields
        assert '_id' not in field_info.fields

        # Confirm that said pk is still caught in fields_and_pk
        assert '_id' in field_info.fields_and_pk
        assert field_info.fields_and_pk['pk'].name == '_id'

    def test_get_fk_relation_field_info(self):
        """
        Tests that one-to-many relation information is correctly sorted
        and managed by the get_field_info() function
        """
        field_info = meta_manager.get_field_info(self.relation_model)

        # Confirm that the one-to-many relation was handled correctly
        fk_field_info = field_info.relations['fk_field']
        assert isinstance(fk_field_info.model_field, djm_models.ForeignKey)
        assert fk_field_info.related_model == test_models.GenericModel
        assert not fk_field_info.to_many
        assert (fk_field_info.to_field == 'id')  # Primary key auto-selected
        assert not fk_field_info.has_through_model
        assert not fk_field_info.reverse

    def test_get_mtm_relation_field_info(self):
        """
        Tests that many-to-many relation information is correctly sorted
        and managed by the get_field_info() function
        """
        field_info = meta_manager.get_field_info(self.relation_model)

        # Confirm that the one-to-many relation was handled correctly
        mfk_field_info = field_info.relations['mfk_field']
        assert isinstance(mfk_field_info.model_field, djm_models.ManyToManyField)
        assert mfk_field_info.related_model == test_models.ReverseRelatedModel
        assert mfk_field_info.to_many
        # Many-to-Many fields lack a `to_field` pointer
        assert not mfk_field_info.has_through_model
        assert not mfk_field_info.reverse

    def test_get_embed_model_field_info(self):
        """
        Tests that embedded model fields are correctly caught and managed
        """
        field_info = meta_manager.get_field_info(self.embed_model)

        # Confirm that embedded model info was caught correctly
        embed_field_info = field_info.embedded['embed_field']
        assert embed_field_info.model_field.model_container == test_models.EmbedModel
        assert not embed_field_info.is_array


