from rest_meets_djongo.fields import ArrayModelField
from rest_meets_djongo.meta_manager import get_model_meta

from tests.models import ArrayContainerModel, EmbedModel

from pytest import mark


@mark.compound
@mark.embed
@mark.field
class TestDataParsing(object):

    embed_data = [
        {'int_field': 34, 'char_field': "Hello"},
        {'int_field': 431, 'char_field': "Bye!"}
    ]

    embed_list = [EmbedModel(**val) for val in embed_data]

    instance = ArrayContainerModel(embed_list=embed_list)

    array_field = ArrayModelField(
        model_field=get_model_meta(instance).get_field('embed_list')
    )

    def test_to_internal_val(self):
        new_list = self.array_field.to_internal_value(self.embed_data)

        assert self.embed_list == new_list

    def test_to_representation(self):
        new_list = self.array_field.to_representation(self.embed_list)

        assert self.embed_data == new_list

    def test_conversion_equivalence(self):
        rep_list = self.array_field.to_representation(self.embed_list)
        new_list = self.array_field.to_internal_value(rep_list)

        assert self.embed_list == new_list

    @mark.error
    def test_invalid_rejection(self, error_raised):
        # Non-list values are caught
        not_a_list = 1234
        with error_raised:
            self.array_field.run_validation(not_a_list)

        # List contents with invalid fields are caught
        invalid_list_field = self.embed_data.copy()
        invalid_list_field.append({'int_field': 34, 'bool_field': True})
        with error_raised:
            self.array_field.run_validation(invalid_list_field)
