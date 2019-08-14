from typing import Callable, List, Dict, Type

from django.db.models import Model
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import Field

from rest_meets_djongo.serializers import DjongoModelSerializer

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
    # Confirm that one or none of the fields/exclude arguments are present
    if fields and exclude:
        raise ValueError("Cannot set both fields and exclude attribute")

    # Build the Meta for the serializer
    class Meta:
        model = target

    # Serialized field collection
    if fields:
        Meta.fields = fields
    elif exclude:
        Meta.exclude = exclude
    else:
        Meta.fields = '__all__'

    # Depth of serialization setup
    if relate_depth:
        Meta.depth = relate_depth
    if embed_depth:
        Meta.embed_depth = embed_depth

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
            custom_fields: Dict[str, Field] = None,
            custom_methods: Dict[str, Callable] = None,
            ) -> Type[ModelSerializer]:
        """
        Build a custom model serializer, for testing purposes
        :param target: The model the serializer should serialize
        :param relate_depth: The depth of relations to serialize
        :param embed_depth: The depth of embedded models to serializer
        :param name: Custom name of the serializer
        :param meta_fields: Fields the serializer should serialize
        :param meta_exclude: Fields the serializer should ignore
        :param custom_fields: Custom DRF/RMD serializer fields to use
        :param custom_methods: Custom methods the serializer should use
        :param base_class: The class the serializer should derive from
        :return: A serializer class with the specified attributes
        """
        # Prepare the attributes for the new serializer, with its new Meta
        attributes = {
            'Meta': _meta_factory(target, relate_depth, embed_depth,
                                  meta_fields, meta_exclude)
        }

        # Add in custom field attributes
        if custom_fields:
            for name, field in custom_fields.items():
                attributes[name] = field

        # Add in custom method attributes
        if custom_methods:
            for name, method in custom_methods.items():
                attributes[name] = method

        Serializer = type(name, (base_class,), attributes)

        return Serializer
    return _serializer_factory


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
    """Compare two dictionaries to one another"""
    def _compare_data(dict1, dict2):
        """Slight tweak to allow input string representations to be used"""
        err_list = {}
        for key in dict1.keys():
            try:
                if not (
                        dict1[key] == dict2[key] or
                        dict1[key] == str(dict2[key])
                ):
                    err_list[key] = f"{dict1[key]} != {dict2[key]}"
            except KeyError:
                err_list[key] = f"`{key}` missing in second dictionary"
        if err_list:
            raise AssertionError(err_list)

    return _compare_data


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
                if not getattr(instance, field).__eq__(data[field]):
                    msg = (f"Field `{field}` has a value of " 
                           f"'{getattr(instance, field)}', but a value of "
                           f"'{data[field]}' was expected")
                    err_list[field] = msg
            # Rarer error types
            except Exception as err:
                err_list[field] = err

        if err_list:
            raise AssertionError(str(err_list))

    return _does_instance_match_data


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
    except AttributeError:
        pass
