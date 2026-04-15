"""
Django settings for PromptX project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'change-me-in-production')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'social_django',
    'api',
    'enhancer',
]

AUTHENTICATION_BACKENDS = [
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
]

# Google OAuth
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('GOOGLE_OAUTH2_CLIENT_ID', '')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv('GOOGLE_OAUTH2_CLIENT_SECRET', '')

# Development settings
SOCIAL_AUTH_REDIRECT_IS_HTTPS = False  # Disable HTTPS requirement for local dev
SOCIAL_AUTH_JSONFIELD_ENABLED = True   # Better field support for some DBs

# Connection settings to prevent premature resets
SOCIAL_AUTH_FIELDS_STORED_IN_SESSION = ['state']
SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {
    'access_type': 'offline',
    'approval_prompt': 'force'
}

# Increase timeouts for outgoing requests
SOCIAL_AUTH_REQUESTS_TIMEOUT = 10 
SOCIAL_AUTH_CONNECT_TIMEOUT = 10

# OAuth Pipeline
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'api.pipeline.send_welcome_email_pipeline',  # Custom welcome email
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

# Login redirect
LOGIN_REDIRECT_URL = '/choose/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/'

# Session
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'api.middleware.APIKeyMiddleware',
]

ROOT_URLCONF = 'promptx_project.urls'
WSGI_APPLICATION = 'promptx_project.wsgi.application'

# CORS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-api-key',
]

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR.parent, 'frontend')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Database - SQLite (change to PostgreSQL for production)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Cache — required by django-ratelimit

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'promptx-cache',
        'TIMEOUT': 3600,
    }
}

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '200/hour',
    },
    'EXCEPTION_HANDLER': 'enhancer.exceptions.custom_exception_handler',
}

# ═══════════════════════════════════════════════
# PROMPTX ENGINE CONFIGURATION
# ═══════════════════════════════════════════════
PROMPTX = {
    'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY', ''),
    'DEFAULT_MODEL': 'gpt-4',
    'MAX_INPUT_LENGTH': 10000,
    'MAX_OUTPUT_TOKENS': 4000,

    # Pipeline configuration
    'PIPELINE': {
        'ENABLE_FACT_CHECK': True,
        'ENABLE_GRAMMAR_CHECK': True,
        'ENABLE_COMPLEXITY_ANALYSIS': True,
        'ENABLE_ITERATIVE_REFINEMENT': True,
        'MAX_REFINEMENT_ITERATIONS': 3,
        'MIN_QUALITY_THRESHOLD': 0.70,
        'TARGET_QUALITY_SCORE': 0.90,
    },

    # Scoring weights
    'SCORING_WEIGHTS': {
        'clarity': 0.20,
        'specificity': 0.20,
        'completeness': 0.20,
        'structure': 0.15,
        'actionability': 0.15,
        'grammar': 0.10,
    },

    # Validation
    'VALIDATION': {
        'CHECK_URL_VALIDITY': True,
        'CHECK_CODE_SYNTAX': True,
        'CHECK_LOGICAL_CONSISTENCY': True,
        'CHECK_GRAMMAR': True,
        'URL_TIMEOUT': 5,
    },
}

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
>>>>>>> upstream/main

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'promptx.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'enhancer': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Static files
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'

# Server port
PORT = int(os.getenv('PORT', 8000))
