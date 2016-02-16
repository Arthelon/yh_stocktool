from distutils.core import setup

with open('requirements.txt', 'rt') as f:
    requirements = f.read().split('\n')

setup(
    name='yh_stocktool',
    version='0.0.1',
    py_modules=['yh_stocktool'],
    url='https://github.com/Arthelon/yh_stocktool',
    license='MIT License',
    author='Arthelon',
    author_email='hsing.daniel@gmail.com',
    description='Stock quote retrieval and storage tool that uses Yahoo Finance APIs',
    install_required=requirements,
    entry_points={
        'console_scripts': 'yh_stocktool = yh_stocktool:main'
    }
)
