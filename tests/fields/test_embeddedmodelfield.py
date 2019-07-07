"""
test_embeddedmodelfield
-----------------------

Tests DRF serialization for EmbeddedModelFields
"""

from django.test import TestCase

from rest_meets_djongo.fields import EmbeddedModelField

from tests.objects import models as test_models


class TestEmbeddedModelField(TestCase):
    obj_data = {
        'int_field': 123,
        'char_field': "Hello"
    }

    instance = test_models.EmbedModel(**obj_data)
    djm_embed_field = test_models.ContainerModel._meta.get_field('embed_field')
    rmd_embed_field = EmbeddedModelField(model_field=djm_embed_field)

    def test_to_internal_val(self):
        new_instance = self.rmd_embed_field.to_internal_value(self.obj_data)

        assert str(self.instance) == str(new_instance)

    def test_to_representation(self):
        new_data = self.rmd_embed_field.to_representation(self.instance)

        assert self.obj_data == new_data

    def test_conversion_equivalence(self):
        data = self.rmd_embed_field.to_representation(self.instance)
        new_instance = self.rmd_embed_field.to_internal_value(data)

        assert str(self.instance) == str(new_instance)

