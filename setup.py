from setuptools import setup, find_packages
setup(
    name = "docker-autocompose",
    version = "1.0.1",
    description = "Generate a docker-compose yaml definition from a running container",
    url = "https://github.com/Red5d/docker-autocompose",
    author = "Red5d",
    license = "GPLv2",
    keywords = "docker yaml container",
    packages = find_packages(),
    install_requires = ['pyaml>=15.8.2', 'docker-py>=1.6.0'],
    scripts = ['autocompose.py'],
    entry_points={
        'console_scripts': [
            'autocompose = autocompose:main',
        ]
    }
)
