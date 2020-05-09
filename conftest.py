from typing import Callable, List, Dict, Type, Union

from django.db.models import Model
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import Field
from rest_meets_djongo.serializers import \
    DjongoModelSerializer, EmbeddedModelSerializer

from pytest import fixture, mark


# -- Utility functions -- #
def _meta_factory(
        target: Model,
        relate_depth: int,
        embed_depth: int,
        fields: List[str],
        exclude: List[str]):
    """
    Creates a Meta class for a ModelSerializer object
    :param target: The model the serializer using the Meta should target
    :param relate_depth: The relation depth to serialize
    :param embed_depth: The embedded model depth to serialize
    :param fields: Fields to retain during serialization
    :param exclude: Fields to ignore during serialization
    :return: A Meta class, ready for use in a serializer
    """
    from rest_framework.serializers import SerializerMetaclass
    # Confirm that one or none of the fields/exclude arguments are present
    if fields and exclude:
        raise ValueError("Cannot set both fields and exclude attribute")

    # Prepare the class attributes
    attributes = {'model': target}

    # Field targeting attributes
    if fields:
        attributes['fields'] = fields
    elif exclude:
        attributes['exclude'] = exclude
    else:
        attributes['fields'] = '__all__'

    # Depth attribute setup
    if relate_depth:
        attributes['depth'] = relate_depth
    if embed_depth:
        attributes['embed_depth'] = embed_depth

    Meta = type('Meta', (), attributes)

    return Meta


# -- Test management fixtures -- #
@fixture(scope='session')
def build_serializer():
    def _serializer_factory(
            target: Model,
            base_class: Type[ModelSerializer] = DjongoModelSerializer,
            relate_depth: int = None,
            embed_depth: int = None,
            name: str = "TestSerializer",
            meta_fields: List[str] = None,
            meta_exclude: List[str] = None,
            custom_fields: Dict[str, Union[Field, dict]] = None,
            custom_methods: Dict[str, Callable] = None,
            **kwargs
            ) -> (Type[ModelSerializer], Dict):
        """
        Build a custom model serializer, for testing purposes
        :param target: The model the serializer should serialize
        :param base_class: The class the serializer should derive from
        :param relate_depth: The depth of relations to serialize
        :param embed_depth: The depth of embedded models to serializer
        :param name: Custom name of the serializer
        :param meta_fields: Fields the serializer should serialize.
        :param meta_exclude: Fields the serializer should ignore
        :param custom_fields: Custom DRF/RMD serializer fields to use
            Pass in either a pre-built field, or a dictionary of
            attributes which should be used to build a new serializer
            (which itself would act as a field)
        :param custom_methods: Custom methods the serializer should use
        :param kwargs: Other kwargs (for custom field-like serializers)
        :return: A serializer class with the specified attributes, and
            the excess kwargs specified (if any)
        """
        # Initialize the attributes dictionary
        attributes = {'__qualname__': name}

        # Add in custom field attributes
        if custom_fields:
            for name, field in custom_fields.items():
                if isinstance(field, dict):
                    # Build the meta-class
                    field['name'] = field.get('name', 'EmbeddedSerializer')
                    field['base_class'] = field.get('base_class', EmbeddedModelSerializer)
                    EmbedSerializer, field_kwargs = _serializer_factory(**field)
                    # Build a field instance which reflects the metaclass
                    attributes[name] = EmbedSerializer(**field_kwargs)
                elif isinstance(field, Field):
                    attributes[name] = field
                else:
                    raise TypeError(
                        "Only `dict` or `field` instances are allowed.\n"
                        f"Value {name} was of type `{type(field)}` instead.")

        # Add in custom method attributes
        if custom_methods:
            for name, method in custom_methods.items():
                attributes[name] = method

        # Add in Meta (this MUST go last to avoid issues)
        attributes['Meta'] = _meta_factory(target, relate_depth,
                                           embed_depth, meta_fields,
                                           meta_exclude)

        Serializer = type(name, (base_class,), attributes)

        return Serializer, kwargs
    return _serializer_factory


@fixture(scope='session')
def update_mono_relation():
    # Prepares a dictionary with values contained in a DB instance
    # One-to-many and one-to-one relations only
    def _prep_dict(val_dict, fields, instance):
        """
        Update the designated fields with relation data, given key words
        For the full instance, use "RAW", for the pk, use "PK"
        :param val_dict: Data dictionary to be updated
        :param fields: Fields to update
        :param instance: Instance to pull data from
        """
        for field in fields:
            if val_dict.get(field, False):
                if val_dict[field] == 'PK':
                    val_dict[field] = getattr(instance, field).pk
                elif val_dict[field] == 'RAW':
                    val_dict[field] = getattr(instance, field)

    return _prep_dict


@fixture(scope='session')
def update_many_relation():
    # Prepares a dictionary with values contained in a DB instance
    # Many-to-many and Many-to-one relations only
    def _prep_dict(val_dict: dict, fields: List[str], instance: Model):
        """
        Update the designated fields with relation data, given key words
        For the full instance, use "RAW", for the pk, use "PK"
        :param val_dict: Data dictionary to be updated
        :param fields: Fields to update
        :param instance: Instance to pull data from
        """
        for field in fields:
            if val_dict.get(field, False):
                if val_dict[field] == 'PK':
                    instance_list = getattr(instance, field).all()
                    val_dict[field] = [i.pk for i in instance_list]
                elif val_dict[field] == 'RAW':
                    val_dict[field] = list(getattr(instance, field).all())

    return _prep_dict


