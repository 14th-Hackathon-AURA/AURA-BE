from django.contrib import admin

from .models import ChatMessage, ChatSession, VisitCard


admin.site.register(ChatSession)
admin.site.register(ChatMessage)
admin.site.register(VisitCard)
