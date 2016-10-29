import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()
    
# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-disbi',
    version=__import__("disbi").__version__,
    packages=find_packages(),
    include_package_data=True,
    license='MIT License',
    description='A Django app framework for managing and integrating systems biology data.',
    long_description=README,
    url='https://github.com/DISBi/django-disbi',
    download_url='https://github.com/DISBi/django-disbi/archive/0.0.2.tar.gz',
    author='Rüdiger Frederik Busche',
    author_email='ruedigerbusche@web.de',
    install_requires=[
        'django>=1.9',
        'django-import-export==0.5.0',
        'numpy>=1.11.0',
        'matplotlib>=1.5.1',
        'more-itertools',
        'psycopg2>=2.6',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.9',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License', 
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
