"""
test_util_functions
-------------------

Tests functions used exclusively by serializers (namely value checks)
"""

from bson import ObjectId
import uuid

from django.test import TestCase

from rest_meets_djongo import serializers as rmd_ser

from tests import serializers as test_sers, models as test_models


class TestNestedWriteChecks(TestCase):

    class TestSerializer(rmd_ser.DjongoModelSerializer):
        class Meta:
            model = test_models.GenericModel
            fields = '__all__'

    test_serializer = TestSerializer()

    generic_obj_data = {
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
        'ip':  '127.01.01',
        'uuid': uuid.uuid1(),
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
        class TestSerializer(rmd_ser.DjongoModelSerializer):
            class Meta:
                model = test_models.GenericModel
                fields = '__all__'

        test_serializer = TestSerializer()

        generic_obj_data = {
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
        }

        rmd_ser.raise_errors_on_nested_writes(
            'create', test_serializer, generic_obj_data
        )

    # def test_nest_field(self):
    #     rmd_ser.raise_errors_on_nested_writes(
    #         'update', self.nested_ser, self.nested_obj_data
    #     )


