from setuptools import setup, find_packages

setup(
    name='dicom_utils',
    version='0.4.0',
    packages=find_packages(),
    install_requires=[
        'ipywidgets>=7.0.0',
        'ipyevents',
        'Pillow>=8.0.0',
        'numpy>=1.19.0'
    ],
    author='Marcin Kostur',
    description='A package for interactive DICOM visualization',
)
