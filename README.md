rest-meets-djongo
===
A package which enables serialization of Djongo fields with 
django-rest-framework's (DRF) serializers and viewsets

## Features
**NOTE: This repo is currently under development, and most (if not all) 
of its features are likely to throw errors or behave in unexpected ways; 
use at your own risk**

Similar to DRF ModelSerializers, creating serializers using 
DjongoModelSerializer allows for the following fields to be detected and 
automatically managed through DRF's serializer setup. These fields 
include:
* ObjectIDField
* EmbeddedModelField
* ArrayModelField (WIP)
* ArrayReferenceField (WIP)

## Usage
<ol><li>
Install rest-meets-djongo:

```
pip install rest_meets_djongo
```

</li><li>
Replace REST's 'ModelSerializer' with 'DjongoModelSerializer' and enjoy 
Djongo model serializeation

</li></ol>

## Requirements:
(Earlier version testing is currently being testing; these are just the 
confirmed functional versions)

1. Python 3.6 or higher
2. MongoDB 4.0 or higher
3. djangorestframework 3.9 or higher
4. djongo 1.2 or higher


