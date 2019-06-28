"""
test_arraymodelfield
--------------------

Test DRF serialization for Djongo ArrayModelFields
"""

from django.core.exceptions import ValidationError
from django.test import TestCase
from djongo import models
from rest_framework import fields
import pytest

from rest_meets_djongo.fields import ArrayModelField


# Model to be embedded in an array field of an outer model
class EmbedModel(models.Model):
    int_field = models.IntegerField()
    char_field = models.CharField(max_length=5)

    def __eq__(self, other):
        return (isinstance(other, EmbedModel) and
                self.char_field == other.char_field and
                self.int_field == other.int_field)

    class Meta:
        abstract = True


# The outer model mentioned prior
class OuterModel(models.Model):
    array_field = models.ArrayModelField(model_container=EmbedModel)


class TestArrayModelField(TestCase):
    val_list = [
        {'int_field': 34, 'char_field': "Hello There"},
        {'int_field': 431, 'char_field': "Goodbye!"}
    ]
    obj_list = [
        EmbedModel(**val_list[0]), EmbedModel(**val_list[1])
    ]
    array_field = ArrayModelField(model_field=OuterModel._meta.get_field('array_field'))

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
