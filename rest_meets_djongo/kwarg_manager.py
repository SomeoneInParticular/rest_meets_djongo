from rest_framework.utils import field_mapping


def get_generic_embed_kwargs(embed_info):
    kwargs = {'read_only': True}
    kwargs['model_field'] = embed_info.model_field
    return kwargs


def get_nested_embed_kwargs(field_name, embed_info):
    model_field, is_array = embed_info
    kwargs = {'many': is_array}

    if field_mapping.needs_label(model_field, field_name):
        kwargs['label'] = model_field.verbose_name

    return kwargs
