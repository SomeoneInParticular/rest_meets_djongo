"""
test_arraymodelfield
--------------------

Test DRF serialization for Djongo ArrayModelFields
"""

from django.test import TestCase

from rest_meets_djongo.fields import ArrayModelField

from tests import models as test_models


class TestArrayModelField(TestCase):

    embed_model = test_models.EmbedModel
    contain_model = test_models.ArrayContainerModel

    val_list = [
        {'int_field': 34, 'char_field': "Hello There"},
        {'int_field': 431, 'char_field': "Goodbye!"}
    ]

    obj_list = [
        embed_model(**val_list[0]), embed_model(**val_list[1])
    ]

    array_field = ArrayModelField(
        model_field=contain_model._meta.get_field('embed_list')
    )

    def test_to_internal_val(self):
        new_list = self.array_field.to_internal_value(self.val_list)

        self.assertListEqual(self.obj_list, new_list)

    def test_to_representation(self):
        new_list = self.array_field.to_representation(self.obj_list)

        self.assertListEqual(self.val_list, new_list)

    def test_conversion_equivalence(self):
        interem_list = self.array_field.to_representation(self.obj_list)
        new_list = self.array_field.to_internal_value(interem_list)

        self.assertListEqual(self.obj_list, new_list)
