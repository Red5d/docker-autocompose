from setuptools import setup, find_packages
setup(
    name = "docker-autocompose",
    version = "1.0",
    packages = find_packages(),
    install_requires = ['pyaml>=15.8.2', 'docker-py>=1.6.0'],
    entry_points={
        'console_scripts': [
            'autocompose = autocompose:main',
        ]
    }
)