@mark.django_db
@fixture(scope='session')
def db_prep():
    """Prepare the DB with the indicated models in preparation for tests"""
    def _db_prep(data: Dict[Type[Model], dict]):
        """
        Instantiates initial instances of given models in the test DB
        :param data: Data map, with keys being the target model
        :return:
        """
        instances = {}
        for model, datum in data.items():
            instance = model._default_manager.create(**datum)
            if model.__name__ not in instances.keys():
                instances[model.__name__] = [instance]
            else:
                instances[model.__name__].append(instance)
        return instances

    return _db_prep


@fixture(scope='session')
def does_a_subset_b():
    """Compare two dictionaries to see if the prior subsets the latter"""
    def _compare_val(val1, val2):
        """
        Compares two values, with some additional logic to allow string
        based comparision if requested
        """
        generic_error = f"`{val1}` != `{val2}`"

        # If the subset is a dictionary, pass it back up to verify
        if isinstance(val1, dict):
            if isinstance(val2, dict):
                _compare_dict(val1, val2)
            else:
                raise AssertionError(generic_error)
        # If the subset value is a string, compare it to a string repr.
        elif isinstance(val1, str):
            assert val1 == str(val2)
        # If the subset value is a list, check every element for equality
        elif isinstance(val1, list):
            _compare_list(val1, val2)
        # For anything else, compare the values without string repr.
        else:
            assert val1 == val2

    def _compare_list(list1: List, list2: List):
        """
        Compares two lists, allowing for string based comparision
        """
        err_dict = {}

        if not isinstance(list2, list):
            raise AssertionError(f"`{list1}` != `{list1}`")

        for i in range(len(list1)):
            try:
                _compare_val(list1[i], list2[i])
            except AssertionError as err:
                err_dict[i] = err

        if err_dict:
            raise AssertionError(err_dict)

    def _compare_dict(dict1: Dict, dict2: Dict):
        """Compare two dictionaries, with string comparision allowed"""
        # Raise an error if the compared dictionary is not a dictionary
        if not isinstance(dict2, dict):
            raise AssertionError(f"{dict1} != {dict2}")

        # Otherwise, build a list of all differences in the dictionaries
        err_dict = {}

        for key in dict1.keys():
            try:
                # If the value is a dictionary, run the comparision recursively
                if isinstance(dict1[key], dict):
                    _compare_dict(dict1[key], dict2[key])
                # If the value is a list, run the comparision for all elements
                elif isinstance(dict1[key], list):
                    _compare_list(dict1[key], dict2[key])
                # Otherwise, compare the values directly,
                # both as strings and literals
                else:
                    _compare_val(dict1[key], dict2[key])
            except AssertionError as err:
                err_dict[key] = err
            except KeyError:
                err_dict[key] = f"`{key}` missing in second dictionary"
        if err_dict:
            raise AssertionError(err_dict)

    return _compare_dict


# -- Utility fixtures -- #
@fixture(scope='session')
def error_raised():
    """Builds a raise instance for use w/ error checks"""
    from rest_framework.exceptions import ValidationError
    from pytest import raises

    return raises(ValidationError)


@fixture(scope='session')
def assert_dict_equals():
    """Compare two dictionaries to one another"""
    from tests.utils import format_dict

    def _compare_data(dict1, dict2):
        assert format_dict(dict1) == format_dict(dict2)

    return _compare_data


@fixture(scope='session')
def instance_matches_data():
    """Confirm that all arg_set_list in a dictionary is present in an instance"""
    def _does_instance_match_data(instance, data):
        err_list = {}
        for field in data.keys():
            # Common error types
            try:
                if not hasattr(instance, field):
                    msg = f"Field `{field}` not found in model instance!"
                    err_list[field] = msg
                elif (data[field] is None and
                      getattr(instance, field) is not None):
                    # Special case for `None` expected
                    # (The None type does not have and __eq__ function)
                    msg = (f"Field `{field}` was expected to be "
                           f"'{data[field]}', but was instead "
                           f"'{getattr(instance, field)}'")
                    err_list[field] = msg
                elif not (
                    (data[field].__eq__(getattr(instance, field))) or
                    (str(data[field]) == str(getattr(instance, field)))
                ):
                    msg = (f"Field `{field}` was expected to be " 
                           f"'{data[field]}', but was instead "
                           f"'{getattr(instance, field)}'")
                    err_list[field] = msg
            # Rarer error types
            except Exception as err:
                err_list[field] = err

        if err_list:
            raise AssertionError(str(err_list))

    return _does_instance_match_data


# -- PyTest Configuration -- #
def pytest_configure():
    from django.conf import settings

    settings.configure(
        DEBUG=True,
        TEMPLATE_DEBUG=True,
        SECRET_KEY='T35TK3Y',
        DATABASES={
            'default': {
                'ENGINE': 'djongo',
                'NAME': 'default'
            }
        },
        INSTALLED_APPS=(
            'rest_framework',
            'rest_meets_djongo',
            'tests'
        )
    )

    try:
        import django
        django.setup()
    except AttributeError as err:
        print(err)
