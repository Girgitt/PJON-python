from distutils.core import setup
setup(
  name='pjon_python',
  packages=['pjon_python', 'pjon_python.protocol', 'pjon_python.strategies', 'pjon_python.utils'],
  version='4.2.2',
  description='Python implementation of the PJON communication protocol.',
  author='Zbigniew Zasieczny',
  author_email='z.zasieczny@gmail.com',
  url='https://github.com/Girgitt/PJON-python',
  download_url='https://github.com/Girgitt/PJON-python/tarball/4.2.2',
  keywords=['PJON', 'multimaster', 'serial', 'RS485', 'arduino'],
  classifiers=[],
)