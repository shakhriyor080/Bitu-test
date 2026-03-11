from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '__first__'),
        ('exams', '0003_question_subject'),
    ]

    operations = [
        migrations.CreateModel(
            name='DirectionSubjectConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_count', models.PositiveIntegerField(default=0, verbose_name='Savollar soni')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Tartib')),
                ('is_active', models.BooleanField(default=True, verbose_name='Aktiv')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('direction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exam_configs', to='accounts.direction')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='direction_configs', to='accounts.subject')),
            ],
            options={
                'verbose_name': "Yo'nalish fan sozlamasi",
                'verbose_name_plural': "Yo'nalish fan sozlamalari",
                'ordering': ['order', 'id'],
                'unique_together': {('direction', 'subject')},
            },
        ),
    ]

