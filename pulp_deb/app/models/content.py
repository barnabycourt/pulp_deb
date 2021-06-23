import os

from django.db import models

from pulpcore.plugin.models import Content


BOOL_CHOICES = [(True, "yes"), (False, "no")]


class GenericContent(Content):
    """
    The "generic" content.

    This model is meant to map to all files in the upstream repository, that
    are not handled by a more specific model.
    Those units are used for the verbatim publish method.
    """

    TYPE = "generic"

    relative_path = models.TextField(null=False)
    sha256 = models.CharField(max_length=255, null=False)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("relative_path", "sha256"),)


class ReleaseFile(Content):
    """
    The "ReleaseFile" content.

    This model holds an artifact to the upstream Release file.
    """

    TYPE = "release_file"

    codename = models.CharField(max_length=255)
    suite = models.CharField(max_length=255)
    distribution = models.CharField(max_length=255)
    components = models.CharField(max_length=255, blank=True)
    architectures = models.CharField(max_length=255, blank=True)
    relative_path = models.TextField()
    sha256 = models.CharField(max_length=255)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (
            (
                "codename",
                "suite",
                "distribution",
                "components",
                "architectures",
                "relative_path",
                "sha256",
            ),
        )

    @property
    def main_artifact(self):
        """
        Retrieve the plain ReleaseFile artifact.
        """
        return self._artifacts.get(sha256=self.sha256)


class PackageIndex(Content):
    """
    The "PackageIndex" content type.

    This model represents the Packages file for a specific
    component - architecture combination.
    It's artifacts should include all (non-)compressed versions
    of the upstream Packages file.
    """

    TYPE = "package_index"

    release = models.ForeignKey(ReleaseFile, on_delete=models.CASCADE)
    component = models.CharField(max_length=255)
    architecture = models.CharField(max_length=255)
    relative_path = models.TextField()
    sha256 = models.CharField(max_length=255)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        verbose_name_plural = "PackageIndices"
        unique_together = (("relative_path", "sha256"),)

    @property
    def main_artifact(self):
        """
        Retrieve the uncompressed PackageIndex artifact.
        """
        return self._artifacts.get(sha256=self.sha256)


class SourceIndex(Content):
    """
    The "SourceIndex" content type.

    This model represents the Sources file for a specific
    component.
    It's artifacts should include all (non-)compressed versions
    of the upstream Sources file.
    """

    TYPE = "source_index"

    release = models.ForeignKey(ReleaseFile, on_delete=models.CASCADE)
    component = models.CharField(max_length=255)
    relative_path = models.TextField()
    sha256 = models.CharField(max_length=255)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        verbose_name_plural = "SourceIndices"
        unique_together = (("relative_path", "sha256"),)

    @property
    def main_artifact(self):
        """
        Retrieve teh uncompressed SourceIndex artifact.
        """
        return self._artifacts.get(sha256=self.sha256)


class InstallerFileIndex(Content):
    """
    The "InstallerFileIndex" content type.

    This model represents the MD5SUMS and SHA256SUMS files for a specific
    component - architecture combination.
    It's artifacts should include all available versions of those SUM-files
    with the sha256-field pointing to the one with the sha256 algorithm.
    """

    TYPE = "installer_file_index"

    FILE_ALGORITHM = {"SHA256SUMS": "sha256", "MD5SUMS": "md5"}  # Are there more?

    release = models.ForeignKey(ReleaseFile, on_delete=models.CASCADE)
    component = models.CharField(max_length=255)
    architecture = models.CharField(max_length=255)
    relative_path = models.TextField()
    sha256 = models.CharField(max_length=255)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        verbose_name_plural = "InstallerFileIndices"
        unique_together = (("relative_path", "sha256"),)

    @property
    def main_artifact(self):
        """
        Retrieve the uncompressed SHA256SUMS artifact.
        """
        return self._artifacts.get(sha256=self.sha256)


