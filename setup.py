from setuptools import setup, find_packages

import glob

# define scripts to be installed by the PyPI package
scripts = glob.glob('bin/*')

setup(name='directional_cnns',
      version='0.2',
      packages=find_packages(),
      description='Experiments with directional CNNs for key and tempo estimation',
      author='Hendrik Schreiber',
      author_email='hs@tagtraum.com',
      license='Attribution 3.0 Unported (CC BY 3.0)',
      scripts=scripts,
      install_requires=[
          'h5py==3.9.0',
          'pytest==7.4.0',
          'scikit-learn==1.3.0',
          'librosa==0.10.1',
          'joblib==1.3.2',
        #   'tensorflow==2.12.0', mannualy install your version of tensorflow
      ],
      include_package_data=True,
      zip_safe=False)
