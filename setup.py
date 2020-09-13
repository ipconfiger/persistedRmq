# coding=utf8

__author__ = 'Alexander.Li'

from setuptools import setup, find_packages

version = '0.0.2'

setup(name='persistedRmq',
      version=version,
      description="A simple MQ based on Redis pubsub, but won't lose message",
      long_description="""\
A simple MQ based on Redis pubsub, but won't lose message(Based on asyncio, only works on Python 3)
""",
      classifiers=[],
      keywords='MQ Redis Pubsub Persisted',
      author='Alexander.Li',
      author_email='superpowerlee@gmail.com',
      url='https://github.com/ipconfiger/persistedRmq',
      license='GNU General Public License v3.0',
      packages=find_packages(exclude=['ez_setup', 'examples']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          # -*- Extra requirements: -*-
          'aioredis',
      ],
      entry_points={},
      )
