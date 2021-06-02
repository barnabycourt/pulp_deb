# Generated by Django 2.2.24 on 2021-06-17 23:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0063_repository_retained_versions'),
        ('deb', '0014_swap_distribution_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='BaseSource',
            fields=[
                ('content_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='deb_basesource', serialize=False, to='core.Content')),
                ('name', models.TextField()),
                ('relative_path', models.TextField()),
                ('size', models.BigIntegerField(null=True)),
                ('md5', models.CharField(max_length=32, null=True)),
                ('md5sum', models.CharField(max_length=32, null=True)),
                ('sha1', models.CharField(max_length=40, null=True)),
                ('sha256', models.CharField(max_length=64)),
                ('sha512', models.CharField(max_length=128, null=True)),
            ],
            options={
                'default_related_name': '%(app_label)s_%(model_name)s',
            },
            bases=('core.content',),
        ),
        migrations.CreateModel(
            name='DscFile',
            fields=[
                ('basesource_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='deb_dscfile', serialize=False, to='deb.BaseSource')),
                ('format', models.TextField()),
                ('source', models.TextField()),
                ('binary', models.TextField(null=True)),
                ('architecture', models.TextField(null=True)),
                ('version', models.TextField()),
                ('maintainer', models.TextField()),
                ('uploaders', models.TextField(null=True)),
                ('homepage', models.TextField(null=True)),
                ('vcs_browser', models.TextField(null=True)),
                ('vcs_arch', models.TextField(null=True)),
                ('vcs_bzr', models.TextField(null=True)),
                ('vcs_cvs', models.TextField(null=True)),
                ('vcs_darcs', models.TextField(null=True)),
                ('vcs_git', models.TextField(null=True)),
                ('vcs_hg', models.TextField(null=True)),
                ('vcs_mtn', models.TextField(null=True)),
                ('vcs_snv', models.TextField(null=True)),
                ('testsuite', models.TextField(null=True)),
                ('dgit', models.TextField(null=True)),
                ('standards_version', models.TextField()),
                ('build_depends', models.TextField(null=True)),
                ('build_depends_indep', models.TextField(null=True)),
                ('build_depends_arch', models.TextField(null=True)),
                ('build_conflicts', models.TextField(null=True)),
                ('build_conflicts_indep', models.TextField(null=True)),
                ('build_conflicts_arch', models.TextField(null=True)),
                ('package_list', models.TextField(null=True)),
            ],
            options={
                'default_related_name': '%(app_label)s_%(model_name)s',
            },
            bases=('deb.basesource',),
        ),
        migrations.CreateModel(
            name='SourceFile',
            fields=[
                ('basesource_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='deb_sourcefile', serialize=False, to='deb.BaseSource')),
            ],
            options={
                'default_related_name': '%(app_label)s_%(model_name)s',
            },
            bases=('deb.basesource',),
        ),
        migrations.CreateModel(
            name='SourceIndex',
            fields=[
                ('content_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='deb_sourceindex', serialize=False, to='core.Content')),
                ('component', models.CharField(max_length=255)),
                ('relative_path', models.TextField()),
                ('sha256', models.CharField(max_length=255)),
                ('release', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deb_sourceindex', to='deb.ReleaseFile')),
            ],
            options={
                'verbose_name_plural': 'SourceIndices',
                'default_related_name': '%(app_label)s_%(model_name)s',
                'unique_together': {('relative_path', 'sha256')},
            },
            bases=('core.content',),
        ),
        migrations.AddField(
            model_name='basesource',
            name='dsc_checksums_sha1',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='checksums_sha1', to='deb.DscFile'),
        ),
        migrations.AddField(
            model_name='basesource',
            name='dsc_checksums_sha256',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='checksums_sha256', to='deb.DscFile'),
        ),
        migrations.AddField(
            model_name='basesource',
            name='dsc_checksums_sha512',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='checksums_sha512', to='deb.DscFile'),
        ),
        migrations.AddField(
            model_name='basesource',
            name='dsc_files',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='files', to='deb.DscFile'),
        ),
        migrations.CreateModel(
            name='SourceReleaseComponent',
            fields=[
                ('content_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='deb_sourcereleasecomponent', serialize=False, to='core.Content')),
                ('release_component', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deb_sourcereleasecomponent', to='deb.ReleaseComponent')),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deb_sourcereleasecomponent', to='deb.SourceFile')),
            ],
            options={
                'default_related_name': '%(app_label)s_%(model_name)s',
                'unique_together': {('source', 'release_component')},
            },
            bases=('core.content',),
        ),
        migrations.CreateModel(
            name='DscFileReleaseComponent',
            fields=[
                ('content_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='deb_dscfilereleasecomponent', serialize=False, to='core.Content')),
                ('release_component', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deb_dscfilereleasecomponent', to='deb.ReleaseComponent')),
                ('dsc_file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deb_dscfilereleasecomponent', to='deb.DscFile')),
            ],
            options={
                'default_related_name': '%(app_label)s_%(model_name)s',
                'unique_together': {('dsc_file', 'release_component')},
            },
            bases=('core.content',),
        ),
        migrations.AlterUniqueTogether(
            name='basesource',
            unique_together={('relative_path', 'sha256')},
        ),
    ]