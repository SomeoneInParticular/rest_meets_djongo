"""
Helper functions to work with the meta of a model without breaking PEP8

Aids in getting field information for Djongo models, as well as
relation info (if any) and embedded model field information (if any)
"""

from collections import namedtuple

from djongo import models as djm_fields
from rest_framework.utils import model_meta

# Extended version of DRF's FieldInfo, to allow for embedded model field
# tracking (namely EmbeddedModelFields and EmbeddedModelSerializers)
FieldInfo = namedtuple('FieldInfo', [
    'pk',  # Primary key for the model (if it is not abstract)
    'fields',  # Non-embedded or relational fields for the object
    'forward_relations',  # Relations from the model to another model
    'reverse_relations',  # Relations to the model from another model
    'embedded',  # Fields for models embedded within this model
    'fields_and_pk',  # Shortcut for all fields that are not relational
    'relations',  # Shortcut for all relational fields (forward + reverse)
])

# Information to keep track of for EmbeddedModelFields
EmbedInfo = namedtuple('EmbedInfo', [
    'model_field',  # The model field for building a DRF field
    'is_array',  # If the model
])


def get_model_meta(model):
    """
    Simply fetches the meta attribute of the model, so PEP8 checks will
    stop screaming at me so much
    """
    return model._meta


def is_model_abstract(model):
    """
    Quickly check if the provided model is abstract or not
    """
    return getattr(get_model_meta(model), 'abstract', False)


def get_field_info(model):
    """
    A bypass of DRF's model_meta function, customized to work with our
    custom FieldInfo tuple. Some minor optimizations as well.
    """
    # Bypass the concrete model fetch, as abstract (embedded) models lack it
    opts = get_model_meta(model)

    # Bypass for pk fetching for EmbeddedModels, as they do not have a pk
    if model_meta.is_abstract_model(model):
        pk = None
    else:
        pk = model_meta._get_pk(opts)

    # Fetch field info based on the model's options
    fields, fwd_relations, emb_fields = _build_generic_field_info(opts)
    rvs_relations = _build_reverse_field_info(opts)
    fields_and_pk = _merge_fields_and_pk(pk, fields)
    relations = _merge_relations(fwd_relations, rvs_relations)

    return FieldInfo(
        pk=pk,
        fields=fields,
        forward_relations=fwd_relations,
        reverse_relations=rvs_relations,
        embedded=emb_fields,
        fields_and_pk=fields_and_pk,
        relations=relations,
    )


def _build_generic_field_info(opts):
    """
    Helper function which builds fields based on a model's meta

    Slightly optimized variation of DRF's model_meta util functions

    Takes a model's option object and returns three dictionaries:
        basic_fields: Field information for non-relation/embedded fields
        forward_fields: Field information for one-to-many forward relations
        embedded_fields: Field information for embedded model fields (Djongo)
    """
    basic_fields = {}
    forward_relations = {}
    embedded_fields = {}

    # Initial pass for non-many-to-many type fields
    for field in [field for field in opts.fields if field.serialize]:
        # Forward, one-to-one, and relation parsing
        if field.remote_field:
            to_field = getattr(field, 'to_fields')[0]
            forward_relations[field.name] = model_meta.RelationInfo(
                model_field=field,
                related_model=field.remote_field.model,
                to_many=isinstance(field, djm_fields.ArrayReferenceField),
                to_field=to_field,
                has_through_model=False,
                reverse=False
            )
        # Embedded model field (array or singular)
        elif hasattr(field, 'model_container'):
            embedded_fields[field.name] = EmbedInfo(
                model_field=field,
                is_array=isinstance(field, djm_fields.ArrayModelField)
            )
        # Other non-many-to-many fields
        else:
            basic_fields[field.name] = field

    # Second pass for many-to-many fields
    for field in [field for field in opts.many_to_many if field.serialize]:
        forward_relations[field.name] = model_meta.RelationInfo(
            model_field=field,
            related_model=field.remote_field.model,
            to_many=True,
            # manytomany do not have to_fields
            to_field=None,
            has_through_model=(
                not field.remote_field.through._meta.auto_created
            ),
            reverse=False
        )

    return basic_fields, forward_relations, embedded_fields


def _build_reverse_field_info(opts):
    """
    Helper function which fetches reverse relation field info

    Slightly tweaked variant of DRF's model_meta util function
    """
    reverse_relations = {}

    for relation in opts.related_objects:
        if not relation.field.many_to_many:
            access_name = relation.get_accessor_name()
            to_field = getattr(relation.field, 'to_fields')[0]
            reverse_relations[access_name] = model_meta.RelationInfo(
                model_field=None,
                related_model=relation.related_model,
                to_many=False,
                to_field=to_field,
                has_through_model=False,
                reverse=True
            )
        else:
            access_name = relation.get_accessor_name()
            reverse_relations[access_name] = model_meta.RelationInfo(
                model_field=None,
                related_model=relation.related_model,
                to_many=True,
                to_field=None,
                has_through_model=(
                    getattr(relation.field.remote_field, 'through', False) and
                    not relation.field.remote_field.through._meta.auto_created
                ),
                reverse=True,
            )

    return reverse_relations


def _merge_fields_and_pk(pk, fields):
    """
    Tweaked variant of DRF's model_meta function to accommodate for
    abstract models

    Used by EmbeddedModelFields and EmbeddedModelSerializers
    """
    fields_and_pk = {}
    fields_and_pk['pk'] = pk
    if pk is not None:
        fields_and_pk[pk.name] = pk
    fields_and_pk.update(fields)

    return fields_and_pk


def _merge_relations(fwd_relations, rvs_relations):
    """
    Tweak of DRF's _merge_relationships to be more readable
    """
    relations = {}
    relations.update(fwd_relations)
    relations.update(rvs_relations)
    return relations
