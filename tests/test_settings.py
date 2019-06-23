from django.conf import settings

SECRET_KEY = 'T35TK3Y'

settings.configure(
    DEBUG=True,
    TEMPLATE_DEBUG=True,
    SECRET_KEY=SECRET_KEY,
    DATABASES={
        'default': {
            'ENGINE': 'djongo',
            'NAME': 'test_db'
        }
    }
)