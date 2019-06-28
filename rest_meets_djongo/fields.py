from bson import ObjectId
from bson.errors import InvalidId

from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _
from djongo import models
from rest_framework import serializers


class ObjectIdField(serializers.Field):
    """ Serializer int_field for Djongo ObjectID fields """

    def to_internal_value(self, data):
        try:
            return ObjectId(smart_text(data))
        except InvalidId:
            raise serializers.ValidationError(
                '`{}` is not a valid ObjectID'.format(data)
            )

    def to_representation(self, value):
        if not ObjectId.is_valid(value):
            raise InvalidId
        return smart_text(value)


class DjongoField(serializers.Field):
    """ Full replacement of DRF's ModelField for Djongo fields

    Tracks and monitors an underlying model int_field, for later use

    Also used to map unknown fields within a DjongoModelSerializer, if
    any happen to be found (this may be the case in the period between
    Djongo updating and us updating to compensate, or in the case of
    custom fields added by the user)
    """

    def __init__(self, model_field, **kwargs):
        self.model_field = model_field
        super(DjongoField, self).__init__(**kwargs)

    def get_attribute(self, instance):
        return instance

    def to_internal_value(self, data):
        """ Convert the data into the relevant python class instance

        Utilizes Djongo int_field overriding, when needed, converting from
        a dict into a new object instance in that situation
        """
        return self.model_field.to_python(data)

    def to_representation(self, value):
        """ Converts the provided value into a serializable representation

        DRF ModelFields use 'value_to_string' for this, but Djongo fields
        lack this. Instead, we utilize smart_text to convert the object
        into text.

        We also check our model_field for validation on

        Note; the value in this case is an Object (the entity to be
        converted into a serializable form), NOT a primitive type. This
        means we are making an assumption on how the object is to be
        serialized (all fields which are read-only or read-write) until
        explicitly told otherwise by the user (via a serializer)
        """
        return smart_text(value, strings_only=True)

    def run_validators(self, value):
        """ Validate the provided values

        Borrows Djongo's field validation for this procedure, as well
        as natively added validators for the field, if any (the latter
        simply catches errors which are not implicitly validation-type
        errors, IE attempts to convert Char -> Int)
        """
        self.model_field.run_validators(value)
        super(DjongoField, self).run_validators(value)


class EmbeddedModelField(serializers.Field):
    """ Field for Djongo EmbeddedModel fields, without specialized
    functions

    Acts similarly to DictField, with reliance on the passed in model
    (model_field) to aid in conversion to the embedded model (borrowing
    its constructor to do so)

    Used internally by EmbeddedModelSerializer to map EmbeddedModels
    which do not have an explicit serializer attached to them
    """

    def __init__(self, model_field, **kwargs):
        if not isinstance(model_field, models.EmbeddedModelField):
            raise TypeError(
                "Tried to initialize a RMD `EmbeddedModelField` with a "
                "`{}` type model_field".format(
                    type(model_field).__name__
                ))
        self.model_field = model_field
        super(EmbeddedModelField, self).__init__(**kwargs)

    default_error_messages = {
        'not_a_dict': serializers.DictField.default_error_messages['not_a_dict'],
        'not_model': _('Expected a Model instance, but got `{input_cls}`'),
    }

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            self.fail('not_a_dict', input_type=type(data).__name__)
        model_class = self.model_field.model_container
        return model_class(**data)

    def to_representation(self, value):
        if not isinstance(value, models.Model):
            self.fail('not_model', input_cls=type(value).__name__)

        fields = self.model_field.model_container._meta.get_fields()
        data = {}

        for field in fields:
            name = field.name
            data[name] = getattr(value, name, None)

        return data


class ArrayModelField(serializers.Field):
    """ Field for Djongo ArrayModelFields, without specialized functions

    Acts akin to a DRF List field, using the passed in model (model_field)
    to aid in the conversion to the listed model and back

    Used internally for RMD serializers later, primarily for mapping fields
    which do not have explicit serialization set up already
    """
    def __init__(self, model_field, **kwargs):
        if not isinstance(model_field, models.ArrayModelField):
            raise TypeError(
                "Tried to initialize a RMD `ArrayModelField` with a "
                "`{}` type model_field".format(
                    type(model_field).__name__
                ))
        self.model_field = model_field
        super(ArrayModelField, self).__init__(**kwargs)

    default_error_messages = {
        'not_a_list': _('Expected a list of objects, but got `{input_class}`'),
    }

    def to_internal_value(self, data):
        if not isinstance(data, list):
            self.fail('not_a_list', input_class=type(data).__name__)
        model_class = self.model_field.model_container
        val_list = []
        for datum in data:
            val_list.append(model_class(**datum))
        return val_list

    def to_representation(self, value):
        if not isinstance(value, list):
            self.fail('not_a_list', input_class=type(value).__name__)
        fields = self.model_field.model_container._meta.get_fields()
        data_list = []
        for val in value:
            data = {}
            for field in fields:
                name = field.name
                data[name] = getattr(val, name, None)
            data_list.append(data)

        return data_list

