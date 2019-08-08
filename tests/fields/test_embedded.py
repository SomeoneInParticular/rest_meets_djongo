from rest_meets_djongo.fields import EmbeddedModelField
from rest_meets_djongo.meta_manager import get_model_meta

from tests.models import ContainerModel, EmbedModel

from pytest import fixture, mark


@mark.embed
class DataParsing(object):
    obj_data = {
        'int_field': 123,
        'char_field': "Hello"
    }

    instance = EmbedModel(**obj_data)
    djm_embed = get_model_meta(ContainerModel).get_field('embed_field')
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
    def test_invalid_rejection(self, error_raised):
        # Non-dictionary values are rejected
        not_a_dict = 1234

        with error_raised:
            self.rmd_embed.run_validation(not_a_dict)

        # Dictionaries denoting fields which do not exist are rejected
        wrong_dict = {
            'bool_field': True,
            'char_field': 'error'
        }

        with error_raised:
            self.rmd_embed.run_validation(wrong_dict)

