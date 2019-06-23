from rest_framework import serializers


def raise_errors_on_nested_writes(method_name, serializer, validated_data):
    # Modified version of DRF's test, as to allow for EmbeddedModels to
    # pass without being tagged as `nested`
    assert not any(
        isinstance(field, serializers.BaseSerializer) and
        (field in validated_data) and
        not isinstance(field, EmbeddedModelSerializer)
        for key, field in serializer.fields.items()
    ), (
        '`{method_name}()` does not natively support writable nested fields'
        'which are not Djongo derived fields by default.\nPlease write an'
        'explicit `{method_name}()` method for {module}.{cls_name}` or set'
        '`read_only=True` on these nested fields'.format(
            method_name=method_name,
            module=serializer.__class__.__module__,
            cls_name=serializer.__class__.__name__
        )
    )

    # Reject '.' formatted references, as is done by DRF
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




class DjangoModelSerializer(serializers.ModelSerializer):
    """ Serializer for models w/ Djongo fields as attributes

    Currently recognized Djongo fields:
        * ObjectID Field

    """
    

    pass


class EmbeddedModelSerializer(DjangoModelSerializer):
    pass
