rest-meets-djongo
===
This package enables default model serializers for models with Djongo 
fields to be generated, for use in Django-Rest-Framework apps

## Features
**NOTE: This repo is currently under active development, and many of the
features of the package may act in strange ways. Please report any issues 
to 'https://gitlab.com/SomeoneInParticular/rest_meets_djongo/issues' as 
you find them**

Similar to DRF ModelSerializers, creating serializers using 
DjongoModelSerializer allows for the following fields to be detected and 
automatically managed through DRF's serializer setup. These fields 
include:
* ObjectIDField
* EmbeddedModelField
* ArrayModelField

The following are currently not fully functional, and as a result are 
not explicitly supported (yet):
* ForeignKeyField (Reverse relations are not generated, even if specified, 
by Djongo)
* ManyToManyField (Reverse relations are not generated, even if specified, 
by Djongo)
* ArrayReferenceField (WIP)

## Installation
<ol><li>
Install rest-meets-djongo:

```
pip install rest-meets-djongo
```

</li><li>
Replace REST's 'ModelSerializer' with 'DjongoModelSerializer' and enjoy!
</li></ol>

## Requirements
(Alternate version testing is currently underway; these are just the 
confirmed functional versions)

1. Python 3.6 or higher
2. MongoDB 4.0 or higher
3. djangorestframework 3.9 or higher
4. djongo 1.2 or higher
