from bson import ObjectId
from bson.errors import InvalidId
from django.core.exceptions import ValidationError
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _
from djongo import models
from rest_framework import serializers


class ObjectIdField(serializers.Field):
    """ Serializer field for Djongo ObjectID fields """

    def to_internal_value(self, data):
        try:
            return ObjectId(smart_text(data))
        except InvalidId:
            raise serializers.ValidationError(
                '`{}` is not a valid ObjectID'.format(data)
            )

    def to_representation(self, value):
        return smart_text(value)


class DjongoModelField(serializers.Field):
    """ Full replacement of DRF's ModelField for Djongo fields

    Tracks and monitors underlying model field, for later use

    Also used to map unknown fields within a DjongoModelSerializer, if
    any happen to be found
    """

    def __init__(self, model_field, **kwargs):
        self.model_field = model_field
        super(DjongoModelField, self).__init__(**kwargs)

    def get_attribute(self, instance):
        return instance

    def to_internal_value(self, data):
        """ Convert the data into the relevant python class instance

        Utilizes Djongo field overrides, when possible, converting from
        a dict into a new object instance
        """
        return self.model_field.to_python(data)

    def to_representation(self, value):
        """ Converts the provided value into a serializable representation

        DRF ModelFields use 'value_to_string' for this, but Djongo fields
        lack this. Instead, we utilize smart_text to convert the object
        into text

        Note; the value in this case is an Object (the entity to be
        converted into a serializable form), NOT a primitive type. This
        means we are making an assumption on how the object is to be
        serialized (all fields which are read-only or read-write) until
        explicitly told otherwise by the user (via a serializer)
        """
        repr = self.model_field.__get__(value, None)
        return smart_text(repr, strings_only=True)

    def run_validators(self, value):
        """ Validate the provided values

        Borrows Djongo's validation for its fields
        """
        try:
            self.model_field.validate(value)
        except ValidationError as e:
            raise e.message
        super(DjongoModelField, self).run_validators(value)


class EmbeddedModelField(serializers.Field):
    """ Field for Djongo EmbeddedModels, without specialized functions

    Acts similarly to DictField, just with recursive checks for other
    Djongo fields
    """

    default_error_messages = {
        'not_a_dict': serializers.DictField.default_error_messages['not_a_dict'],
        'not_embed': _('Expected an EmbeddedModel, but got a "{input_type}"'),
    }

    def to_internal_value(self, data):
        raise NotImplementedError(
            '{cls}.to_internal_value() must be implemented.'.format(
                cls=self.__class__.__name__
            )
        )

    def to_representation(self, value):
        raise NotImplementedError(
            '{cls}.to_representation() must be implemented for field '
            '{field_name}. If you do not need to support write operations '
            'you probably want to subclass `ReadOnlyField` instead.'.format(
                cls=self.__class__.__name__,
                field_name=self.field_name,
            )
        )

