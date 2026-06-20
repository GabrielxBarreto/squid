from celery import shared_task
from django.core.mail import send_mail
from celery import shared_task
from django.core.mail import send_mail

from dashboard import models
#destinatários é um array!!!
@shared_task
def enviar_email_na_data(email, assunto, mensagem, membros):
    for membro in membros:
        participante = models.Participante.objects.filter(id=membro.id).first()
        if participante.email:
            send_mail(
                subject=assunto,
                message=mensagem,
                from_email=email,
                recipient_list=[participante.email],
                fail_silently=False,
            )