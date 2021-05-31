rest-meets-djongo
===
This package enables default model serializers for models with Djongo 
fields to be generated, for use in Django-Rest-Framework apps

**_THIS REPOSITORY IS NOW DEFUNCT. YOU ARE FREE TO USE THE CODE HEREIN FOR YOUR PURPOUSES, BUT IT WILL NO LONGER BE UPDATED. YOU ARE ALSO WELCOME TO FORK THE CODE FOR YOUR OWN PURPOSES._**

## Features
**NOTE: This repo is currently under active development, and many of the
features of the package may act in strange ways. Please report any issues 
to [GitLab](https://gitlab.com/SomeoneInParticular/rest_meets_djongo/issues) 
or [GitHub](https://github.com/SomeoneInParticular/rest_meets_djongo/issues) 
as you find them**

Similar to DRF ModelSerializers, creating serializers using 
DjongoModelSerializer allows for the following fields to be detected and 
automatically managed through DRF's serializer setup. These fields 
include:
* ObjectIDField
* EmbeddedField
* ArrayField

The following are currently not fully functional, and as a result are 
not explicitly supported (yet):
* ArrayReferenceField (WIP)

Some fields are not currently supported fully within Djongo, and as 
such are not supported by this package either (though they will work
to an extent nonetheless):
* ForeignKeyField (Reverse relations are not generated, even if specified, 
by Djongo)
* ManyToManyField (Reverse relations are not generated, even if specified, 
by Djongo)

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
4. djongo 1.3 or higher (use version 0.11 for djongo 1.2 versions)
