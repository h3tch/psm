try:
    import vps_setup
except ModuleNotFoundError as e:
    import subprocess
    p = subprocess.run(['pip', 'install', 'vps-setup'])
    import vps_setup
import psm

requirements = ['vps-setup', 'vps-py', 'numpy', 'pkgconfig']

vps_setup.default(
    psm.info,
    author='Michael Hecher',
    author_email='michael.hecher@gmail.com',
    description='Perceptual shadow mapping.',
    url='cg.tuwien.ac.at',
    setup_requires=requirements,
    install_requires=requirements,
    python_requires='>=3.5',
    license='Proprietary',
    classifiers=['License :: Other/Proprietary License']
)
