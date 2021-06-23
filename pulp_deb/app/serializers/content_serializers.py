from gettext import gettext as _

import os
from pulp_deb.app.models.content import BaseSource

from debian import deb822, debfile

from rest_framework.serializers import CharField, Field, ValidationError
from pulpcore.plugin.models import Artifact, RemoteArtifact
from pulpcore.plugin.serializers import (
    ContentChecksumSerializer,
    MultipleArtifactContentSerializer,
    NoArtifactContentSerializer,
    SingleArtifactContentSerializer,
    SingleArtifactContentUploadSerializer,
    DetailRelatedField,
)

from pulp_deb.app.models import (
    BasePackage,
    GenericContent,
    InstallerFileIndex,
    InstallerPackage,
    Package,
    PackageIndex,
    PackageReleaseComponent,
    Release,
    ReleaseArchitecture,
    ReleaseComponent,
    ReleaseFile,
    SourceIndex,
    DscFile,
    SourceFile,
    SourceReleaseComponent,
    DscFileReleaseComponent,
)


class YesNoField(Field):
    """
    A serializer field that accepts 'yes' or 'no' as boolean.
    """

    def to_representation(self, value):
        """
        Translate boolean to "yes/no".
        """
        if value is True:
            return "yes"
        elif value is False:
            return "no"

    def to_internal_value(self, data):
        """
        Translate "yes/no" to boolean.
        """
        data = data.strip().lower()
        if data == "yes":
            return True
        if data == "no":
            return False
        else:
            raise ValidationError('Value must be "yes" or "no".')


class GenericContentSerializer(SingleArtifactContentUploadSerializer, ContentChecksumSerializer):
    """
    A serializer for GenericContent.
    """

    def deferred_validate(self, data):
        """Validate the GenericContent data."""
        data = super().deferred_validate(data)

        data["sha256"] = data["artifact"].sha256

        content = GenericContent.objects.filter(
            sha256=data["sha256"], relative_path=data["relative_path"]
        )
        if content.exists():
            raise ValidationError(
                _(
                    "There is already a generic content with relative path '{path}' and sha256 "
                    "'{sha256}'."
                ).format(path=data["relative_path"], sha256=data["sha256"])
            )

        return data

    class Meta(SingleArtifactContentUploadSerializer.Meta):
        fields = (
            SingleArtifactContentUploadSerializer.Meta.fields
            + ContentChecksumSerializer.Meta.fields
        )
        model = GenericContent


class ReleaseFileSerializer(MultipleArtifactContentSerializer):
    """
    A serializer for ReleaseFile.
    """

    codename = CharField(help_text='Codename of the release, i.e. "buster".', required=False)

    suite = CharField(help_text='Suite of the release, i.e. "stable".', required=False)

    distribution = CharField(
        help_text='Distribution of the release, i.e. "stable/updates".', required=True
    )

    relative_path = CharField(help_text="Path of file relative to url.", required=False)

    class Meta:
        fields = MultipleArtifactContentSerializer.Meta.fields + (
            "codename",
            "suite",
            "distribution",
            "relative_path",
        )
        model = ReleaseFile


class PackageIndexSerializer(MultipleArtifactContentSerializer):
    """
    A serializer for PackageIndex.
    """

    component = CharField(
        help_text="Component of the component - architecture combination.", required=True
    )

    architecture = CharField(
        help_text="Architecture of the component - architecture combination.", required=True
    )

    relative_path = CharField(help_text="Path of file relative to url.", required=False)

    release = DetailRelatedField(
        help_text="Release this index file belongs to.",
        many=False,
        queryset=ReleaseFile.objects.all(),
        view_name="deb-release-file-detail",
    )

    class Meta:
        fields = MultipleArtifactContentSerializer.Meta.fields + (
            "release",
            "component",
            "architecture",
            "relative_path",
        )
        model = PackageIndex