class BasePackage(Content):
    """
    Abstract base class for package like content.
    """

    MULTIARCH_CHOICES = [
        ("no", "no"),
        ("same", "same"),
        ("foreign", "foreign"),
        ("allowed", "allowed"),
    ]

    package = models.TextField()  # package name
    source = models.TextField(null=True)  # source package name
    version = models.TextField()
    architecture = models.TextField()  # all, i386, ...
    section = models.TextField(null=True)  # admin, comm, database, ...
    priority = models.TextField(null=True)  # required, standard, optional, extra
    origin = models.TextField(null=True)
    tag = models.TextField(null=True)
    bugs = models.TextField(null=True)
    essential = models.BooleanField(null=True, choices=BOOL_CHOICES)
    build_essential = models.BooleanField(null=True, choices=BOOL_CHOICES)
    installed_size = models.IntegerField(null=True)
    maintainer = models.TextField()
    original_maintainer = models.TextField(null=True)
    description = models.TextField()
    description_md5 = models.TextField(null=True)
    homepage = models.TextField(null=True)
    built_using = models.TextField(null=True)
    auto_built_package = models.TextField(null=True)
    multi_arch = models.TextField(null=True, choices=MULTIARCH_CHOICES)

    # Depends et al
    breaks = models.TextField(null=True)
    conflicts = models.TextField(null=True)
    depends = models.TextField(null=True)
    recommends = models.TextField(null=True)
    suggests = models.TextField(null=True)
    enhances = models.TextField(null=True)
    pre_depends = models.TextField(null=True)
    provides = models.TextField(null=True)
    replaces = models.TextField(null=True)

    # relative path in the upstream repository
    relative_path = models.TextField(null=False)
    # this digest is transferred to the content as a natural_key
    sha256 = models.TextField(null=False)

    @property
    def name(self):
        """Print a nice name for Packages."""
        return "{}_{}_{}".format(self.package, self.version, self.architecture)

    def filename(self, component=""):
        """Assemble filename in pool directory."""
        sourcename = self.source or self.package
        sourcename = sourcename.split("(", 1)[0].rstrip()
        if sourcename.startswith("lib"):
            prefix = sourcename[0:4]
        else:
            prefix = sourcename[0]
        return os.path.join(
            "pool",
            component,
            prefix,
            sourcename,
            "{}.{}".format(self.name, self.SUFFIX),
        )

    repo_key_fields = ("package", "version", "architecture")

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("relative_path", "sha256"),)
        abstract = True


class Package(BasePackage):
    """
    The "package" content type.

    This model must contain all information that is needed to
    generate the corresponding paragraph in "Packages" files.
    """

    TYPE = "package"

    SUFFIX = "deb"

    class Meta(BasePackage.Meta):
        pass


class InstallerPackage(BasePackage):
    """
    The "installer_package" content type.

    This model must contain all information that is needed to
    generate the corresponding paragraph in "Packages" files.
    """

    TYPE = "installer_package"

    SUFFIX = "udeb"

    class Meta(BasePackage.Meta):
        pass


class Release(Content):
    """
    The "Release" content.

    This model represents a debian release.
    """

    TYPE = "release"

    codename = models.CharField(max_length=255)
    suite = models.CharField(max_length=255)
    distribution = models.CharField(max_length=255)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("codename", "suite", "distribution"),)


class ReleaseArchitecture(Content):
    """
    The ReleaseArchitecture content.

    This model represents an architecture in association to a Release.
    """

    TYPE = "release_architecture"

    architecture = models.CharField(max_length=255)
    release = models.ForeignKey(Release, on_delete=models.CASCADE)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("architecture", "release"),)


class ReleaseComponent(Content):
    """
    The ReleaseComponent content.

    This model represents a repository component in association to a Release.
    """

    TYPE = "release_component"

    component = models.CharField(max_length=255)
    release = models.ForeignKey(Release, on_delete=models.CASCADE)

    @property
    def plain_component(self):
        """
        The "plain_component" returns the component WITHOUT path prefixes.

        When a Release file is not stored in a directory directly beneath "dists/",
        the components, as stored in the Release file, may be prefixed with the
        path following the directory beneath "dists/".

        e.g.: If a Release file is stored at "REPO_BASE/dists/something/extra/Release",
        then a component normally named "main" may be stored as "extra/main".

        See also: https://wiki.debian.org/DebianRepository/Format#Components
        """
        return os.path.basename(self.component)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("component", "release"),)


class PackageReleaseComponent(Content):
    """
    The PackageReleaseComponent.

    This is the join table that decides, which Packages (in which RepositoryVersions) belong to
    which ReleaseComponents.
    """

    TYPE = "package_release_component"

    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    release_component = models.ForeignKey(ReleaseComponent, on_delete=models.CASCADE)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("package", "release_component"),)


