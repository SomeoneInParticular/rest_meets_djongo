import traceback

from djongo import models
from rest_framework import serializers

from .fields import EmbeddedModelField
from .utils import meta_manager


def raise_errors_on_nested_writes(method_name, serializer, validated_data):
    """
    Replacement for DRF, allows for EmbeddedModelFields to not cause an error
    """
    # Make sure the field is a format which can be managed by the method
    assert not any(
        isinstance(field, serializers.BaseSerializer) and
        (field.source in validated_data) and
        isinstance(validated_data[field.source], (list, dict)) and
        not isinstance(field, EmbeddedModelSerializer)
        for field in serializer._writable_fields), (
        'The method `{method_name}` does not support this form of '
        'writable nested field by default.\nWrite a custom version of '
        'the method for `{module}.{class_name}` or set the field to '
        '`read_only=True`'.format(
            method_name=method_name,
            module=serializer.__class__.__module__,
            class_name=serializer.__class__.__name__
        )
    )

    for field in serializer._writable_fields:
        print(field)

    # Make sure dotted-source fields weren't passed
    assert not any(
        '.' in field.source and
        (key in validated_data) and
        isinstance(validated_data[key], (list, dict))
        for key, field in serializer.fields.items()
    ), (
        'The `.{method_name}()` method does not support writable dotted-source '
        'fields by default.\nWrite an explicit `.{method_name}()` method for '
        'serializer `{module}.{class_name}`, or set `read_only=True` on '
        'dotted-source serializer fields.'.format(
            method_name=method_name,
            module=serializer.__class__.__module__,
            class_name=serializer.__class__.__name__
        )
    )


class DjongoModelSerializer(serializers.ModelSerializer):
    """
    A modification of DRF's ModelSerializer to allow for EmbeddedModelFields
    to be easily handled.

    Automatically generates fields for the model, accounting for embedded
    model fields in the process
    """

    # Easy trigger variable for use in inherited classes (IE EmbeddedModels)
    _saving_instances = True

    def recursive_save(self, validated_data, instance=None):
        """
        Recursively traverses provided validated data, creating
        EmbeddedModels w/ the correct class as it does so

        Returns a Model instance
        """
        obj_data = {}

        for key, val in validated_data.items():
            try:
                field = self.fields[key]

                # For other embedded models, recursively build their fields too
                if isinstance(field, EmbeddedModelSerializer):
                    obj_data[key] = field.recursive_save(val)

                # For lists of embedded models, build each object as above
                elif ((isinstance(field, serializers.ListSerializer) or
                        isinstance(field, serializers.ListField)) and
                       isinstance(field.child, EmbeddedModelSerializer)):
                    obj_data[key] = []
                    for datum in val:
                        obj_data[key].append(field.child.recursive_save(datum))

                # For ArrayModelFields, do above (with a different reference)
                # WIP
                elif isinstance(field, models.ArrayModelField):
                    obj_data[key] = field.value_from_object(val)

                else:
                    obj_data[key] = val

            # Dynamic data (Shouldn't exist with current Djongo, but may
            # appear in future)
            except KeyError:
                obj_data = val

        if instance is None:
            instance = self.Meta.model(**obj_data)
        else:
            for key, val in obj_data.items():
                setattr(instance, key, val)

        if self._saving_instances:
            instance.save()

        return instance

    def create(self, validated_data):
        raise_errors_on_nested_writes('create', self, validated_data)

        model_class = self.Meta.model

        # Remove many-to-many relations, since they are not used in
        # create() by default
        info = meta_manager.get_field_info(model_class)

        try:
            instance = self.recursive_save(validated_data)
        except TypeError:
            tb = traceback.format_exc()
            msg = (
                    'Got a `TypeError` when calling `%s.%s.create()`. '
                    'This may be because you have a writable field on the '
                    'serializer class that is not a valid argument to '
                    '`%s.%s.create()`. You may need to make the field '
                    'read-only, or override the %s.create() method to handle '
                    'this correctly.\nOriginal exception was:\n %s' %
                    (
                        model_class.__name__,
                        model_class._default_manager.name,
                        model_class.__name__,
                        model_class._default_manager.name,
                        self.__class__.__name__,
                        tb
                    )
            )
            raise TypeError(msg)

    def to_internal_value(self, data):
        """
        Borrows DRF's implimentation, but creates initial and validated
        data for EmbeddedModels so recursive save can correctly use them

        Arbitrary data is silently dropped from validated data, as to avoid
        issues down the line (assignment to an attribute which doesn't exist)
        """

        for field in self._writable_fields:
            if (isinstance(field, EmbeddedModelSerializer) and
                    field.field_name in data):
                field.initial_data = data[field.field_name]

        ret = super(DjongoModelSerializer, self).to_internal_value(data)

        for field in self._writable_fields:
            if (isinstance(field, EmbeddedModelSerializer) and
                    field.field_name in ret):
                field._validated_data = ret[field.field_name]

        return ret


class EmbeddedModelSerializer(DjongoModelSerializer):
    # Placeholder for the time being
    pass
