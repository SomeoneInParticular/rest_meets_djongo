"""
test_embeddedmodelfield
-----------------------

Tests DRF serialization for EmbeddedModelFields
"""

from pytest import fixture, mark, raises

from rest_meets_djongo.fields import EmbeddedModelField
from tests.models import ContainerModel, EmbedModel


@mark.embed
class TestEmbeddedModelField(object):
    obj_data = {
        'int_field': 123,
        'char_field': "Hello"
    }

    instance = EmbedModel(**obj_data)
    djm_embed = ContainerModel._meta.get_field('embed_field')
    rmd_embed = EmbeddedModelField(model_field=djm_embed)

    @fixture
    def errors(self, build_tuple):
        from rest_framework.exceptions import ValidationError

        err_dict = {
            'ValidationError': ValidationError,
            'TypeError': TypeError
        }

        return build_tuple('Errors', err_dict)

    def test_to_internal_val(self):
        new_instance = self.rmd_embed.to_internal_value(self.obj_data)

        assert str(self.instance) == str(new_instance)

    def test_to_representation(self):
        new_data = self.rmd_embed.to_representation(self.instance)

        assert self.obj_data == new_data

    def test_conversion_equivalence(self):
        data = self.rmd_embed.to_representation(self.instance)
        new_instance = self.rmd_embed.to_internal_value(data)

        assert str(self.instance) == str(new_instance)

    @mark.error
    def test_validation(self, errors):
        """
        Confirm that invalid objects are rejected when trying to
        serialize/de-serialize in a field which was not build for them
        """
        # Non-models are rejected when attempting to serialize
        not_a_model = dict()

        with raises(errors.ValidationError):
            self.rmd_embed.to_representation(not_a_model)

        # Non-dictionary values are rejected when building instances
        not_a_dict = 1234

        with raises(errors.ValidationError):
            self.rmd_embed.to_internal_value(not_a_dict)

        # Models of the incorrect type are rejected
        wrong_model = ContainerModel()

        with raises(errors.ValidationError):
            self.rmd_embed.to_representation(wrong_model)

        # Dictionaries denoting fields which do not exist are rejected
        wrong_dict = {
            'bool_field': True,
            'char_field': 'error'
        }

        with raises(errors.TypeError):
            self.rmd_embed.to_internal_value(wrong_dict)

