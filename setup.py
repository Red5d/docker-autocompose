from setuptools import setup, find_packages
setup(
    name = "docker-autocompose",
    version = "1.0",
    packages = find_packages(),
    install_requires = ['pyaml, docker-py'],
    entry_points={
        'console_scripts': [
            'autocompose = autocompose',
        ]
    }
)