class SourceIndexSerializer(MultipleArtifactContentSerializer):
    """
    A serializer for SourceIndex.
    """

    component = CharField(help_text="Component this index file belongs to.", required=True)

    relative_path = CharField(help_text="Path of file relative to url.", required=False)

    release = DetailRelatedField(
        help_text="Release this index file belongs to.",
        many=False,
        queryset=ReleaseFile.objects.all(),
        view_name="deb-release-file-detail",
    )

    class Meta:
        fields = MultipleArtifactContentSerializer.Meta.fields + (
            "release",
            "component",
            "relative_path",
        )
        model = SourceIndex


class InstallerFileIndexSerializer(MultipleArtifactContentSerializer):
    """
    A serializer for InstallerFileIndex.
    """

    component = CharField(
        help_text="Component of the component - architecture combination.", required=True
    )

    architecture = CharField(
        help_text="Architecture of the component - architecture combination.", required=True
    )

    relative_path = CharField(
        help_text="Path of directory containing MD5SUMS and SHA256SUMS relative to url.",
        required=False,
    )

    release = DetailRelatedField(
        help_text="Release this index file belongs to.",
        many=False,
        queryset=ReleaseFile.objects.all(),
        view_name="deb-release-file-detail",
    )

    class Meta:
        fields = MultipleArtifactContentSerializer.Meta.fields + (
            "release",
            "component",
            "architecture",
            "relative_path",
        )
        model = InstallerFileIndex


class BasePackage822Serializer(SingleArtifactContentSerializer):
    """
    A Serializer for abstract BasePackage used for conversion from 822 format.
    """

    TRANSLATION_DICT = {
        "package": "Package",
        "source": "Source",
        "version": "Version",
        "architecture": "Architecture",
        "section": "Section",
        "priority": "Priority",
        "origin": "Origin",
        "tag": "Tag",
        "bugs": "Bugs",
        "essential": "Essential",
        "build_essential": "Build-Essential",
        "installed_size": "Installed-Size",
        "maintainer": "Maintainer",
        "original_maintainer": "Original-Maintainer",
        "description": "Description",
        "description_md5": "Description-md5",
        "homepage": "Homepage",
        "built_using": "Built-Using",
        "auto_built_package": "Auto_Built_Package",
        "multi_arch": "Multi-Arch",
        "breaks": "Breaks",
        "conflicts": "Conflicts",
        "depends": "Depends",
        "recommends": "Recommends",
        "suggests": "Suggests",
        "enhances": "Enhances",
        "pre_depends": "Pre-Depends",
        "provides": "Provides",
        "replaces": "Replaces",
    }

    package = CharField()
    source = CharField(required=False)
    version = CharField()
    architecture = CharField()
    section = CharField(required=False)
    priority = CharField(required=False)
    origin = CharField(required=False)
    tag = CharField(required=False)
    bugs = CharField(required=False)
    essential = YesNoField(required=False)
    build_essential = YesNoField(required=False)
    installed_size = CharField(required=False)
    maintainer = CharField()
    original_maintainer = CharField(required=False)
    description = CharField()
    description_md5 = CharField(required=False)
    homepage = CharField(required=False)
    built_using = CharField(required=False)
    auto_built_package = CharField(required=False)
    multi_arch = CharField(required=False)
    breaks = CharField(required=False)
    conflicts = CharField(required=False)
    depends = CharField(required=False)
    recommends = CharField(required=False)
    suggests = CharField(required=False)
    enhances = CharField(required=False)
    pre_depends = CharField(required=False)
    provides = CharField(required=False)
    replaces = CharField(required=False)

    def __init__(self, *args, **kwargs):
        """Initializer for BasePackage822Serializer."""
        super().__init__(*args, **kwargs)
        self.fields.pop("artifact")
        if "relative_path" in self.fields:
            self.fields["relative_path"].required = False

    @classmethod
    def from822(cls, data, **kwargs):
        """
        Translate deb822.Package to a dictionary for class instatiation.
        """
        return cls(
            data={k: data[v] for k, v in cls.TRANSLATION_DICT.items() if v in data}, **kwargs
        )

    def to822(self, component=""):
        """Create deb822.Package object from model."""
        ret = deb822.Packages()

        for k, v in self.TRANSLATION_DICT.items():
            value = self.data.get(k)
            if value is not None:
                ret[v] = value

        try:
            artifact = self.instance._artifacts.get()
            if artifact.md5:
                ret["MD5sum"] = artifact.md5
            if artifact.sha1:
                ret["SHA1"] = artifact.sha1
            ret["SHA256"] = artifact.sha256
        except Artifact.DoesNotExist:
            artifact = RemoteArtifact.objects.filter(sha256=self.instance.sha256).first()
            if artifact.md5:
                ret["MD5sum"] = artifact.md5
            if artifact.sha1:
                ret["SHA1"] = artifact.sha1
            ret["SHA256"] = artifact.sha256

        ret["Filename"] = self.instance.filename(component)

        return ret

    class Meta(SingleArtifactContentSerializer.Meta):
        fields = SingleArtifactContentSerializer.Meta.fields + (
            "package",
            "source",
            "version",
            "architecture",
            "section",
            "priority",
            "origin",
            "tag",
            "bugs",
            "essential",
            "build_essential",
            "installed_size",
            "maintainer",
            "original_maintainer",
            "description",
            "description_md5",
            "homepage",
            "built_using",
            "auto_built_package",
            "multi_arch",
            "breaks",
            "conflicts",
            "depends",
            "recommends",
            "suggests",
            "enhances",
            "pre_depends",
            "provides",
            "replaces",
        )
        model = BasePackage


