from rest_meets_djongo.fields import DjongoField
from rest_meets_djongo.meta_manager import get_model_meta

from tests.models import ObjIDModel

from pytest import fixture, mark


@mark.basic
@mark.core
class TestDataParsing(object):

    model_meta = get_model_meta(ObjIDModel())

    int_field = DjongoField(model_field=model_meta.get_field('int_field'))
    char_field = DjongoField(model_field=model_meta.get_field('char_field'))

    @fixture(scope='class')
    def drf_int_field(self):
        from rest_framework.fields import IntegerField
        return IntegerField()

    def test_to_internal_value(self, drf_int_field):
        """
        The int_field, bound to a underlying Djongo int_field, is mapped and
        interpreted as if it were that int_field

        Usually used as a last resort, primarily in the case of Djongo
        adding a new int_field type which has not yet been accommodated for
        in the package yet
        """
        int_val = 14342

        int_data = drf_int_field.to_internal_value(int_val)
        new_data = self.int_field.to_internal_value(int_val)

        assert int_data == new_data

    def test_to_representation(self, drf_int_field):
        """
        Confirm that the int_field can be serialized from it initial data
        """
        int_val = 15465

        interim = drf_int_field.to_representation(int_val)
        new_val = self.int_field.to_representation(interim)

        assert new_val.__eq__(int_val)

    def test_conversion_equivalence(self):
        """Confirm that serializing the data """
        int_val = 5465423

        rep_val = self.int_field.to_representation(int_val)
        new_val = self.int_field.to_internal_value(rep_val)

        assert int_val.__eq__(new_val)

    @mark.error
    def test_invalid_rejection(self, error_raised):
        # A non-integer parsable data
        invalid_val = "Hello"
        with error_raised:
            self.int_field.run_validators(invalid_val)

        # Integer larger than field allowed
        big_int = 9876543210
        with error_raised:
            self.int_field.run_validators(big_int)

        # Non-string field passed as string
        invalid_string = ObjIDModel()
        with error_raised:
            self.char_field.run_validators(invalid_string)

        # String too large for the field provided
        bad_string = "WAY TO LONG"
        with error_raised:
            self.char_field.run_validators(bad_string)

