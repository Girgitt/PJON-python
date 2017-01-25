from setuptools import setup

try:
    from pypandoc import convert
    read_md = lambda f: convert(f, 'rst')
except ImportError:
    print("warning: pypandoc module not found, could not convert Markdown to RST")
    read_md = lambda f: open(f, 'r').read()

setup(
  name='pjon_python',
  packages=['pjon_python', 'pjon_python.protocol', 'pjon_python.strategies', 'pjon_python.utils'],
  version='4.2.4',
  description='Python implementation of the PJON communication protocol.',
  long_description=read_md('README.md'),
  author='Zbigniew Zasieczny',
  author_email='z.zasieczny@gmail.com',
  url='https://github.com/Girgitt/PJON-python',
  download_url='https://github.com/Girgitt/PJON-python/tarball/4.2.4',
  keywords=['PJON', 'multimaster', 'serial', 'RS485', 'arduino'],
  classifiers=[],
)