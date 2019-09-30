from setuptools import setup

setup(
    name="SnapshotAlyzer-3000",
    version="1.0",
    author="Tiffany Gray",
    author_email="KarateTD@yahoo.com",
    description="SnapshotAlyzer 3000",
    license="GPLv3+",
    packages=['shotty'],
    url="https://github.com/KarateTD/snapshotalyzer-3000",
    install_requires=[
        'click',
        'boto3'
    ],
    entry_points='''
        [console_scripts]
        shotty=shotty.shotty:cli
    ''',

)
