try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

try:
    import pypandoc
    long_description = pypandoc.convert_file('README.rst', 'rst')
except(IOError, ImportError):
    long_description = None

setup(
    name='apscheduler-intervalcron',
    packages=['intervalcron'],
    version='0.1.0',
    py_modules=['intervalcron'],
    install_requires=[
        'apscheduler',
        'python-dateutil'
    ],
    test_suite="tests",
    entry_points={
        'apscheduler.triggers': ['intervalcron = intervalcron:IntervalCronTrigger']
    },

    license='MIT',
    description='Interval Cron Trigger Plugin for APScheduler',
    long_description=long_description,
    author='Neeraj',
    author_email='durgapalneeraj@gmail.com',
    url='https://github.com/Code0987/apscheduler-intervalcron',
    keywords=[
        'apscheduler',
        'interval',
        'cron'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)
