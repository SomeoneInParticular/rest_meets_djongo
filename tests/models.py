from djongo import models


# --- Basic Models --- #
# Generic, DRF compliant model, with all DRF fields
class GenericModel(models.Model):
    big_int = models.BigIntegerField()
    bool = models.BooleanField()
    char = models.CharField(max_length=20)
    comma_int = models.CommaSeparatedIntegerField()
    date = models.DateField()
    date_time = models.DateTimeField()
    decimal = models.DecimalField(max_digits=10, decimal_places=5)
    email = models.EmailField()
    float = models.FloatField()
    integer = models.IntegerField()
    null_bool = models.NullBooleanField()
    pos_int = models.PositiveIntegerField()
    pos_small_int = models.PositiveSmallIntegerField()
    slug = models.SlugField()
    small_int = models.SmallIntegerField()
    text = models.TextField()
    time = models.TimeField()
    url = models.URLField()
    ip = models.GenericIPAddressField()
    uuid = models.UUIDField()

    # TODO: add these
    # basic_file = models.FileField()
    # image = models.ImageField()

    objects = models.DjongoManager()


# Model with its primary key set as its ObjectID
class ObjIDModel(models.Model):
    _id = models.ObjectIdField()
    int_field = models.IntegerField()
    char_field = models.CharField(max_length=5)

    objects = models.DjongoManager()


# Model a variant for DRF standard arguments
class OptionsModel(models.Model):
    db_column_id = models.ObjectIdField(db_column='_id')
    null_char = models.CharField(null=True)
    blank_char = models.TextField(blank=True)
    choice_char = models.CharField(choices=['Foo', 'Bar', 'Baz'])
    default_email = models.EmailField(default='noonecares@no.nope')
    read_only_int = models.IntegerField(editable=False)
    # NOTE: By default, custom error messages are not conserved. This is
    # just here to make sure it does not crash the serializer
    custom_error = models.IntegerField(error_messages={
        'blank': 'You tried to submit a blank integer, you dingus'
    })
    help_char = models.CharField(help_text='Super helpful text')
    unique_int = models.IntegerField(unique=True)

    objects = models.DjongoManager()


# --- Compound Field Containing Models --- #
class ListModel(models.Model):
    char_field = models.CharField(max_length=16)
    list_field = models.ListField()


class DictModel(models.Model):
    int_field = models.IntegerField()
    dict_field = models.DictField()


# --- Embedded Model Containing Models --- #
# Model for use w/ testing embedded models
class EmbedModel(models.Model):
    int_field = models.IntegerField()
    char_field = models.CharField(max_length=5)

    objects = models.DjongoManager()

    def __eq__(self, other):
        return (isinstance(other, EmbedModel) and
                self.char_field == other.char_field and
                self.int_field == other.int_field)

    def __str__(self):
        return str(self.int_field) + "-" + str(self.char_field)

    class Meta:
        abstract = True


# Model for use w/ testing nested embedded models,
class ContainerModel(models.Model):
    _id = models.ObjectIdField()
    control_val = models.CharField(default='CONTROL', max_length=7)
    embed_field = models.EmbeddedField(model_container=EmbedModel,
                                            blank=True)

    objects = models.DjongoManager()

    def __eq__(self, other):
        # Only compare _id if both have one (neither are embedded)
        _id_match = True
        if self._id and other._id:
            _id_match = (str(self._id) == str(other._id))

        # Compare the other values to confirm they are identical
        return(
            _id_match and
            self.control_val == other.control_val and
            self.embed_field.__eq__(other.embed_field)
        )

    def __str__(self):
        vals = [self.control_val, str(self.embed_field)]
        return f"{str(self._id)}: {'|'.join(vals)}"


# Model for testing w/ embedded models which contain embedded models
class DeepContainerModel(models.Model):
    str_id = models.CharField(primary_key=True, max_length=10)
    control_val = models.CharField(default='CONTROL', max_length=7)
    deep_embed = models.EmbeddedField(model_container=ContainerModel)

    objects = models.DjongoManager()


# Model for use w/ testing nested arrays of embedded models,
class ArrayContainerModel(models.Model):
    _id = models.ObjectIdField()
    embed_list = models.ArrayField(model_container=EmbedModel)

    objects = models.DjongoManager()


# --- Relation Containing Models --- #
# Model related to by RelationContainerModel
class ManyToManyRelatedModel(models.Model):
    _id = models.ObjectIdField()
    boolean = models.BooleanField(default=True)
    smol_int = models.SmallIntegerField()

    objects = models.DjongoManager()


class ForeignKeyRelatedModel(models.Model):
    _id = models.ObjectIdField()
    null_bool = models.NullBooleanField()
    description = models.TextField()

    objects = models.DjongoManager()


# Model with representative types of relations
class RelationContainerModel(models.Model):
    _id = models.ObjectIdField()
    control_val = models.CharField(default='CONTROL', max_length=10)
    fk_field = models.ForeignKey(to=ForeignKeyRelatedModel,
                                 on_delete=models.CASCADE)
    mtm_field = models.ManyToManyField(to=ManyToManyRelatedModel,
                                       blank=True,
                                       related_name='container_field')

    objects = models.DjongoManager()


# Model related to by ArrayRelationModel
class ArrayRelatedModel(models.Model):
    _id = models.ObjectIdField()
    email = models.EmailField()

    objects = models.DjongoManager()


class ArrayRelationModel(models.Model):
    _id = models.ObjectIdField()
    int_val = models.IntegerField(default=-1234)
    arr_relation = models.ArrayReferenceField(
        to=ArrayRelatedModel,
        blank=True,
        on_delete=models.CASCADE
    )

    objects = models.DjongoManager()
