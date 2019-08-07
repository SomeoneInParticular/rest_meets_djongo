from rest_meets_djongo.fields import ArrayModelField
from rest_meets_djongo.meta_manager import get_model_meta

from tests.models import ArrayContainerModel, EmbedModel

from pytest import mark


@mark.compound
@mark.embed
class TestArrayModelField(object):

    val_list = [
        {'int_field': 34, 'char_field': "Hello"},
        {'int_field': 431, 'char_field': "Bye!"}
    ]

    embed_list = [EmbedModel(**val) for val in val_list]

    instance = ArrayContainerModel(embed_list=embed_list)

    array_field = ArrayModelField(
        model_field=get_model_meta(instance).get_field('embed_list')
    )

    def test_to_internal_val(self):
        new_list = self.array_field.to_internal_value(self.val_list)

        assert self.embed_list == new_list

    def test_to_representation(self):
        new_list = self.array_field.to_representation(self.embed_list)

        assert self.val_list == new_list

    def test_conversion_equivalence(self):
        rep_list = self.array_field.to_representation(self.embed_list)
        new_list = self.array_field.to_internal_value(rep_list)

        assert self.embed_list == new_list

    @mark.error
    def test_validation(self, raises):
        not_a_list = self.val_list[0]
        with raises.SerializerValidationError:
            self.array_field.to_internal_value(not_a_list)

        invalid_list_field = self.val_list.copy()
        invalid_list_field.append({'int_field': 34, 'bool_field': True})
        with raises.FieldDoesNotExist:
            self.array_field.to_internal_value(invalid_list_field)

        nest_field_invalid = self.val_list.copy()
        nest_field_invalid.append({'int_field': 34, 'char_field': "Hello World!"})
        with raises.SerializerValidationError as exc:
            self.array_field.to_internal_value(nest_field_invalid)
