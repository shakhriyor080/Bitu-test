from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0004_directionsubjectconfig'),
    ]

    operations = [
        migrations.AlterField(
            model_name='question',
            name='direction',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='questions', to='accounts.direction', verbose_name="Yo'nalish"),
        ),
    ]
