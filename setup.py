from distutils.core import setup

setup(
    name='chimera_t80cam',
    version='0.0.1',
    packages=['chimera_t80cam', 'chimera_t80cam.instruments',
              'chimera_t80cam.instruments.ebox',
              'chimera_t80cam.instruments.ebox.fsufilters',
              'chimera_t80cam.instruments.ebox.fsupolarimeter'],
    requires=['chimera','git+https://github.com/astroufsc/python-si-tcpclient.git','adshli'],
    scripts=[],
    url='http://github.com/astroufsc/chimera_t80cam',
    license='GPL v2',
    author='Tiago Ribeiro',
    author_email='tribeiro@ufs.br',
    description='Chimera plugins for T80Cam'
)
