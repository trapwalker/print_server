from setuptools import setup, find_packages

setup(
    name='print_server',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        "aiohttp==3.9.3",
        "pycups>=2.0.1",
        "python-dotenv==1.0.1",
        # "pyjwt==2.8.0",
        # "pytz==2024.1",
        # "sentry-sdk==1.41.0",
    ],

    author='Sergey Pankov',
    author_email='svpmailbox@gmail.com',
    description='Сервис, получающий задания на печать из API и отправляющий их на указанный принтер',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/trapwalker/print_server',
    license='BSD:',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: BSD:',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