class Package822Serializer(BasePackage822Serializer):
    """
    A Serializer for Package used for conversion from 822 format.
    """

    class Meta(BasePackage822Serializer.Meta):
        model = Package


class InstallerPackage822Serializer(BasePackage822Serializer):
    """
    A Serializer for InstallerPackage used for conversion from 822 format.
    """

    class Meta(BasePackage822Serializer.Meta):
        model = InstallerPackage


class BasePackageSerializer(SingleArtifactContentUploadSerializer, ContentChecksumSerializer):
    """
    A Serializer for abstract BasePackage.
    """

    package = CharField(read_only=True)
    source = CharField(read_only=True)
    version = CharField(read_only=True)
    architecture = CharField(read_only=True)
    section = CharField(read_only=True)
    priority = CharField(read_only=True)
    origin = CharField(read_only=True)
    tag = CharField(read_only=True)
    bugs = CharField(read_only=True)
    essential = YesNoField(read_only=True)
    build_essential = YesNoField(read_only=True)
    installed_size = CharField(read_only=True)
    maintainer = CharField(read_only=True)
    original_maintainer = CharField(read_only=True)
    description = CharField(read_only=True)
    description_md5 = CharField(read_only=True)
    homepage = CharField(read_only=True)
    built_using = CharField(read_only=True)
    auto_built_package = CharField(read_only=True)
    multi_arch = CharField(read_only=True)
    breaks = CharField(read_only=True)
    conflicts = CharField(read_only=True)
    depends = CharField(read_only=True)
    recommends = CharField(read_only=True)
    suggests = CharField(read_only=True)
    enhances = CharField(read_only=True)
    pre_depends = CharField(read_only=True)
    provides = CharField(read_only=True)
    replaces = CharField(read_only=True)

    def __init__(self, *args, **kwargs):
        """Initializer for BasePackageSerializer."""
        super().__init__(*args, **kwargs)
        if "relative_path" in self.fields:
            self.fields["relative_path"].required = False

    def deferred_validate(self, data):
        """Validate that the artifact is a package and extract it's values."""
        data = super().deferred_validate(data)

        try:
            package_paragraph = debfile.DebFile(fileobj=data["artifact"].file).debcontrol()
        except Exception:  # TODO: Be more specific
            raise ValidationError(_("Unable to read Deb Package"))

        from822_serializer = self.Meta.from822_serializer.from822(data=package_paragraph)
        from822_serializer.is_valid(raise_exception=True)
        package_data = from822_serializer.validated_data
        data.update(package_data)
        data["sha256"] = data["artifact"].sha256

        if "relative_path" not in data:
            data["relative_path"] = self.Meta.model(**package_data).filename()
        elif not os.path.basename(data["relative_path"]) == "{}.{}".format(
            self.Meta.model(**package_data).name, self.Meta.model.SUFFIX
        ):
            raise ValidationError(_("Invalid relative_path provided, filename does not match."))

        content = self.Meta.model.objects.filter(
            sha256=data["sha256"], relative_path=data["relative_path"]
        )
        if content.exists():
            raise ValidationError(
                _(
                    "There is already a deb package with relative path '{path}' and sha256 "
                    "'{sha256}'."
                ).format(path=data["relative_path"], sha256=data["sha256"])
            )

        return data

    class Meta(SingleArtifactContentUploadSerializer.Meta):
        fields = (
            SingleArtifactContentUploadSerializer.Meta.fields
            + ContentChecksumSerializer.Meta.fields
            + (
                "package",
                "source",
                "version",
                "architecture",
                "section",
                "priority",
                "origin",
                "tag",
                "bugs",
                "essential",
                "build_essential",
                "installed_size",
                "maintainer",
                "original_maintainer",
                "description",
                "description_md5",
                "homepage",
                "built_using",
                "auto_built_package",
                "multi_arch",
                "breaks",
                "conflicts",
                "depends",
                "recommends",
                "suggests",
                "enhances",
                "pre_depends",
                "provides",
                "replaces",
            )
        )
        model = BasePackage


