from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.care.models import Diagnosis, VisitReservation
from apps.community.models import Comment, Post

from .models import Notification, calculate_membership_tier_from_counts
from .notification_service import create_notification


def _remember_previous_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    instance._previous_status = (
        sender.objects.filter(pk=instance.pk)
        .values_list("status", flat=True)
        .first()
    )


pre_save.connect(_remember_previous_status, sender=Diagnosis)
pre_save.connect(_remember_previous_status, sender=VisitReservation)


def _frontend_path(setting_name, fallback, **values):
    template = getattr(settings, setting_name, fallback)
    return template.format(**values)


@receiver(post_save, sender=Diagnosis)
def notify_diagnosis_result(sender, instance, created, **kwargs):
    if created or instance.status == instance._previous_status:
        return
    action_url = _frontend_path(
        "FRONTEND_DIAGNOSIS_PATH_TEMPLATE",
        "/care/diagnoses/{id}",
        id=instance.pk,
    )
    if instance.status == Diagnosis.Status.DONE:
        level = instance.get_condition_level_display() if instance.condition_level else "진단 완료"
        create_notification(
            user=instance.requested_by,
            type=Notification.Type.CARE,
            title="AI 케어 진단이 완료되었어요",
            body=f"{instance.product.name} 진단 결과는 {level}입니다.",
            action_url=action_url,
            event_key=f"diagnosis:{instance.pk}:done",
        )
    elif instance.status == Diagnosis.Status.FAILED:
        create_notification(
            user=instance.requested_by,
            type=Notification.Type.CARE,
            title="AI 케어 진단을 완료하지 못했어요",
            body=f"{instance.product.name} 사진을 확인한 뒤 다시 진단해 주세요.",
            action_url=action_url,
            event_key=f"diagnosis:{instance.pk}:failed",
        )


@receiver(post_save, sender=VisitReservation)
def notify_visit_reservation(sender, instance, created, **kwargs):
    if created:
        title = "방문 예약이 접수되었어요"
        body = f"{instance.store.name} 방문 예약을 접수했습니다."
        event = "created"
    elif instance.status != instance._previous_status:
        title = "방문 예약 상태가 변경되었어요"
        body = f"{instance.store.name} 예약 상태: {instance.get_status_display()}"
        event = instance.status.lower()
    else:
        return
    create_notification(
        user=instance.user,
        type=Notification.Type.GENERAL,
        title=title,
        body=body,
        action_url=_frontend_path(
            "FRONTEND_VISIT_PATH_TEMPLATE",
            "/my/visit-reservations/{id}",
            id=instance.pk,
        ),
        event_key=f"visit:{instance.pk}:{event}",
    )


TIER_RANK = {
    "AURA Silver": 0,
    "AURA Gold": 1,
    "AURA Platinum": 2,
    "AURA Diamond": 3,
}


def _notify_membership_upgrade(user, *, previous_posts, previous_comments):
    current_tier = calculate_membership_tier_from_counts(
        user.post_set.count(), user.comment_set.count()
    )
    previous_tier = calculate_membership_tier_from_counts(
        previous_posts, previous_comments
    )
    if TIER_RANK[current_tier] <= TIER_RANK[previous_tier]:
        return
    create_notification(
        user=user,
        type=Notification.Type.MEMBERSHIP,
        title=f"{current_tier} 등급으로 올라갔어요",
        body="커뮤니티 활동으로 새로운 멤버십 등급을 달성했습니다.",
        action_url=getattr(settings, "FRONTEND_MEMBERSHIP_PATH", "/my/membership"),
        event_key=f"membership:{current_tier}",
    )


@receiver(post_save, sender=Post)
def notify_membership_after_post(sender, instance, created, **kwargs):
    if created:
        user = instance.author
        _notify_membership_upgrade(
            user,
            previous_posts=max(user.post_set.count() - 1, 0),
            previous_comments=user.comment_set.count(),
        )


@receiver(post_save, sender=Comment)
def notify_membership_after_comment(sender, instance, created, **kwargs):
    if created:
        user = instance.author
        _notify_membership_upgrade(
            user,
            previous_posts=user.post_set.count(),
            previous_comments=max(user.comment_set.count() - 1, 0),
        )