class BaseSource(Content):
    """
    The BaseSource content type.

    This is used to represent a single source file in a "sources" indices file
    paragraph. ie. an lineitem in the Files, Checksums-Sha1, Checksums-Sha256,
    and Checksums-512 lists.
    """

    name = models.TextField(null=False)
    relative_path = models.TextField(null=False)

    size = models.BigIntegerField(null=True)
    md5 = models.CharField(max_length=32, null=True)
    md5sum = models.CharField(max_length=32, null=True)
    sha1 = models.CharField(max_length=40, null=True)
    sha256 = models.CharField(max_length=64, null=False)
    sha512 = models.CharField(max_length=128, null=True)

    dsc_files = models.ForeignKey(
        "DscFile",
        related_name="files",
        on_delete=models.CASCADE,
        null=True,
    )

    dsc_checksums_sha1 = models.ForeignKey(
        "DscFile",
        related_name="checksums_sha1",
        on_delete=models.CASCADE,
        null=True,
    )

    dsc_checksums_sha256 = models.ForeignKey(
        "DscFile",
        related_name="checksums_sha256",
        on_delete=models.CASCADE,
        null=True,
    )

    dsc_checksums_sha512 = models.ForeignKey(
        "DscFile",
        related_name="checksums_sha512",
        on_delete=models.CASCADE,
        null=True,
    )

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("relative_path", "sha256"),)


class SourceFile(BaseSource):
    """
    The SourceFile content type.

    This is used to represent a single source file in a "sources" indices file
    paragraph of either the orig.tar or debian.tar type. These files contain
    no meta-data of their own, only attributes as described in BaseSource.
    """

    TYPE = "source_file"

    def derived_path(self, component=""):
        """Assemble filename in pool directory."""
        sourcename = self.name
        sourcename = sourcename.split("_")[0]
        prefix = sourcename[0]
        return os.path.join(
            "pool",
            component,
            prefix,
            sourcename,
            self.name,
        )

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class DscFile(BaseSource):
    """
    The Debian Source Control file content type.

    This model must contain all information that is needed to
    generate the corresponding paragraph in "Souces" indices files.
    """

    TYPE = "dsc_file"

    SUFFIX = "dsc"

    format = models.TextField()  # the format of the source package
    source = models.TextField()  # source package nameformat
    binary = models.TextField(null=True)  # lists binary packages which a source package can produce
    architecture = models.TextField(null=True)  # all, i386, ...
    version = models.TextField()  # The format is: [epoch:]upstream_version[-debian_revision]
    maintainer = models.TextField()
    uploaders = models.TextField(null=True)  # Names and emails of co-maintainers
    homepage = models.TextField(null=True)
    vcs_browser = models.TextField(null=True)
    vcs_arch = models.TextField(null=True)
    vcs_bzr = models.TextField(null=True)
    vcs_cvs = models.TextField(null=True)
    vcs_darcs = models.TextField(null=True)
    vcs_git = models.TextField(null=True)
    vcs_hg = models.TextField(null=True)
    vcs_mtn = models.TextField(null=True)
    vcs_snv = models.TextField(null=True)
    testsuite = models.TextField(null=True)
    dgit = models.TextField(null=True)
    standards_version = models.TextField()  # most recent version of the standards the pkg complies
    build_depends = models.TextField(null=True)
    build_depends_indep = models.TextField(null=True)
    build_depends_arch = models.TextField(null=True)
    build_conflicts = models.TextField(null=True)
    build_conflicts_indep = models.TextField(null=True)
    build_conflicts_arch = models.TextField(null=True)
    package_list = models.TextField(
        null=True
    )  # all the packages that can be built from the source package

    def __init__(self, *args, **kwargs):
        # Sanatize kwargs
        for kw in ["files", "checksums_sha1", "checksums_sha256", "checksums_sha512"]:
            if kw in kwargs:
                kwargs.pop(kw)
        super().__init__(*args, **kwargs)

    def derived_name(self):
        """Print a nice name for the Dsc file."""
        return "{}_{}.{}".format(self.source, self.version, self.SUFFIX)

    def derived_path(self, component=""):
        """Assemble filename in pool directory."""
        sourcename = self.source
        prefix = sourcename[0]
        return os.path.join(
            "pool",
            component,
            prefix,
            sourcename,
            self.derived_name(),
        )

    repo_key_fields = ("source", "version")

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"


class SourceReleaseComponent(Content):
    """
    The SourceReleaseComponent.

    This is the join table that decides, which Sources (in which RepositoryVersions) belong to
    which ReleaseComponents.
    """

    TYPE = "source_release_component"

    source = models.ForeignKey(SourceFile, on_delete=models.CASCADE)
    release_component = models.ForeignKey(ReleaseComponent, on_delete=models.CASCADE)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("source", "release_component"),)


class DscFileReleaseComponent(Content):
    """
    The DscReleaseComponent.

    This is the join table that decides, which Dsc (in which RepositoryVersions) belong to
    which ReleaseComponents.
    """

    TYPE = "dsc_file_release_component"

    dsc_file = models.ForeignKey(DscFile, on_delete=models.CASCADE)
    release_component = models.ForeignKey(ReleaseComponent, on_delete=models.CASCADE)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
        unique_together = (("dsc_file", "release_component"),)