class PackageSerializer(BasePackageSerializer):
    """
    A Serializer for Package.
    """

    def deferred_validate(self, data):
        """Validate for 'normal' Package (not installer)."""
        data = super().deferred_validate(data)

        if data.get("section") == "debian-installer":
            raise ValidationError(_("Not a valid Deb Package"))

        return data

    class Meta(BasePackageSerializer.Meta):
        model = Package
        from822_serializer = Package822Serializer


class InstallerPackageSerializer(BasePackageSerializer):
    """
    A Serializer for InstallerPackage.
    """

    def deferred_validate(self, data):
        """Validate for InstallerPackage."""
        data = super().deferred_validate(data)

        if data.get("section") != "debian-installer":
            raise ValidationError(_("Not a valid uDeb Package"))

        return data

    class Meta(BasePackageSerializer.Meta):
        model = InstallerPackage
        from822_serializer = InstallerPackage822Serializer


class ReleaseSerializer(NoArtifactContentSerializer):
    """
    A Serializer for Release.
    """

    codename = CharField()
    suite = CharField()
    distribution = CharField()

    class Meta(NoArtifactContentSerializer.Meta):
        model = Release
        fields = NoArtifactContentSerializer.Meta.fields + ("codename", "suite", "distribution")


class ReleaseArchitectureSerializer(NoArtifactContentSerializer):
    """
    A Serializer for ReleaseArchitecture.
    """

    architecture = CharField(help_text="Name of the architecture.")
    release = DetailRelatedField(
        help_text="Release this architecture is contained in.",
        many=False,
        queryset=Release.objects.all(),
        view_name="deb-release-detail",
    )

    class Meta(NoArtifactContentSerializer.Meta):
        model = ReleaseArchitecture
        fields = NoArtifactContentSerializer.Meta.fields + ("architecture", "release")


class ReleaseComponentSerializer(NoArtifactContentSerializer):
    """
    A Serializer for ReleaseComponent.
    """

    component = CharField(help_text="Name of the component.")
    release = DetailRelatedField(
        help_text="Release this component is contained in.",
        many=False,
        queryset=Release.objects.all(),
        view_name="deb-release-detail",
    )

    class Meta(NoArtifactContentSerializer.Meta):
        model = ReleaseComponent
        fields = NoArtifactContentSerializer.Meta.fields + ("component", "release")


class PackageReleaseComponentSerializer(NoArtifactContentSerializer):
    """
    A Serializer for PackageReleaseComponent.
    """

    package = DetailRelatedField(
        help_text="Package that is contained in release_comonent.",
        many=False,
        queryset=ReleaseComponent.objects.all(),
        view_name="deb-release_component-detail",
    )
    release_component = DetailRelatedField(
        help_text="ReleaseComponent this package is contained in.",
        many=False,
        queryset=ReleaseComponent.objects.all(),
        view_name="deb-release_component-detail",
    )

    class Meta(NoArtifactContentSerializer.Meta):
        model = PackageReleaseComponent
        fields = NoArtifactContentSerializer.Meta.fields + ("package", "release_component")


