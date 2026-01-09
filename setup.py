from setuptools import setup, find_packages

setup(
    name='dicom_utils',
    version='0.2.1',
    packages=find_packages(),
    install_requires=[
        'ipywidgets>=7.0.0',
        'Pillow>=8.0.0',
        'numpy>=1.19.0'
    ],
    author='Marcin Kostur',
    description='A package for interactive DICOM visualization',
)
