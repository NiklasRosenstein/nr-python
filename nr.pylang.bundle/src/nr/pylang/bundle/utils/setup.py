
import nr.fs
import os
import setuptools
import six


def load_setup_configuration(filename):
    """
    Loads the setup file specified with *filename* and returns the arguments
    passed to #setuptools.setup() in this script.
    """

    class SetupKwargs(BaseException):
        def __init__(self, kwargs):
            self.kwargs = kwargs

    def new_setup(**kwargs):
        raise SetupKwargs(kwargs)

    filename = nr.fs.canonical(filename)
    old_setup = setuptools.setup
    setuptools.setup = new_setup
    old_cwd = os.getcwd()
    os.chdir(nr.fs.dir(filename))
    try:
        with open(filename) as fp:
            scope = {'__name__': '__main__', '__file__': filename}
            six.exec_(compile(fp.read(), filename, 'exec'), scope)
    except SetupKwargs as exc:
        return exc.kwargs
    else:
        raise RuntimeError('setuptools.setup() was not called in file "{}"'
            .format(filename))
    finally:
        os.chdir(old_cwd)
        setuptools.setup = old_setup
