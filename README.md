Debian Support
==============

Pulp plugin to handle Debian packages.

**WARNING:** There may be bugs.

### Requirements

Admin extensions do not need any additional tools.

Server extensions need:
* python-debian: https://pypi.python.org/pypi/python-debian
* python-debpkgr: https://pypi.python.org/pypi/python-debpkgr


### Installation

#### Installation via package manager

The debian plugin is now available as RPMs for RHEL7, Fedora 24 and Fedora 25.
To install the plugin to an existing pulp server, install the following
packages:

```
$ sudo dnf install \
  pulp-deb-plugins \
  python-debian \
  python-pulp-deb-common \
  python2-debpkgr
```

On a machine with the `pulp-admin` client, install the admin client extensions:

```
$ sudo dnf install pulp-deb-admin-extensions
```

To enable the plugin, you will need to stop pulp services and migrate the
database, and then restart the services.

To do this, on the pulp server run:

```
$ sudo systemctl stop \
  httpd \
  pulp_celerybeat \
  pulp_resource_manager \
  pulp_streamer \
  pulp_workers \
  qpidd \
  goferd

$ sudo -u apache pulp-manage-db

... output omitted ...

$ sudo systemctl start
  httpd \
  pulp_celerybeat \
  pulp_resource_manager \
  pulp_streamer \
  pulp_workers \
  qpidd \
  goferd
```

> The pulp_streamer and goferd services should be omitted if those services are
> not installed.

On a machine with the pulp-admin client configured to control your pulp server,
and with the `pulp-deb-admin-extensions` package installed, you should now be
able to create debian repositories.

```
$ pulp-admin deb repo create --repo-id now-i-serve-debian-packages
```

#### Build your own RPMs
Alternatively, you can build the RPMs from spec file and then install with rpm.
If you do this, you must also build python-debian and python-debpkgr as rpm packages and install.

### Representing Debian Dependency Relationships

This plugin uses `deb822.PkgRelation` to parse Debian dependency fields.

We currently support `breaks`, `conflicts`, `depends`, `enhances`,
`pre_depends`, `provides`, `recommends`, `replaces`, `suggests`.

The representation of a Debian relationship is following, when possible,
the conventions used by `pulp_rpm`:

* The representation is a list of sub-items, with an implicit conjunction
  (`AND`) for the sub-items. In other words, all the sub-items have to
  evaluate to True in order for the relationship to be satisfied.
* Simple (single package) items are dictionaries with a `name` field. They may
  contain additional fields `version`, `flag`, `arch`, `restrictions`.
* Versioned dependencies will have a `version` field to describe the desired
  target version, and the `flag` field will denote the operator for comparing
  versions. Where the operators in a Debian representation are one of "<<",
  "<=", "=", ">=", ">>", `flag` will be `LT`, `LE`, `EQ`, `GE`, `GT`
  respectively.
* `arch` is a list of architecture strings. Negation is represented with a
  leading exclamation mark.
* `restrictions`, if present, is a list of one or more lists of strings.
  Just like with architectures, negation is represented with a leading
  exclamation mark.

In addition, Debian supports disjunction. Where simple package dependencies
are dictionaries, disjunction (`OR`) is a list of simple package dependencies.

Here are examples of dependencies and their representation in Pulp:

* `'emacs | emacsen, make, debianutils (>= 1.7)'`:
```json
 [
     [{"name": "emacs"}, {"name": "emacsen"}],
     {"name": "make"},
     {"name": "debianutils", "version": "1.7", "flag": "GE"}
 ]
```
* `'tcl8.4-dev [amd64], procps [!hurd-i386]'`:
```json
 [
    {"name": "tcl8.4-dev", "arch": ["amd64"]},
    {"name": "procps", "arch": ["!hurd-i386"]}
 ]
```
* `'texlive <stage1 !cross> <stage2>'`:
```json
 [
     {"name": "texlive", "restrictions": [["stage1", "!cross"], ["stage2"]]}
 ]
```

### Signing support

To enable repository metadata signing, you will need to supply a configuration
file `/etc/pulp/server/plugins.conf.d/deb_distributor.json`, containing
something like:

```json
{
  "gpg_cmd": "/usr/local/bin/sign.sh",
  "gpg_key_id": "0452AB3D"
}

```

The supplied sign command has to be an executable accessible to the Apache
user. It will be supplied the path to a `Release` file to be signed, and is
expected to produce a file named `Release.gpg` in the same directory as the
`Release` file. Additionally, the sign command will be passed the following
environment variables:
* `GPG_CMD`
* `GPG_KEY_ID` (if specified in the configuration file)
* `GPG_REPOSITORY_NAME`
* `GPG_DIST`

The sign command may decide on a key ID to use, based on the repository name
or the dist that is being signed.

A minimal sign command using GPG could be:

```Shell
#!/bin/bash -e

KEYID=${GPG_KEY_ID:-45BA0816}

gpg --homedir /var/lib/pulp/gpg-home \
    --detach-sign --default-key $KEYID \
    --armor --output ${1}.gpg ${1}
```

You could import your password-less GPG keys like this:

```Shell
mkdir /var/lib/pulp/gpg-home
chmod 0700 /var/lib/pulp/gpg-home
gpg --homedir /var/lib/pulp/gpg-home --import <path-to-secret-keys>
chown -R apache.apache /var/lib/pulp/gpg-home
```

**WARNING!** The example, as presented above, is not suitable for production
use. Unprotected GPG keys may be easily stolen. You may want to consider
more secure alternatives for your signing needs, like a dedicated server,
potentially with a
[Hardware Security Module](https://en.wikipedia.org/wiki/Hardware_security_module).
