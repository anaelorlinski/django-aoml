# -*- coding: utf-8 -*-


from django.db import models, migrations
import emencia.django.newsletter.models
import datetime
import tagging.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255, verbose_name='title')),
                ('file_attachment', models.FileField(upload_to=emencia.django.newsletter.models.get_newsletter_storage_path, max_length=255, verbose_name='file to attach')),
            ],
            options={
                'verbose_name': 'attachment',
                'verbose_name_plural': 'attachments',
            },
        ),
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(unique=True, max_length=254, verbose_name='email')),
                ('first_name', models.CharField(max_length=50, verbose_name='first name', blank=True)),
                ('last_name', models.CharField(max_length=50, verbose_name='last name', blank=True)),
                ('subscriber', models.BooleanField(default=True, verbose_name='subscriber')),
                ('valid', models.BooleanField(default=True, verbose_name='valid email')),
                ('tester', models.BooleanField(default=False, verbose_name='contact tester')),
                ('tags', tagging.fields.TagField(max_length=255, verbose_name='tags', blank=True)),
                ('object_id', models.PositiveIntegerField(null=True, blank=True)),
                ('creation_date', models.DateTimeField(auto_now_add=True, verbose_name='creation date')),
                ('modification_date', models.DateTimeField(auto_now=True, verbose_name='modification date')),
                ('content_type', models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True)),
            ],
            options={
                'ordering': ('creation_date',),
                'verbose_name': 'contact',
                'verbose_name_plural': 'contacts',
            },
        ),
        migrations.CreateModel(
            name='ContactMailingStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.IntegerField(verbose_name='status', choices=[(-1, 'sent in test'), (0, 'sent'), (1, 'error'), (2, 'invalid email'), (4, 'opened'), (5, 'opened on site'), (6, 'link opened'), (7, 'unsubscription')])),
                ('creation_date', models.DateTimeField(auto_now_add=True, verbose_name='creation date')),
                ('contact', models.ForeignKey(verbose_name='contact', to='newsletter.Contact')),
            ],
            options={
                'ordering': ('-creation_date',),
                'verbose_name': 'contact mailing status',
                'verbose_name_plural': 'contact mailing statuses',
            },
        ),
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255, verbose_name='title')),
                ('url', models.CharField(max_length=255, verbose_name='url')),
                ('creation_date', models.DateTimeField(auto_now_add=True, verbose_name='creation date')),
            ],
            options={
                'ordering': ('-creation_date',),
                'verbose_name': 'link',
                'verbose_name_plural': 'links',
            },
        ),
        migrations.CreateModel(
            name='MailingList',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('description', models.TextField(verbose_name='description', blank=True)),
                ('creation_date', models.DateTimeField(auto_now_add=True, verbose_name='creation date')),
                ('modification_date', models.DateTimeField(auto_now=True, verbose_name='modification date')),
                ('subscribers', models.ManyToManyField(related_name='mailinglist_subscriber', verbose_name='subscribers', to='newsletter.Contact')),
                ('unsubscribers', models.ManyToManyField(related_name='mailinglist_unsubscriber', verbose_name='unsubscribers', to='newsletter.Contact', blank=True)),
            ],
            options={
                'ordering': ('-creation_date',),
                'verbose_name': 'mailing list',
                'verbose_name_plural': 'mailing lists',
            },
        ),
        migrations.CreateModel(
            name='Newsletter',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text='You can use the "{{ UNIQUE_KEY }}" variable for unique identifier within the newsletter\'s title.', max_length=255, verbose_name='title')),
                ('content', models.TextField(default='<body>\n<!-- Edit your newsletter here -->\n</body>', help_text='Or paste an URL.', verbose_name='content')),
                ('header_sender', models.CharField(default=b'Emencia Newsletter<noreply@emencia.com>', max_length=255, verbose_name='sender')),
                ('header_reply', models.CharField(default=b'Emencia Newsletter<noreply@emencia.com>', max_length=255, verbose_name='reply to')),
                ('status', models.IntegerField(default=0, verbose_name='status', choices=[(0, 'draft'), (1, 'waiting sending'), (2, 'sending'), (4, 'sent'), (5, 'canceled')])),
                ('sending_date', models.DateTimeField(default=datetime.datetime.now, verbose_name='sending date')),
                ('slug', models.SlugField(help_text='Used for displaying the newsletter on the site.', unique=True)),
                ('creation_date', models.DateTimeField(auto_now_add=True, verbose_name='creation date')),
                ('modification_date', models.DateTimeField(auto_now=True, verbose_name='modification date')),
                ('mailing_list', models.ForeignKey(verbose_name='mailing list', to='newsletter.MailingList')),
            ],
            options={
                'ordering': ('-creation_date',),
                'verbose_name': 'newsletter',
                'verbose_name_plural': 'newsletters',
                'permissions': (('can_change_status', 'Can change status'),),
            },
        ),
        migrations.CreateModel(
            name='SMTPServer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('host', models.CharField(max_length=255, verbose_name='server host')),
                ('user', models.CharField(help_text='Leave it empty if the host is public.', max_length=128, verbose_name='server user', blank=True)),
                ('password', models.CharField(help_text='Leave it empty if the host is public.', max_length=128, verbose_name='server password', blank=True)),
                ('port', models.IntegerField(default=25, verbose_name='server port')),
                ('tls', models.BooleanField(verbose_name='server use TLS')),
                ('headers', models.TextField(help_text='key1: value1 key2: value2, splitted by return line.\nUseful for passing some tracking headers if your provider allows it.', verbose_name='custom headers', blank=True)),
                ('mails_hour', models.IntegerField(default=0, verbose_name='mails per hour')),
            ],
            options={
                'verbose_name': 'SMTP server',
                'verbose_name_plural': 'SMTP servers',
            },
        ),
        migrations.CreateModel(
            name='WorkGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('contacts', models.ManyToManyField(to='newsletter.Contact', verbose_name='contacts', blank=True)),
                ('group', models.ForeignKey(verbose_name='permissions group', to='auth.Group')),
                ('mailinglists', models.ManyToManyField(to='newsletter.MailingList', verbose_name='mailing lists', blank=True)),
                ('newsletters', models.ManyToManyField(to='newsletter.Newsletter', verbose_name='newsletters', blank=True)),
            ],
            options={
                'verbose_name': 'workgroup',
                'verbose_name_plural': 'workgroups',
            },
        ),
        migrations.AddField(
            model_name='newsletter',
            name='server',
            field=models.ForeignKey(default=1, verbose_name='smtp server', to='newsletter.SMTPServer'),
        ),
        migrations.AddField(
            model_name='newsletter',
            name='test_contacts',
            field=models.ManyToManyField(to='newsletter.Contact', verbose_name='test contacts', blank=True),
        ),
        migrations.AddField(
            model_name='contactmailingstatus',
            name='link',
            field=models.ForeignKey(verbose_name='link', blank=True, to='newsletter.Link', null=True),
        ),
        migrations.AddField(
            model_name='contactmailingstatus',
            name='newsletter',
            field=models.ForeignKey(verbose_name='newsletter', to='newsletter.Newsletter'),
        ),
        migrations.AddField(
            model_name='attachment',
            name='newsletter',
            field=models.ForeignKey(verbose_name='newsletter', to='newsletter.Newsletter'),
        ),
        migrations.AddField(
            model_name='smtpserver',
            name='ssl',
            field=models.BooleanField(default=True, verbose_name='server use SSL'),
        ),
    ]
