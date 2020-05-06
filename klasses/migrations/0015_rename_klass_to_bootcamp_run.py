# Generated by Django 2.2.10 on 2020-05-04 20:31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0001_bootcamp_application_models'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('klasses', '0014_no_max_len_application_stage'),
        ('mail', '0003_remove_mail_models'),
        ('ecommerce', '0003_rename_line_klass_id_to_klass_key'),
        ('cms', '0003_bootcamp_product_run_page'),
        ('jobma', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Klass',
            new_name='BootcampRun',
        ),
        migrations.AlterModelOptions(
            name='installment',
            options={'ordering': ['bootcamp_run', 'deadline']},
        ),
        migrations.RenameField(
            model_name='bootcamprun',
            old_name='klass_key',
            new_name='run_key',
        ),
        migrations.RenameField(
            model_name='installment',
            old_name='klass',
            new_name='bootcamp_run',
        ),
        migrations.RenameField(
            model_name='personalprice',
            old_name='klass',
            new_name='bootcamp_run',
        ),
        migrations.AlterField(
            model_name='personalprice',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='run_prices', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='bootcamprun',
            unique_together={('run_key', 'source')},
        ),
        migrations.AlterUniqueTogether(
            name='installment',
            unique_together={('bootcamp_run', 'deadline')},
        ),
        migrations.AlterUniqueTogether(
            name='personalprice',
            unique_together={('bootcamp_run', 'user')},
        ),
        migrations.AlterIndexTogether(
            name='installment',
            index_together={('bootcamp_run', 'deadline')},
        ),
    ]
