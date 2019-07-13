from djongo import models


# --- Basic Models --- #
# Generic, DRF compliant model, with all DRF fields
class GenericModel(models.Model):
    big_int = models.BigIntegerField()
    bool = models.BooleanField()
    char = models.CharField()
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


# Model with its primary key set as its ObjectID
class ObjIDModel(models.Model):
    _id = models.ObjectIdField()
    int_field = models.IntegerField()
    char_field = models.CharField(max_length=5)


# --- Embedded Model Containing Models --- #
# Model for use w/ testing embedded models
class EmbedModel(models.Model):
    int_field = models.IntegerField()
    char_field = models.CharField(max_length=5)

    def __eq__(self, other):
        return (isinstance(other, EmbedModel) and
                self.char_field == other.char_field and
                self.int_field == other.int_field)

    def __str__(self):
        return str(self.int_field) + "-" + str(self.char_field)

    class Meta:
        abstract = True


# Model for use w/ testing nested embedded models
class ContainerModel(models.Model):
    _id = models.ObjectIdField()
    embed_field = models.EmbeddedModelField(model_container=EmbedModel)


# Model for use w/ testing nested arrays of embedded models
class ArrayContainerModel(models.Model):
    _id = models.ObjectIdField()
    embed_list = models.ArrayModelField(model_container=EmbedModel)


# A model setup to have both old DRF embedded model and new RMD embedded
# model serialization (the prior should be caught and throw a warning)
# TODO: confirm the prior is properly caught with warning
class OldAndNewEmbedModel(models.Model):
    _id = models.ObjectIdField()
    generic_val = models.EmbeddedModelField(
        model_container=GenericModel
    )
    embed_val = models.EmbeddedModelField(
        model_container=EmbedModel
    )


# --- Relation Containing Models --- #
# Model with a reverse relation (see RelationContainerModel)
class ReverseRelatedModel(models.Model):
    _id = models.ObjectIdField()
    # container_field = ... (given by related name below)


# Model with most types of relations
class RelationContainerModel(models.Model):
    fk_field = models.ForeignKey(to=GenericModel,
                                 on_delete=models.CASCADE,
                                 related_name='+')
    mfk_field = models.ManyToManyField(to=ReverseRelatedModel,
                                       blank=True,
                                       related_name='container_field')
