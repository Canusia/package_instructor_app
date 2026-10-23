"""Application notes that older code wrote to the host's cis table (#11).

Notes now live only in ``instructor_app.TeacherApplicationNote``. Some tenants
(WSU, westmoreland) also have ``cis.TeacherApplicationNote`` pointing at this
package's TeacherApplication, holding notes written before the switch. Other
tenants' cis model points at cis's own TeacherApplication (or is absent) and
holds nothing of ours, so it is left alone.
"""
from django.apps import apps
from django.db import transaction
from django.core.exceptions import FieldDoesNotExist


def legacy_note_model():
    """``cis.TeacherApplicationNote`` if it references our applications, else None."""
    try:
        model = apps.get_model('cis', 'TeacherApplicationNote')
        field = model._meta.get_field('teacher_application')
    except (LookupError, FieldDoesNotExist):
        return None
    # By label, not class identity: editable and installed layouts differ.
    target = field.related_model._meta.label if field.related_model else None
    return model if target == 'instructor_app.TeacherApplication' else None


def copy_legacy_notes(dry_run=False):
    """Copy legacy notes into the package table, keeping their ids so reply
    links and ``parent`` pointers still resolve. Idempotent and atomic.

    Rows are bulk-created so the note post_save signal does not fire: copying
    must not re-email applicants or raise CE alerts for old notes. Rows with no
    application are skipped (the package FK is not nullable). ``createdon`` is
    copied from the legacy row, whose cis field is auto_now -- so it is the
    note's last edit, which for notes is in practice its creation.

    Returns (copied, already_present, skipped); zeros when there is no
    legacy table.
    """
    from ..models.teacher_application_note import TeacherApplicationNote
    legacy = legacy_note_model()
    if legacy is None:
        return 0, 0, 0
    existing = set(TeacherApplicationNote.objects.values_list('id', flat=True))
    to_copy, present, skipped = [], 0, 0
    for old in legacy.objects.all().iterator():
        if old.id in existing:
            present += 1
        elif not old.teacher_application_id:
            skipped += 1
        else:
            to_copy.append(old)
    if dry_run or not to_copy:
        return len(to_copy), present, skipped
    with transaction.atomic():
        TeacherApplicationNote.objects.bulk_create([
            TeacherApplicationNote(
                id=old.id,
                teacher_application_id=old.teacher_application_id,
                note=old.note,
                createdby_id=old.createdby_id,
                parent=old.parent,
                meta=getattr(old, 'meta', None),
            ) for old in to_copy
        ])
        # createdon is auto_now_add on create; restore the original times.
        for old in to_copy:
            TeacherApplicationNote.objects.filter(id=old.id).update(createdon=old.createdon)
    return len(to_copy), present, skipped


def delete_legacy_notes(teacher_application):
    """Remove an application's legacy notes so deleting it isn't blocked by a
    PROTECT foreign key (westmoreland)."""
    legacy = legacy_note_model()
    if legacy is not None:
        legacy.objects.filter(teacher_application=teacher_application).delete()
