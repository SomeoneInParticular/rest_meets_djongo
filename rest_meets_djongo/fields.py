from bson import ObjectId
from bson.errors import InvalidId

from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import FieldDoesNotExist
from django.core.exceptions import ValidationError as ModelValidationError
from djongo import models
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .meta_manager import get_model_meta


class ObjectIdField(serializers.Field):
    """
    Serializer field for Djongo ObjectID fields
    """
    def to_internal_value(self, data):
        """Serialized -> Database"""
        try:
            return ObjectId(str(data))
        except InvalidId:
            raise ValidationError(
                f'`{data}` is not a valid ObjectID'
            )

    def to_representation(self, value):
        """Database -> Serialized"""
        return smart_text(value)


class DjongoField(serializers.Field):
    """ Full replacement of DRF's ModelField for Djongo fields

    Tracks and monitors an underlying model_field, for later use with
    validation and conversion

    Used primarily to map unknown fields within a DjongoModelSerializer,
    if any happen to be found (this may be the case in the period
    between Djongo updating and us updating to compensate, or in the
    case of custom fields added by the user)
    """
    def __init__(self, model_field, **kwargs):
        self.model_field = model_field
        super(DjongoField, self).__init__(**kwargs)

    def get_attribute(self, instance):
        return instance

    def to_internal_value(self, data):
        """ Convert the data into the relevant python class instance

        Utilizes Djongo's field `to_python()`
        """
        try:
            return self.model_field.to_python(data)
        except TypeError as err:
            return ValidationError(err)

    def to_representation(self, value):
        """ Converts the provided data into a serializable representation

        DRF ModelFields use 'value_to_string' for this, but Djongo fields
        lack this. Instead, we utilize smart_text to convert the object
        into a textual representation.
        """
        return smart_text(value, strings_only=True)

    def run_validators(self, value):
        """ Validate the provided values

        Borrows Djongo's field validation for this procedure, as well
        as natively added validators for the field, if any (the latter
        simply catches errors which are not implicitly validation-type
        errors, IE attempts to convert String -> Integer)
        """
        try:
            self.model_field.run_validators(value)
        except ModelValidationError as err:
            raise ValidationError(err.messages)
        except TypeError as err:
            raise ValidationError(err)
        super(DjongoField, self).run_validators(value)


class EmbeddedModelField(serializers.Field):
    """ Generic field for Djongo EmbeddedModel fields

    Acts similarly to DictField, with reliance on the passed in model
    (model_field) to aid in conversion to correct model type (borrowing
    its constructor to do so)

    Used internally by EmbeddedModelSerializer to map EmbeddedModels
    which do not have an explicit serializer attached to them
    """
    default_error_messages = {
        'not_a_dict': serializers.DictField.default_error_messages['not_a_dict'],
        'not_model': _('Expected a Djongo model instance, found `{input_cls}`'),
        'wrong_model': _('Expected a `{target_cls}` instance, but found `{input_cls}`')
    }

    def __init__(self, model_field, **kwargs):
        if not isinstance(model_field, models.EmbeddedModelField):
            raise TypeError(
                "Tried to initialize a RMD `EmbeddedModelField` with a "
                "`{}` type model_field".format(
                    type(model_field).__name__
                ))
        self.model_field = model_field
        super(EmbeddedModelField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        """Serialized -> Database"""
        if not isinstance(data, dict):
            self.fail('not_a_dict', input_type=type(data).__name__)
        try:
            model_class = self.model_field.model_container
            return model_class(**data)
        except TypeError as err:
            raise ValidationError(err)

    def to_representation(self, value):
        """Database -> Serialized"""
        if not isinstance(value, models.Model):
            self.fail('not_model', input_cls=type(value).__name__)

        model_container = self.model_field.model_container
        if not isinstance(value, model_container):
            self.fail('wrong_model',
                      target_cls=model_container.__name__,
                      input_cls=type(value).__name__)

        fields = get_model_meta(model_container).get_fields()
        data = {}

        for field in fields:
            name = field.name
            data[name] = getattr(value, name, None)

        return data


class ArrayModelField(serializers.Field):
    """ Field for generic Djongo ArrayModelFields

    Acts akin to a DRF List field, using the passed in model
    (model_field) to aid in the conversion of list elements to and from
    a their serialized form

    Used internally for RMD serializers later, primarily for mapping
    fields which do not have explicit serialization set up already
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
        'wrong_model': _('Expected a `{model_type}`, but got `{input_class}`')
    }

    def to_internal_value(self, data):
        """Serialized -> Database"""
        try:
            return self.model_field.to_python(data)
        except AssertionError:
            self.fail('not_a_list', input_class=type(data).__name__)
        except FieldDoesNotExist as err:
            raise ValidationError('bad_field', err)
        except Exception as err:
            raise ValidationError('invalid', err)

    def to_representation(self, value):
        """Database -> Serialized"""
        if not isinstance(value, list):
            self.fail('not_a_list', input_class=type(value).__name__)
        fields = get_model_meta(self.model_field.model_container).get_fields()
        data_list = []
        for val in value:
            data = {}
            for field in fields:
                name = field.name
                data[name] = getattr(val, name, None)
            data_list.append(data)

        return data_list
