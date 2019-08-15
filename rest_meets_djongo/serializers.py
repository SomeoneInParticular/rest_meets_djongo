import copy
from collections import namedtuple
import traceback

from django.db import models as dja_fields
from djongo.models import fields as djm_fields
from rest_framework import fields as drf_fields
from rest_framework import serializers as drf_ser
from rest_framework.settings import api_settings
from rest_framework.utils.field_mapping import get_nested_relation_kwargs

from .fields import EmbeddedModelField, ArrayModelField, ObjectIdField
from .meta_manager import get_model_meta
from rest_meets_djongo import meta_manager, kwarg_manager


# Object to track and manage nested field customization attributes
Customization = namedtuple("Customization", [
    'fields',
    'exclude',
    'extra_kwargs',
    'validate_methods'
])


def raise_errors_on_nested_writes(method_name, serializer, validated_data):
    """
    Replacement for DRF, allows for Djongo fields to not throw errors
    """
    # Make sure the field is a format which can be managed by the method
    for field in serializer._writable_fields:
        assert not (
            isinstance(field, drf_ser.BaseSerializer) and
            (field.source in validated_data) and
            isinstance(validated_data[field.source], (list, dict)) and not
            (isinstance(field, EmbeddedModelSerializer) or
             isinstance(field, drf_ser.ListSerializer) or
             isinstance(field, drf_fields.ListField)
             )), (
            'The method `{method_name}` does not support serialization of '
            '`{field_name}` fields in writable nested field by default.\n'
            'Write a custom version of the method for `{module}.{class_name}` '
            'or set the field to `read_only=True`'.format(
                field_name=field.__class__.__name__,
                method_name=method_name,
                module=serializer.__class__.__module__,
                class_name=serializer.__class__.__name__
            )
        )

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


