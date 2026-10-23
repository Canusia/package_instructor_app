"""Application notes that older code wrote to the host's cis table (#11).

Notes now live only in ``instructor_app.TeacherApplicationNote``. Some tenants
(WSU, westmoreland) also have ``cis.TeacherApplicationNote`` pointing at this
package's TeacherApplication, holding notes written before the switch. Other
tenants' cis model points at cis's own TeacherApplication (or is absent) and
holds nothing of ours, so it is left alone.
"""
from django.apps import apps
from django.core.exceptions import FieldDoesNotExist


def legacy_note_model():
    """``cis.TeacherApplicationNote`` if it references our applications, else None."""
    from ..models.teacher_application import TeacherApplication
    try:
        model = apps.get_model('cis', 'TeacherApplicationNote')
        field = model._meta.get_field('teacher_application')
    except (LookupError, FieldDoesNotExist):
        return None
    return model if field.related_model is TeacherApplication else None


def copy_legacy_notes(dry_run=False):
    """Copy legacy notes into the package table, keeping their ids so reply
    links and ``parent`` pointers still resolve. Idempotent.

    Returns (copied, already_present); (0, 0) when there is no legacy table.
    """
    from ..models.teacher_application_note import TeacherApplicationNote
    legacy = legacy_note_model()
    if legacy is None:
        return 0, 0
    existing = set(TeacherApplicationNote.objects.values_list('id', flat=True))
    copied = present = 0
    for old in legacy.objects.all().iterator():
        if old.id in existing:
            present += 1
            continue
        copied += 1
        if dry_run:
            continue
        TeacherApplicationNote.objects.create(
            id=old.id,
            teacher_application_id=old.teacher_application_id,
            note=old.note,
            createdby_id=old.createdby_id,
            parent=old.parent,
            meta=getattr(old, 'meta', None),
        )
        # createdon is auto_now_add; keep the original time.
        TeacherApplicationNote.objects.filter(id=old.id).update(createdon=old.createdon)
    return copied, present


def delete_legacy_notes(teacher_application):
    """Remove an application's legacy notes so deleting it isn't blocked by a
    PROTECT foreign key (westmoreland)."""
    legacy = legacy_note_model()
    if legacy is not None:
        legacy.objects.filter(teacher_application=teacher_application).delete()