class BaseSourceSerializer(SingleArtifactContentUploadSerializer, ContentChecksumSerializer):
    """
    A Serializer for Source.
    """

    name = CharField(
        help_text=_("Filename to use."),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        """Initializer for SourceFileSerializer."""
        super().__init__(*args, **kwargs)
        if "relative_path" in self.fields:
            self.fields["relative_path"].required = False

    def deferred_validate(self, data):
        """Validate the Source data."""
        data = super().deferred_validate(data)

        data["size"] = data["artifact"].size
        data["md5sum"] = data["artifact"].md5
        data["sha1"] = data["artifact"].sha1
        data["sha256"] = data["artifact"].sha256
        data["sha512"] = data["artifact"].sha512

        return data

    class Meta:
        model = BaseSource
        fields = (
            SingleArtifactContentUploadSerializer.Meta.fields
            + ContentChecksumSerializer.Meta.fields
        ) + (
            "md5sum",
            "size",
            "name",
        )


class SourceFileSerializer(BaseSourceSerializer):
    """
    A Serializer for SourceFile.
    """

    def deferred_validate(self, data):
        """Validate the Source data."""
        data = super().deferred_validate(data)

        if "relative_path" not in data:
            name = data["name"]
            if name.count("_") < 1:
                raise ValidationError(
                    _("Source file names must have an underscore between the name and version.")
                )
            source_data = {k: data[k] for k, v in data.items() if k != "artifact"}
            data["relative_path"] = self.Meta.model(**source_data).derived_path()
        elif not os.path.basename(data["relative_path"]) == data["name"]:
            raise ValidationError(
                _("Invalid name '{}' and  relative_path filename '{}' do not match.").format(
                    data["name"], os.path.basename(data["relative_path"])
                )
            )

        content = SourceFile.objects.filter(
            sha256=data["sha256"], relative_path=data["relative_path"]
        )
        if content.exists():
            raise ValidationError(
                _(
                    "There is already a source file with relative path '{path}' and sha256 "
                    "'{sha256}'."
                ).format(path=data["relative_path"], sha256=data["sha256"])
            )

        return data

    class Meta:
        model = SourceFile
        fields = BaseSourceSerializer.Meta.fields


class SourceMd5sumSerializer(SingleArtifactContentSerializer):
    """
    A Serializer for SourceFileMd5sum.
    """

    class Meta:
        model = SourceFile
        fields = (
            "md5sum",
            "size",
            "name",
        )


class SourceSha1Serializer(SingleArtifactContentSerializer):
    """
    A Serializer for SourceFileSha1.
    """

    class Meta:
        model = SourceFile
        fields = (
            "sha1",
            "size",
            "name",
        )


class SourceSha256Serializer(SingleArtifactContentSerializer):
    """
    A Serializer for SourceFileSha256.
    """

    class Meta:
        model = SourceFile
        fields = (
            "sha256",
            "size",
            "name",
        )


class SourceSha512Serializer(SingleArtifactContentSerializer):
    """
    A Serializer for SourceFileSha512.
    """

    class Meta:
        model = SourceFile
        fields = (
            "sha512",
            "size",
            "name",
        )


class SourceReleaseComponentSerializer(NoArtifactContentSerializer):
    """
    A Serializer for SourceReleaseComponent.
    """

    source = DetailRelatedField(
        help_text="Source that is contained in release_comonent.",
        many=False,
        queryset=ReleaseComponent.objects.all(),
        view_name="deb-source_component-detail",
    )
    release_component = DetailRelatedField(
        help_text="ReleaseComponent this source is contained in.",
        many=False,
        queryset=ReleaseComponent.objects.all(),
        view_name="deb-release_component-detail",
    )

    class Meta(NoArtifactContentSerializer.Meta):
        model = SourceReleaseComponent
        fields = NoArtifactContentSerializer.Meta.fields + ("source", "release_component")


class DscFile822Serializer(NoArtifactContentSerializer):
    """
    A Serializer for DscFile used for conversion to/from 822 format.
    """

    TRANSLATION_DICT = {
        "format": "Format",
        "source": "Source",
        "binary": "Binary",
        "architecture": "Architecture",
        "version": "Version",
        "maintainer": "Maintainer",
        "uploaders": "Uploaders",
        "homepage": "Homepage",
        "vcs_browser": "Vcs-Browser",
        "vcs_arch": "Vcs-Arch",
        "vcs_bzr": "Vcs-Bzr",
        "vcs_cvs": "Vcs-Cvs",
        "vcs_darcs": "Vcs-Darcs",
        "vcs_git": "Vcs-Git",
        "vcs_hg": "Vcs-Hg",
        "vcs_mtn": "Vcs-Mtn",
        "vcs_snv": "Vcs-Svn",
        "testsuite": "Testsuite",
        "dgit": "Dgit",
        "standards_version": "Standards-Version",
        "build_depends": "Build-Depends",
        "build_depends_indep": "Build-Depends-Indep",
        "build_depends_arch": "Build-Depends-Arch",
        "build_conflicts": "Build-Conflicts",
        "build_conflicts_indep": "Build-Conflicts-Indep",
        "build_conflicts_arch": "Build-Conflicts-Arch",
        "package_list": "Package-List",
        "checksums_sha1": "Checksums-Sha1",
        "checksums_sha256": "Checksums-Sha256",
        "checksums_sha512": "Checksums-Sha512",
        "files": "Files",
    }

    format = CharField()
    source = CharField()
    binary = CharField(required=False)
    architecture = CharField(required=False)
    version = CharField()
    maintainer = CharField()
    uploaders = CharField(required=False)
    homepage = CharField(required=False)
    vcs_browser = CharField(required=False)
    vcs_arch = CharField(required=False)
    vcs_bzr = CharField(required=False)
    vcs_cvs = CharField(required=False)
    vcs_darcs = CharField(required=False)
    vcs_git = CharField(required=False)
    vcs_hg = CharField(required=False)
    vcs_mtn = CharField(required=False)
    vcs_snv = CharField(required=False)
    testsuite = CharField(required=False)
    dgit = CharField(required=False)
    standards_version = CharField()
    build_depends = CharField(required=False)
    build_depends_indep = CharField(required=False)
    build_depends_arch = CharField(required=False)
    build_conflicts = CharField(required=False)
    build_conflicts_indep = CharField(required=False)
    build_conflicts_arch = CharField(required=False)
    package_list = CharField(required=False)
    checksums_sha1 = SourceSha1Serializer(many=True, required=False)
    checksums_sha256 = SourceSha256Serializer(many=True)
    checksums_sha512 = SourceSha512Serializer(many=True, required=False)
    files = SourceMd5sumSerializer(many=True)

    @classmethod
    def from822(cls, data, **kwargs):
        """
        Translate deb822.Dsc to a dictionary for class instatiation.
        """
        return cls(
            data={k: data[v] for k, v in cls.TRANSLATION_DICT.items() if v in data}, **kwargs
        )

    def to822(self, component="", paragraph=False):
        """Create deb822.Dsc object from model."""
        ret = deb822.Dsc()

        for k, v in self.TRANSLATION_DICT.items():
            value = self.data.get(k)
            if value is not None:
                ret[v] = value

        # DB storage strips leading newline-space from the first 'Package-List' entry, restore it.
        if "Package-List" in ret and ret["Package-List"][0] != "\n":
            ret["Package-List"] = "\n {}".format(ret["Package-List"])

        if paragraph:
            """
            Used as a paragraph in the Sources indices file. Use 'Package' instead of 'Source'
            and include 'Directory'. Currently we skip the optional 'Priority' and 'Section'.
            """
            ret["Package"] = ret.pop("Source")
            ret["Directory"] = os.path.dirname(self.instance.derived_path(component))

        return ret

    class Meta:
        fields = (
            "format",
            "source",
            "binary",
            "architecture",
            "version",
            "maintainer",
            "uploaders",
            "homepage",
            "vcs_browser",
            "vcs_arch",
            "vcs_bzr",
            "vcs_cvs",
            "vcs_darcs",
            "vcs_git",
            "vcs_hg",
            "vcs_mtn",
            "vcs_snv",
            "testsuite",
            "dgit",
            "standards_version",
            "build_depends",
            "build_depends_indep",
            "build_depends_arch",
            "build_conflicts",
            "build_conflicts_indep",
            "build_conflicts_arch",
            "package_list",
            "checksums_sha1",
            "checksums_sha256",
            "checksums_sha512",
            "files",
        )
        model = DscFile


class DscFileSerializer(BaseSourceSerializer):
    """
    A Serializer for DscFile.
    """

    format = CharField(read_only=True)
    source = CharField(read_only=True)
    binary = CharField(read_only=True)
    architecture = CharField(read_only=True)
    version = CharField(read_only=True)
    maintainer = CharField(read_only=True)
    uploaders = CharField(read_only=True)
    homepage = CharField(read_only=True)
    vcs_browser = CharField(read_only=True)
    vcs_arch = CharField(read_only=True)
    vcs_bzr = CharField(read_only=True)
    vcs_cvs = CharField(read_only=True)
    vcs_darcs = CharField(read_only=True)
    vcs_git = CharField(read_only=True)
    vcs_hg = CharField(read_only=True)
    vcs_mtn = CharField(read_only=True)
    vcs_snv = CharField(read_only=True)
    testsuite = CharField(read_only=True)
    dgit = CharField(read_only=True)
    standards_version = CharField(read_only=True)
    build_depends = CharField(read_only=True)
    build_depends_indep = CharField(read_only=True)
    build_depends_arch = CharField(read_only=True)
    build_conflicts = CharField(read_only=True)
    build_conflicts_indep = CharField(read_only=True)
    build_conflicts_arch = CharField(read_only=True)
    package_list = CharField(read_only=True)
    checksums_sha1 = SourceSha1Serializer(many=True, read_only=True)
    checksums_sha256 = SourceSha256Serializer(many=True, read_only=True)
    checksums_sha512 = SourceSha512Serializer(many=True, read_only=True)
    files = SourceMd5sumSerializer(many=True, read_only=True)

    def __init__(self, *args, **kwargs):
        """Initializer for DscFileSerializer."""
        super().__init__(*args, **kwargs)
        if "relative_path" in self.fields:
            self.fields["relative_path"].required = False
        self.fields["name"].required = False

    def create(self, validated_data):
        # Required
        files = validated_data.pop("files")
        checksums_sha256s = validated_data.pop("checksums_sha256")
        # Optional
        checksums_sha1s = None
        checksums_sha512s = None
        if "checksums_sha1" in validated_data:
            checksums_sha1s = validated_data.pop("checksums_sha1")
        if "checksums_sha512" in validated_data:
            checksums_sha512s = validated_data.pop("checksums_sha512")

        dsc_file = super().create(validated_data)

        # Required
        dsc_file.dsc_files = dsc_file
        for source in files:
            obj = SourceFile.objects.filter(md5sum=source["md5sum"], name=source["name"]).first()
            obj.dsc_files = dsc_file
            obj.save()
        dsc_file.dsc_checksums_sha256 = dsc_file
        for source in checksums_sha256s:
            obj = SourceFile.objects.filter(sha256=source["sha256"], name=source["name"]).first()
            obj.dsc_checksums_sha256 = dsc_file
            obj.save()
        # Optional
        if checksums_sha1s is not None:
            dsc_file.dsc_checksums_sha1 = dsc_file
            for source in checksums_sha1s:
                obj = SourceFile.objects.filter(sha1=source["sha1"], name=source["name"]).first()
                obj.dsc_checksums_sha1 = dsc_file
                obj.save()
        if checksums_sha512s is not None:
            dsc_file.dsc_checksums_sha512 = dsc_file
            for source in checksums_sha512s:
                obj = SourceFile.objects.filter(
                    sha512=source["sha512"], name=source["name"]
                ).first()
                obj.dsc_checksums_sha512 = dsc_file
                obj.save()
        dsc_file.save()

        return dsc_file

    def deferred_validate(self, data):
        """Validate that the artifact is a source control file and extract it's values."""
        data = super().deferred_validate(data)

        try:
            source_paragraph = deb822.Dsc(data["artifact"].file)
        except Exception:  # TODO: Be more specific
            raise ValidationError(_("Unable to read Source Control File"))

        from822_serializer = DscFile822Serializer.from822(data=source_paragraph)
        from822_serializer.is_valid(raise_exception=True)
        source_data = from822_serializer.validated_data
        data.update(source_data)

        """
        Really no leeway here. 'name' and 'filename' must match contents of DSC
        only the path component of relative_path can be adjusted (though shouldn't)
        """
        if "name" not in data:
            data["name"] = self.Meta.model(**source_data).derived_name()
        elif not data["name"] == self.Meta.model(**source_data).derived_name():
            raise ValidationError(
                _("Invalid name provided '{}', derived_name '{}' do not match.").format(
                    data["name"], self.Meta.model(**source_data).derived_name()
                )
            )
        if "relative_path" not in data:
            data["relative_path"] = self.Meta.model(**source_data).filename()
        elif (
            not os.path.basename(data["relative_path"])
            == self.Meta.model(**source_data).derived_name()
        ):
            raise ValidationError(
                _("Invalid relative_path provided '{}', filename '{}' do not match.").format(
                    data["relative_path"], self.Meta.model(**source_data).derived_name()
                )
            )

        content = self.Meta.model.objects.filter(
            sha256=data["sha256"], relative_path=data["relative_path"]
        )
        if content.exists():
            raise ValidationError(
                _(
                    "There is already a dsc file with relative path '{path}' and sha256 "
                    "'{sha256}'."
                ).format(path=data["relative_path"], sha256=data["sha256"])
            )

        for source in data["checksums_sha256"]:
            content = SourceFile.objects.filter(sha256=source["sha256"], name=source["name"])
            if not content.exists():
                raise ValidationError(
                    _(
                        "A source_file is listed in the dsc file but is not yet available '{name}' "
                        "and sha256 '{sha256}'."
                    ).format(name=source["name"], sha256=source["sha256"])
                )

        return data

    class Meta:
        fields = BaseSourceSerializer.Meta.fields + (
            "format",
            "source",
            "binary",
            "architecture",
            "version",
            "maintainer",
            "uploaders",
            "homepage",
            "vcs_browser",
            "vcs_arch",
            "vcs_bzr",
            "vcs_cvs",
            "vcs_darcs",
            "vcs_git",
            "vcs_hg",
            "vcs_mtn",
            "vcs_snv",
            "testsuite",
            "dgit",
            "standards_version",
            "build_depends",
            "build_depends_indep",
            "build_depends_arch",
            "build_conflicts",
            "build_conflicts_indep",
            "build_conflicts_arch",
            "package_list",
            "checksums_sha1",
            "checksums_sha256",
            "checksums_sha512",
            "files",
        )
        model = DscFile


class DscFileReleaseComponentSerializer(NoArtifactContentSerializer):
    """
    A Serializer for DscFileReleaseComponent.
    """

    dsc_file = DetailRelatedField(
        help_text="Dsc file that is contained in release_comonent.",
        many=False,
        queryset=ReleaseComponent.objects.all(),
        view_name="deb-dsc_file_component-detail",
    )
    release_component = DetailRelatedField(
        help_text="ReleaseComponent this Dsc file is contained in.",
        many=False,
        queryset=ReleaseComponent.objects.all(),
        view_name="deb-release_component-detail",
    )

    class Meta(NoArtifactContentSerializer.Meta):
        model = DscFileReleaseComponent
        fields = NoArtifactContentSerializer.Meta.fields + ("dsc_file", "release_component")
