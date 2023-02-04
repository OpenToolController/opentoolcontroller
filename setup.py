from setuptools import setup, find_packages

setup(
    name='OpenToolController',
    version='0.1',
    description='An opensource machine controller.',
    author='Shawn Wright',
    author_email='399wright@gmail.com',
    packages=find_packages(),
    setup_requires=["pytest-runner"],
    tests_require=['pytest','pytest-qt','discover'],
    install_requires=['pyqt5','numpy','scipy'], #external packages as dependencies
)
