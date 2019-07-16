from rest_framework import serializers as drf_ser

from rest_meets_djongo import serializers as rmd_ser

from tests import models as test_models


class GenericModelSerializer(drf_ser.ModelSerializer):

    class Meta:
        model = test_models.GenericModel
        fields = '__all__'


class EmbedModelSerializer(rmd_ser.EmbeddedModelSerializer):

    class Meta:
        model = test_models.EmbedModel
        fields = '__all__'


class NestedModelSerializer(rmd_ser.DjongoModelSerializer):

    generic_val = GenericModelSerializer()
    embed_val = EmbedModelSerializer()

    class Meta:
        model = test_models.DualEmbedModel
        fields = '__all__'
