from gettext import gettext as _
import errno
import logging
import os
import shutil

from pulp.common.config import read_json_config
from pulp.plugins.util.publish_step import AtomicDirectoryPublishStep
from pulp.plugins.util.publish_step import PluginStep, UnitModelPluginStep
from pulp.plugins.distributor import Distributor

from pulp_deb.common import ids, constants
from pulp_deb.plugins.db import models
from . import configuration, yum_plugin_util
from debpkgr import aptrepo

_logger = logging.getLogger(__name__)


CONF_FILE_PATH = 'server/plugins.conf.d/%s.json' % ids.TYPE_ID_DISTRIBUTOR


def entry_point():
    """
    Entry point that pulp platform uses to load the distributor
    :return: distributor class and its config
    :rtype:  Distributor, dict
    """
    return DebDistributor, read_json_config(CONF_FILE_PATH)


class DebDistributor(Distributor):
    @classmethod
    def metadata(cls):
        """
        Used by Pulp to classify the capabilities of this distributor. The
        following keys must be present in the returned dictionary:

        * id - Programmatic way to refer to this distributor. Must be unique
          across all distributors. Only letters and underscores are valid.
        * display_name - User-friendly identification of the distributor.
        * types - List of all content type IDs that may be published using this
          distributor.

        :return:    keys and values listed above
        :rtype:     dict
        """
        return {
            'id': ids.TYPE_ID_DISTRIBUTOR,
            'display_name': _('Deb Distributor'),
            'types': sorted(ids.SUPPORTED_TYPES)
        }

    def __init__(self):
        super(DebDistributor, self).__init__()
        self._publisher = None
        self.canceled = False

    def publish_repo(self, transfer_repo, publish_conduit, config):
        """
        Publishes the given repository.

        :param transfer_repo: metadata describing the repository
        :type  transfer_repo: pulp.plugins.model.Repository

        :param publish_conduit: provides access to relevant Pulp functionality
        :type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit

        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginConfiguration

        :return: report describing the publish run
        :rtype:  pulp.plugins.model.PublishReport
        """
        _logger.debug('Publishing deb repository: %s' % transfer_repo.id)
        self._publisher = Publisher(transfer_repo, publish_conduit, config,
                                    plugin_type=ids.TYPE_ID_DISTRIBUTOR)
        return self._publisher.process_lifecycle()

    def cancel_publish_repo(self):
        """
        Call cancellation control hook.
        """
        _logger.debug('Canceling deb repository publish')
        self.canceled = True
        if self._publisher is not None:
            self._publisher.cancel()

    def distributor_removed(self, repo, config):
        """
        Called when a distributor of this type is removed from a repository.
        This hook allows the distributor to clean up any files that may have
        been created during the actual publishing.

        The distributor may use the contents of the working directory in cleanup.
        It is not required that the contents of this directory be deleted by
        the distributor; Pulp will ensure it is wiped following this call.

        If this call raises an exception, the distributor will still be removed
        from the repository and the working directory contents will still be
        wiped by Pulp.

        :param repo: metadata describing the repository
        :type  repo: pulp.plugins.model.Repository

        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        # remove the directories that might have been created for this repo/distributor

        repo_dir = configuration.get_master_publish_dir(
            repo, ids.TYPE_ID_DISTRIBUTOR)
        shutil.rmtree(repo_dir, ignore_errors=True)
        # remove the symlinks that might have been created for this
        # repo/distributor
        rel_path = configuration.get_repo_relative_path(repo, config)
        rel_path = rel_path.rstrip(os.sep)
        pub_dirs = [
            configuration.get_http_publish_dir(config),
            configuration.get_https_publish_dir(config),
        ]
        for pub_dir in pub_dirs:
            symlink = os.path.join(pub_dir, rel_path)
            try:
                os.unlink(symlink)
            except OSError as error:
                if error.errno != errno.ENOENT:
                    raise

    def validate_config(self, transfer_repo, config, config_conduit):
        """
        Allows the distributor to check the contents of a potential configuration
        for the given repository. This call is made both for the addition of
        this distributor to a new repository as well as updating the configuration
        for this distributor on a previously configured repository. The implementation
        should use the given repository data to ensure that updating the
        configuration does not put the repository into an inconsistent state.

        The return is a tuple of the result of the validation (True for success,
        False for failure) and a message. The message may be None and is unused
        in the success case. For a failed validation, the message will be
        communicated to the caller so the plugin should take i18n into
        consideration when generating the message.

        The related_repos parameter contains a list of other repositories that
        have a configured distributor of this type. The distributor configurations
        is found in each repository in the "plugin_configs" field.

        :param repo: metadata describing the repository to which the
                     configuration applies
        :type  repo: pulp.plugins.model.Repository

        :param config: plugin configuration instance; the proposed repo
                       configuration is found within
        :type  config: pulp.plugins.config.PluginCallConfiguration

        :param config_conduit: Configuration Conduit;
        :type  config_conduit: pulp.plugins.conduits.repo_config.RepoConfigConduit

        :return: tuple of (bool, str) to describe the result
        :rtype:  tuple

        :raises: PulpCodedValidationException if any validations failed
        """
        repo = transfer_repo.repo_obj
        return configuration.validate_config(repo, config, config_conduit)


class Publisher(PluginStep):
    description = _("Publishing Debian artifacts")

    def __init__(self, repo, conduit, config, plugin_type, **kwargs):
        super(Publisher, self).__init__(step_type=constants.PUBLISH_REPO_STEP,
                                        repo=repo,
                                        conduit=conduit,
                                        config=config,
                                        plugin_type=plugin_type)
        self.description = self.__class__.description
        self.add_child(ModulePublisher(conduit=conduit,
                                       config=config, repo=repo))
        repo_relative_path = configuration.get_repo_relative_path(repo, config)
        master_publish_dir = configuration.get_master_publish_dir(
            repo, plugin_type)
        target_directories = []
        listing_steps = []
        if config.get(constants.PUBLISH_HTTP_KEYWORD):
            root_publish_dir = configuration.get_http_publish_dir(config)
            repo_publish_dir = os.path.join(root_publish_dir,
                                            repo_relative_path)
            target_directories.append(root_publish_dir)
            listing_steps.append(GenerateListingFileStep(root_publish_dir,
                                                         repo_publish_dir))
        if config.get(constants.PUBLISH_HTTPS_KEYWORD):
            root_publish_dir = configuration.get_https_publish_dir(config)
            repo_publish_dir = os.path.join(root_publish_dir,
                                            repo_relative_path)
            target_directories.append(root_publish_dir)
            listing_steps.append(GenerateListingFileStep(root_publish_dir,
                                                         repo_publish_dir))
        target_directories = [('/', os.path.join(x, repo_relative_path))
                              for x in target_directories]
        atomic_publish_step = AtomicDirectoryPublishStep(
            self.get_working_dir(),
            target_directories,
            master_publish_dir)
        atomic_publish_step.description = _("Publishing files to web")
        self.add_child(atomic_publish_step)
        for step in listing_steps:
            self.add_child(step)


class ModulePublisher(PluginStep):
    description = _("Publishing modules")

    def __init__(self, **kwargs):
        kwargs.setdefault('step_type', constants.PUBLISH_MODULES_STEP)
        super(ModulePublisher, self).__init__(**kwargs)
        self.description = self.__class__.description
        work_dir = self.get_working_dir()
        self.publish_units = PublishDebStep(work_dir)
        self.add_child(self.publish_units)
        self.add_child(MetadataStep())

        if self.non_halting_exceptions is None:
            self.non_halting_exceptions = []

    def _get_total(self):
        return len(self.publish_units.units)


class PublishDebStep(UnitModelPluginStep):
    ID_PUBLISH_STEP = constants.PUBLISH_DEB_STEP
    Model = models.DebPackage

    def __init__(self, work_dir, **kwargs):
        super(PublishDebStep, self).__init__(
            self.ID_PUBLISH_STEP, [self.Model], **kwargs)
        self.working_dir = work_dir
        self.units = []

    def process_main(self, item=None):
        self.units.append(item)


class MetadataStep(PluginStep):
    Codename = 'stable'
    Component = 'main'

    def __init__(self):
        super(MetadataStep, self).__init__(constants.PUBLISH_REPODATA)

    def process_main(self, unit=None):
        units = self.parent.publish_units.units
        filenames = [x.storage_path for x in units]
        sign_options = configuration.get_gpg_sign_options(self.get_repo(),
                                                          self.get_config())
        arch = 'amd64'
        repometa = aptrepo.AptRepoMeta(
            codename=self.Codename,
            components=[self.Component],
            architectures=[arch])
        arepo = aptrepo.AptRepo(self.get_working_dir(),
                                repo_name=self.get_repo().id,
                                metadata=repometa,
                                gpg_sign_options=sign_options)

        arepo.create(filenames,
                     component=self.Component,
                     architecture=arch,
                     with_symlinks=True)


class GenerateListingFileStep(PluginStep):
    def __init__(self, root_dir, target_dir,
                 step=constants.PUBLISH_GENERATE_LISTING_FILE_STEP):
        """
        Initialize and set the ID of the step
        """
        super(GenerateListingFileStep, self).__init__(step)
        self.description = _("Writing Listings File")
        self.root_dir = root_dir
        self.target_dir = target_dir

    def process_main(self, item=None):
        yum_plugin_util.generate_listing_files(self.root_dir, self.target_dir)
