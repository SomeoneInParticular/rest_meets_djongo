"""
test_util_functions
-------------------

Tests functions used exclusively by serializers (namely value checks)
"""

from bson import ObjectId

from django.test import TestCase

from rest_meets_djongo import serializers as rmd_serializers

from tests import serializers as test_sers, models as test_models


class TestNestedWriteChecks(TestCase):

    basic_ser = test_sers.GenericModelSerializer()
    generic_obj_data = {
        'float_field': 0.3123,
        'date_field': "1997-01-07"
    }

    nested_ser = test_sers.NestedModelSerializer()
    embed_obj_data = {
        'int_field': 31415,
        'char_field': 'Hello!'
    }

    nested_obj_data = {
        '_id': ObjectId(),
        'generic_val': test_models.GenericModel(**generic_obj_data),
        'embed_val': test_models.EmbedModel(**embed_obj_data)
    }

    def test_normal_field(self):
        rmd_serializers.raise_errors_on_nested_writes(
            'create', self.basic_ser, self.generic_obj_data
        )

    # def test_nest_field(self):
    #     rmd_serializers.raise_errors_on_nested_writes(
    #         'update', self.nested_ser, self.nested_obj_data
    #     )


