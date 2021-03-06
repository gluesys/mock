import os
import tempfile
import shutil

from unittest import mock
from unittest.mock import MagicMock

from mockbuild.util import TemplatedDictionary, load_defaults
from mockbuild.buildroot import Buildroot
from mockbuild.package_manager import _PackageManager, Dnf


class TestPackageManager:

    def setup_method(self, method):
        self.workdir = tempfile.mkdtemp(prefix='mock-test')

        testdir = os.path.dirname(os.path.realpath(__file__))
        plugindir = os.path.join(testdir, '..', 'py', 'mockbuild')
        plugindir = os.path.realpath(plugindir)

        self.config_opts = load_defaults(None, 'git', plugindir)
        self.config_opts['root'] = 'distro-version-arch'
        self.config_opts['basedir'] = self.workdir
        self.config_opts["resultdir"] = "{{basedir}}/{{root}}/result"
        self.config_opts['chroothome'] = '/builddir'
        self.config_opts['chrootgid'] = '135'
        self.config_opts['package_manager'] = 'dnf'

        with mock.patch('mockbuild.buildroot.package_manager'):
            with mock.patch('mockbuild.util.cmpKernelVer') as kv:
                kv.return_value = True
                self.bootstrap_buildroot = Buildroot(
                    self.config_opts.copy(),
                    None,         # state
                    MagicMock(),  # state
                    MagicMock(),  # plugins
                    None,         # bootstrap_buildroot
                    True,         # is_bootstrap
                )

                self.buildroot = Buildroot(
                    self.config_opts,
                    None,         # uidManager
                    MagicMock(),  # state
                    MagicMock(),  # plugins
                    self.bootstrap_buildroot,
                    False,        # is_bootstrap
                )

        self.package_manager = _PackageManager(
            self.buildroot.config,
            self.buildroot,
            self.buildroot.plugins,
            self.bootstrap_buildroot,
            False
        )

        self.package_manager_bootstrap = _PackageManager(
            self.bootstrap_buildroot.config,
            self.bootstrap_buildroot,
            self.bootstrap_buildroot.plugins,
            self.buildroot.plugins,
            False
        )

    def teardown_method(self, method):
        shutil.rmtree(self.workdir)

    def get_user_bind_mounts_from_config(self, config):
        pm = self.package_manager_bootstrap
        pm.pkg_manager_config = config
        pm.initialize_config()
        pm._bind_mount_repos_to_bootstrap()
        return self.bootstrap_buildroot.mounts.user_mounts

    def test_absolute_path_name_in_baseurl(self):
        repo_directory = os.path.join(self.workdir, 'repo')
        os.mkdir(repo_directory)
        config = """
        [main]
        something = 1

        [external]
        baseurl = http://exmaple.com/test/

        [fedora]
        baseurl = {}
        """.format(repo_directory)
        mounts = self.get_user_bind_mounts_from_config(config)
        assert len(mounts) == 1
        assert mounts[0].srcpath == repo_directory
        assert mounts[0].bindpath.startswith(self.workdir)
        assert mounts[0].bindpath.endswith(repo_directory)

    def test_file_colon_slash_path_name_in_baseurl(self):
        repo_directory = os.path.join(self.workdir, 'repo')
        os.mkdir(repo_directory)
        config = """
        [main]
        something = 1

        [fedora]
        baseurl = file://{}
        """.format(repo_directory)
        mounts = self.get_user_bind_mounts_from_config(config)
        assert len(mounts) == 1
        assert mounts[0].srcpath == repo_directory
        assert mounts[0].bindpath.startswith(self.workdir)
        assert mounts[0].bindpath.endswith(repo_directory)

    def test_dir_doesnt_exist(self):
        repo_directory = os.path.join(self.workdir, 'repo')
        config = """
        [main]
        something = 1

        [fedora]
        baseurl = file://{}
        """.format(repo_directory)
        mounts = self.get_user_bind_mounts_from_config(config)
        assert len(mounts) == 0
