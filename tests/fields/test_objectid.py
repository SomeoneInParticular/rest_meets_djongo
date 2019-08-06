"""
test_objectidfield
------------------

Tests DRF serialization for Djongo ObjectID type fields
"""

from rest_meets_djongo.fields import ObjectIdField

from pytest import fixture, mark, raises


@mark.basic
@mark.field
class TestObjectIDField(object):

    field = ObjectIdField()

    @fixture(scope='class')
    def object_id(self):
        from bson import ObjectId
        return ObjectId()

    @fixture(scope='class')
    def errors(self, build_tuple):
        from bson.errors import InvalidId
        from rest_framework.exceptions import ValidationError

        err_dict = {
            'InvalidId': InvalidId,
            'ValidationError': ValidationError
        }
        return build_tuple('Errors', err_dict)

    def test_to_internal_value(self, object_id):
        """
        For object ID fields, the internal value should be an ObjectID
        object, appropriately formatted w/ MongoDB's setup.

        We use an ObjectID key generated by Djongo previously, uti lizing its
        ObjectIDField (for models) to do so
        """
        new_obj = self.field.to_internal_value(str(object_id))

        assert new_obj.__eq__(object_id)

    def test_to_representation(self, object_id):
        """
        Confirm that object ID objects can still be reconstructed once
        serialized. This allows for them to be used as primary key queries
        by DRF (I.E. '/students/5d08078b1f7eb051eafe2390')
        """
        ref_id = str(object_id)
        obj_id = self.field.to_representation(object_id)

        assert ref_id == obj_id

    def test_conversion_equivalence(self, object_id):
        """
        Confirm that serialization and de-serialization of ObjectIDs is a
        lossless operation (and thus its use won't create unexpected
        behaviours) by default.
        """
        obj_repr = self.field.to_representation(object_id)
        new_obj = self.field.to_internal_value(obj_repr)

        assert object_id.__eq__(new_obj)

    @mark.error
    def test_invalid_rejection(self, errors):
        """
        Confirm that invalid ObjectID values are rejected when
        attempting to serialize them
        """
        bad_key = "wrong"  # Too short, also incorrect format

        with raises(errors.ValidationError):
            self.field.to_internal_value(bad_key)

        not_a_key = dict()  # Not an ObjectID or string-representation of one

        with raises(errors.InvalidId):
            self.field.to_representation(not_a_key)