from rest_framework.utils import field_mapping


def get_generic_embed_kwargs(embed_info):
    kwargs = {'read_only': True}
    kwargs['model_field'] = embed_info.model_field
    return kwargs


def get_nested_embed_kwargs(field_name, embed_info):
    model_field, is_array = embed_info
    kwargs = {}

    if is_array:
        kwargs = {'many': True}

    if model_field is not None:
        if (model_field.verbose_name and
                field_mapping.needs_label(model_field, field_name)):
            kwargs['label'] = model_field.verbose_name
        if model_field.help_text:
            kwargs['help_test'] = model_field.help_text
        if not model_field.editable:
            kwargs['read_only'] = True
            return kwargs  # If the field is read only, finish here

        if model_field.has_default() or model_field.blank or model_field.null:
            kwargs['required'] = False
        if model_field.null:
            kwargs['allow_null'] = True
        if model_field.validators:
            kwargs['validators'] = model_field.validators
        # Unique keyword not currently supported

    return kwargs
