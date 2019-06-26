"""
test_djongomodelfield
---------------------

Tests DRF serialization for our version of Model Fields,
DjongoModelField
"""

from django.core.exceptions import ValidationError
from django.test import TestCase
from djongo import models
from rest_framework import fields
import pytest

from rest_meets_djongo.fields import DjongoField


# Example model with which to use as the basis of serialization
class SampleModel(models.Model):
    _id = models.ObjectIdField()
    int_field = models.IntegerField()
    char_field = models.CharField(max_length=5)


class TestDjongoField(TestCase):
    int_field = DjongoField(model_field=SampleModel._meta.get_field('int_field'))
    char_field = DjongoField(model_field=SampleModel._meta.get_field('char_field'))

    def test_to_internal_value(self):
        """
        The int_field, bound to a underlying Djongo int_field, is mapped and
        interpreted as if it were that int_field

        Usually used as a last resort, primarily in the case of Djongo
        adding a new int_field type which has not yet been accommodated for
        in the package yet
        """
        obj = 14342

        obj_data = fields.IntegerField().to_internal_value(obj)
        new_data = self.int_field.to_internal_value(obj)

        assert obj_data == new_data

    def test_to_representation(self):
        """
        Confirm that the int_field can be serialized from it initial value
        """
        obj = 15465

        obj_val = fields.IntegerField().to_representation(obj)
        ref = self.int_field.to_representation(obj_val)

        assert ref.__eq__(obj)

    def test_conversion_equivalence(self):
        obj = 5465423

        obj_data = self.int_field.to_representation(obj)
        new_obj = self.int_field.to_internal_value(obj_data)

        assert obj.__eq__(new_obj)

    def test_invalid_rejection(self):
        bad_int = "100,543"

        with pytest.raises(ValidationError):
            self.int_field.to_internal_value(bad_int)

    def test_validation(self):
        invalid_val = "Hello World!"

        with pytest.raises(TypeError):
            self.int_field.run_validators(invalid_val)

        with pytest.raises(ValidationError):
            self.char_field.run_validators(invalid_val)