class DjongoModelSerializer(drf_ser.ModelSerializer):
    """
    A modification of DRF's ModelSerializer to allow for EmbeddedModelFields
    to be easily handled.

    Automatically generates fields for the model, accounting for embedded
    model fields in the process
    """
    serializer_field_mapping = {
        # Original DRF field mappings (Django Derived)
        dja_fields.AutoField: drf_fields.IntegerField,
        dja_fields.BigIntegerField: drf_fields.IntegerField,
        dja_fields.BooleanField: drf_fields.BooleanField,
        dja_fields.CharField: drf_fields.CharField,
        dja_fields.CommaSeparatedIntegerField: drf_fields.CharField,
        dja_fields.DateField: drf_fields.DateField,
        dja_fields.DateTimeField: drf_fields.DateTimeField,
        dja_fields.DecimalField: drf_fields.DecimalField,
        dja_fields.EmailField: drf_fields.EmailField,
        dja_fields.Field: drf_fields.ModelField,
        dja_fields.FileField: drf_fields.FileField,
        dja_fields.FloatField: drf_fields.FloatField,
        dja_fields.ImageField: drf_fields.ImageField,
        dja_fields.IntegerField: drf_fields.IntegerField,
        dja_fields.NullBooleanField: drf_fields.NullBooleanField,
        dja_fields.PositiveIntegerField: drf_fields.IntegerField,
        dja_fields.PositiveSmallIntegerField: drf_fields.IntegerField,
        dja_fields.SlugField: drf_fields.SlugField,
        dja_fields.SmallIntegerField: drf_fields.IntegerField,
        dja_fields.TextField: drf_fields.CharField,
        dja_fields.TimeField: drf_fields.TimeField,
        dja_fields.URLField: drf_fields.URLField,
        dja_fields.GenericIPAddressField: drf_fields.IPAddressField,
        dja_fields.FilePathField: drf_fields.FilePathField,
        # REST-meets-Djongo field mappings (Djongo Derived)
        djm_fields.ObjectIdField: ObjectIdField,
        djm_fields.EmbeddedModelField: EmbeddedModelField,
        djm_fields.ArrayModelField: ArrayModelField,
    }

    # Class for creating fields for embedded models w/o a serializer
    serializer_generic_embed = EmbeddedModelField

    # Class for creating array model fields w/o a serializer
    serializer_array_embed = ArrayModelField

    # Class for creating nested fields for embedded model fields
    # Defaults to our version of EmbeddedModelField or ArrayModelField
    serializer_nested_embed = None

    # Easy trigger variable for use in inherited classes (EmbeddedModels)
    _saving_instances = True

    def build_instance_data(self, validated_data, instance=None):
        """
        Recursively traverses provided validated data, creating a
        dictionary describing the target model in the process

        Returns a dictionary of model data, for use w/ creating or
        updating instances of the target model
        """
        obj_data = {}

        for key, val in validated_data.items():
            try:
                field = self.fields[key]

                # For other embedded models, recursively build their fields too
                if isinstance(field, EmbeddedModelSerializer):
                    if instance is not None:
                        field_obj = get_model_meta(instance).get_field(key)
                        embed_instance = field_obj.value_from_object(instance)
                        obj_data[key] = field.update(embed_instance, val)
                    else:
                        obj_data[key] = field.create(val)

                # Build defaults for EmbeddedModelFields
                elif isinstance(field, EmbeddedModelField):
                    obj_data[key] = field.model_field(**val)

                # For lists of embedded models, build each object as above
                elif ((isinstance(field, drf_ser.ListSerializer) or
                       isinstance(field, drf_ser.ListField)) and
                      isinstance(field.child, EmbeddedModelSerializer)):
                    obj_data[key] = []
                    for datum in val:
                        embed_instance = field.child.create(datum)
                        obj_data[key].append(embed_instance)

                # Other values, such as common datatypes
                else:
                    obj_data[key] = val

            # Dynamic data (Shouldn't exist with current Djongo, but may
            # appear in future)
            except KeyError:
                obj_data = val

        return obj_data

    def create(self, validated_data):
        """
        Build a new instance of the target model w/ attributes matching
        validated data for the model
        """
        raise_errors_on_nested_writes('create', self, validated_data)

        model_class = self.Meta.model

        try:
            data = self.build_instance_data(validated_data)
            instance = model_class._default_manager.create(**data)
            return instance
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

    def update(self, instance, validated_data):
        """
        Update an existing instance of the target model w/ attributes
        provided from validated data
        """
        raise_errors_on_nested_writes('update', self, validated_data)

        data = self.build_instance_data(validated_data, instance)
        for key, val in data.items():
            setattr(instance, key, val)
        instance.save()

        return instance

    def to_internal_value(self, data):
        """
        Borrows DRF's implementation, but creates initial and validated
        data for EmbeddedModels so `build_instance_data` can use them

        Arbitrary data is silently dropped from validated data, as to
        avoid issues down the line (assignment to an attribute which
        doesn't exist)
        """
        # Initial pass through for initial data writing
        for field in self._writable_fields:
            if (isinstance(field, EmbeddedModelSerializer) and
                    field.field_name in data):
                field.initial_data = data[field.field_name]

        ret = super(DjongoModelSerializer, self).to_internal_value(data)

        # Secondary, post conversion pass to add initial data to validated data
        for field in self._writable_fields:
            if (isinstance(field, EmbeddedModelSerializer) and
                    field.field_name in ret):
                field._validated_data = ret[field.field_name]

        return ret

    def get_fields(self):
        """
        An override of DRF's `get_fields` to enable EmbeddedModelFields
        to be correctly caught and constructed
        """
        if self.url_field_name is None:
            self.url_field_name = api_settings.URL_FIELD_NAME

        assert hasattr(self, 'Meta'), (
            'Class {serializer_class} missing "Meta" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )

        assert hasattr(self.Meta, 'model'), (
            "Class {serializer_name} missing `Meta.model` attribute".format(
                serializer_name=self.__class__.__name__
            )
        )

        if meta_manager.is_model_abstract(self.Meta.model) and self._saving_instances:
            raise ValueError(
                "Cannot use DjongoModelSerializer w/ Abstract Models.\n"
                "Consider using an EmbeddedModelSerializer instead."
            )

        # Fetch and check useful metadata parameters
        declared_fields = copy.deepcopy(self._declared_fields)
        model = getattr(self.Meta, 'model')
        rel_depth = getattr(self.Meta, 'depth', 0)
        emb_depth = getattr(self.Meta, 'embed_depth', 5)

        assert rel_depth >= 0, "'depth' may not be negative"
        assert rel_depth <= 10, "'depth' may not be greater than 10"

        assert emb_depth >= 0, "'embed_depth' may not be negative"

        # Fetch information about the fields for our model class
        info = meta_manager.get_field_info(model)
        field_names = self.get_field_names(declared_fields, info)

        # Determine extra field arguments + hidden fields that need to
        # be included
        extra_kwargs = self.get_extra_kwargs()
        extra_kwargs, hidden_fields = self.get_uniqueness_extra_kwargs(
            field_names, declared_fields, extra_kwargs
        )

        # Find fields which are required for the serializer
        fields = {}

        for field_name in field_names:
            # Fields explicitly declared should always be used
            if field_name in declared_fields:
                fields[field_name] = declared_fields[field_name]
                continue

            extra_field_kwargs = extra_kwargs.get(field_name, {})
            source = extra_field_kwargs.get('source', field_name)
            if source == '*':
                source = field_name

            # Determine field class and keyword arguments
            field_class, field_kwargs = self.build_field(
                source, info, model, rel_depth, emb_depth
            )

            # Fetch any extra_kwargs specified by the meta
            field_kwargs = self.include_extra_kwargs(
                field_kwargs, extra_field_kwargs
            )

            # Create the serializer field
            fields[field_name] = field_class(**field_kwargs)

        # Update with any hidden fields
        fields.update(hidden_fields)

        return fields

    def get_field_names(self, declared_fields, info):
        """
        Override of DRF's `get_field_names` function, enabling
        EmbeddedModelFields to be caught and handled.

        Some slight optimization is also provided. (Useful given how
        many nested model fields may need to be iterated over)

        Will include only direct children of the serializer; no
        grandchildren are included by default
        """
        fields = getattr(self.Meta, 'fields', None)
        exclude = getattr(self.Meta, 'exclude', None)

        # Confirm that both were not provided, which is invalid
        assert not (fields and exclude), (
            "Cannot set both 'fields' and 'exclude' options on "
            "serializer {serializer_class}.".format(
                serializer_class=self.__class__.__name__
            )
        )

        # Construct the list of fields to be serialized
        if fields is not None:
            # If the user just wants all fields...
            if fields == drf_ser.ALL_FIELDS:
                return self.get_default_field_names(declared_fields, info)
            # If the user specified fields explicitly...
            elif isinstance(fields, (list, tuple)):
                # Check to make sure all declared fields (required for creation)
                # were specified by the user
                required_field_names = set(declared_fields)
                for cls in self.__class__.__bases__:
                    required_field_names -= set(getattr(cls, '_declared_fields', []))

                for field_name in required_field_names:
                    assert field_name in fields, (
                        "The field '{field_name}' was declared on serializer "
                        "{serializer_class}, but has not been included in the "
                        "'fields' option.".format(
                            field_name=field_name,
                            serializer_class=self.__class__.__name__
                        )
                    )
            # If the user didn't provide a field set in the proper format...
            else:
                raise TypeError(
                    'The `fields` option must be a list or tuple or "__all__". '
                    'Got {cls_name}.'.format(cls_name=type(fields).__name__)
                )
        # Strip out designated fields for serialization
        elif exclude is not None:
            fields = self.get_default_field_names(declared_fields, info)

            # Ignore nested field customization; they're handled later
            for field_name in [name for name in exclude if '.' not in name]:
                assert field_name not in self._declared_fields, (
                    "Cannot both declare the field '{field_name}' and include "
                    "it in the {serializer_class} 'exclude' option. Remove the "
                    "field or, if inherited from a parent serializer, disable "
                    "with `{field_name} = None`.".format(
                        field_name=field_name,
                        serializer_class=self.__class__.__name__
                    )
                )

                assert field_name in fields, (
                    "The field '{field_name}' was included on serializer "
                    "{serializer_class} in the 'exclude' option, but does "
                    "not match any model field.".format(
                        field_name=field_name,
                        serializer_class=self.__class__.__name__
                    )
                )

                fields.remove(field_name)
        # If the user failed to specify a set of fields to include/exclude
        else:
            raise AssertionError(
                "Creating a ModelSerializer without either the 'fields' attribute "
                "or the 'exclude' attribute has been deprecated and is now " 
                "disallowed. Add an explicit fields = '__all__' to the "
                "{serializer_class} serializer.".format(
                    serializer_class=self.__class__.__name__
                )
            )

        # Filter out child fields, which would be contained in the child
        # instance anyways
        return [name for name in fields if '.' not in name]

    def get_default_field_names(self, declared_fields, model_info):
        """Provide the list of fields included when `__all__` is used"""
        return (
            [model_info.pk.name] +
            list(declared_fields.keys()) +
            list(model_info.fields.keys()) +
            list(model_info.forward_relations.keys()) +
            list(model_info.embedded.keys())
        )

    def get_nested_field_customization(self, field_name):
        """
        Fetches nested customization for Djongo unique fields

        Extracts fields, exclude, extra_kwargs, and validation methods
        for the parent serializer, related to the attributes of field

        Used to enable automatic writable nested field construction

        This should be called after self.get_fields(). Therefore, we
        assume that most field validation has already been done
        """
        fields = getattr(self.Meta, 'fields', None)
        exclude = getattr(self.Meta, 'exclude', None)

        # String used to identify nested fields
        leading_str = field_name + '.'

        # Get nested fields/exclusions
        if fields is not None:
            nested_exclude = None
            if fields == drf_ser.ALL_FIELDS:
                nested_fields = drf_ser.ALL_FIELDS
            else:
                nested_fields = [field[len(leading_str):] for
                                 field in fields if
                                 field.startswith(leading_str)]
        else:
            nested_fields = None
            nested_exclude = [field[len(leading_str):] for
                                 field in exclude if
                                 field.startswith(leading_str)]

        # Get any user specified kwargs (including read-only)
        extra_kwargs = self.get_extra_kwargs()
        nested_extra_kwargs = {key[len(leading_str):]: value for
                               key, value in extra_kwargs.items() if
                               key.startswith(leading_str)}

        # Fetch nested validations methods for the field
        # Renames them so that they may be added to the serializer's
        # validation dictionary without conflicts
        nested_validate_methods = {}
        for attr in dir(self.__class__):
            valid_lead_str = 'validate_{}__'.format(field_name.replace('.', '__'))
            if attr.startswith(valid_lead_str):
                method = getattr(self.__class__, attr)
                method_name = 'validate' + attr[len(valid_lead_str):]
                nested_validate_methods[method_name] = method

        return Customization(nested_fields, nested_exclude, nested_extra_kwargs,
                             nested_validate_methods)

    # TODO: Make this use self instead of a serializer
    #  or move to a utility function
    def apply_customization(self, serializer, customization):
        """
        Applies customization from nested fields to the serializer

        Assumes basic verification has already been done
        """
        if customization.fields:
            serializer.Meta.fields = customization.fields
        elif customization.exclude:
            serializer.Meta.exclude = customization.exclude

        # Apply extra_kwargs
        if customization.extra_kwargs is not None:
            serializer.Meta.extra_kwargs = customization.extra_kwargs

        # Apply validation methods
        for method_name, method in customization.validate_methods.items():
            setattr(serializer, method_name, method)

    def build_field(self, field_name, info, model_class, nested_depth, embed_depth):
        # Basic field construction
        if field_name in info.fields_and_pk:
            model_field = info.fields_and_pk[field_name]
            return self.build_standard_field(field_name, model_field)

        # Relational field construction
        elif field_name in info.relations:
            relation_info = info.relations[field_name]
            if not nested_depth:
                return self.build_relational_field(field_name, relation_info)
            else:
                return self.build_nested_relation_field(field_name, relation_info, nested_depth)

        # Embedded field construction
        elif field_name in info.embedded:
            embed_info = info.embedded[field_name]
            # If the field is in the deepest depth,
            if embed_depth == 0:
                return self.build_root_embed_field(field_name, embed_info)
            else:
                return self.build_nested_embed_field(field_name, embed_info, embed_depth)

        # Property field construction
        elif hasattr(model_class, field_name):
            return self.build_property_field(field_name, model_class)

        # URL field construction
        elif field_name == self.url_field_name:
            return self.build_url_field(field_name, model_class)

        # If all mapping above fails,
        return self.build_unknown_field(field_name, model_class)

    def build_nested_relation_field(self, field_name, relation_info, nested_depth):
        """
        Create nested fields for forward/reverse relations

        Slight tweak of DRF's variant, as to allow the nested serializer
        to use our specified field mappings
        """
        class NestedRelationSerializer(DjongoModelSerializer):
            class Meta:
                model = relation_info.related_model
                depth = nested_depth - 1
                fields = '__all__'

        field_class = NestedRelationSerializer
        field_kwargs = get_nested_relation_kwargs(relation_info)

        return field_class, field_kwargs

    def build_root_embed_field(self, field_name, embed_info):
        """Build a field instance for when the max `embed_depth` is reached"""
        if embed_info.is_array:
            field_class = self.serializer_array_embed
        else:
            field_class = self.serializer_generic_embed
        field_kwargs = kwarg_manager.get_generic_embed_kwargs(embed_info)
        return field_class, field_kwargs

    def build_nested_embed_field(self, field_name, embed_info, depth):
        """Create a serializer for nested embedded model fields"""
        subclass = self.serializer_nested_embed or EmbeddedModelSerializer

        class EmbeddedSerializer(subclass):
            class Meta:
                model = embed_info.model_field.model_container
                fields = '__all__'
                embed_depth = depth - 1

        # Apply customization to the nested field, if any is provided

        customization = self.get_nested_field_customization(field_name)
        self.apply_customization(EmbeddedSerializer, customization)

        field_class = EmbeddedSerializer
        field_kwargs = kwarg_manager.get_nested_embed_kwargs(field_name, embed_info)
        return field_class, field_kwargs

    def get_unique_for_date_validators(self):
        # Not currently supported
        return []


class EmbeddedModelSerializer(DjongoModelSerializer):
    _saving_instances = False

    def get_default_field_names(self, declared_fields, model_info):
        """Modified to not include the `pk` attribute"""
        return (
                list(declared_fields.keys()) +
                list(model_info.fields.keys()) +
                list(model_info.forward_relations.keys()) +
                list(model_info.embedded.keys())
        )

    def create(self, validated_data):
        """
        Slight tweak to not push to directly to database; the containing
        model does this for us
        """
        raise_errors_on_nested_writes('create', self, validated_data)

        model_class = self.Meta.model

        try:
            data = self.build_instance_data(validated_data)
            return model_class(**data)
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

    def update(self, instance, validated_data):
        """
        Does not push the updated model to the database; the containing
        instance will do this for us
        """
        data = self.build_instance_data(validated_data, instance)
        for key, val in data.items():
            setattr(instance, key, val)

        return instance

    def get_unique_together_validators(self):
        # Skip these validators (may be added again in future)
        return []
