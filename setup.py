from setuptools import setup, find_packages

setup(name='answer'
     ,version='0.0.0'

     ,url='https://github.com/yabok/answer'

     ,author='Johannes Löthberg'
     ,author_email='johannes@kyriasis.com'

     ,license='ISC'

     ,classifiers=['Development Status :: 1 - Planning'
                  ,'License :: OSI Approved :: ISC License (ISCL)'
                  ,'Programming Language :: Python :: 3.6']

     ,packages=find_packages()

     ,install_requires=['trio', 'h11']
     ,dependency_links=['git+https://github.com/python-trio/trio#egg=trio'])
