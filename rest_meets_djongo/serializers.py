from djongo import models as djm_fields
from rest_framework import serializers
from rest_framework import fields as drf_fields

from . import fields as rmd_fields


def raise_errors_on_nested_writes(method_name, serializer, validated_data):
    # Modified version of DRF's test, as to allow for EmbeddedModels to
    # pass without being tagged as `nested`
    assert not any(
        isinstance(field, serializers.BaseSerializer) and
        (field in validated_data) and
        not isinstance(field, EmbeddedModelSerializer)
        for key, field in serializer.fields.items()
    ), (
        '`{method_name}()` does not natively support writable nested '
        'fields which are not Djongo derived fields by default.\nPlease '
        'write an explicit `{method_name}()` method for '
        '{module}.{cls_name}` or set `read_only=True` on these nested '
        'fields'.format(
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
    """ Serializers for Djongo-derived models

    Heavily derived from django-rest-framework-mongoengine; please

    Adds support for Djongo embedded models, List fields (NYI), ObjectID
    fields (NYI), and Array Model/Reference fields (NYI), on top of
    fields already serializable via normal REST

    ForeignKey's remain handled as normal (depth used to determine their
    rendering) (NYI)

    Embedded models are treated as nested field representations, WITHOUT
    primary keys or relationship handling

    List and Array fields are treated the same was as multiple object
    serialization (a la `Many = True` parameter) (NYI)

    Embedded fields for Files, Images, or Binary remain untested, and
    may work in unpredictable ways (if at all)
    """

    _saving_instances = True

    new_mappings = {
        djm_fields.EmbeddedModelField: rmd_fields.EmbeddedModelField,
    }

    serializer_field_mapping = serializers.ModelSerializer.serializer_field_mapping.update(new_mappings)

    def recursive_save(self, validated_data, instance=None):
        obj_data = {}

        obj_meta = self.Meta.model._meta

        for key, value in validated_data.items():
            try:
                field = obj_meta.get_field(key)

                # When field is an embedded model, recursively iterate
                # through it as well
                if isinstance(field, EmbeddedModelSerializer):
                    obj_data[key] = field.recursive_save(value)

                # When the field is a list of EmbeddedModels
                elif ((isinstance(field, serializers.ListSerializer) or
                       isinstance(field, serializers.ListField)) and
                      isinstance(field.child, EmbeddedModelSerializer)):
                    obj_data[key] = []
                    for val in value:
                        obj_data[key].append(field.child.recursive_save())

                elif ():
                    continue

            except KeyError:  # Dynamic or ignored data
                obj_data[key] = value






class EmbeddedModelSerializer(DjangoModelSerializer):
    # WIP
    pass
