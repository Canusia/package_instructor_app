jQuery(function ($) {
    $('.dataTable').DataTable();
});

jQuery(document).ready(function ($) {
    var config = $('#detail-config');
    var remindReviewerUrl = config.data('remind-reviewer-url');
    var updateReviewerStatusUrl = config.data('update-reviewer-status-url');
    var sendApprovalEmailUrl = config.data('send-approval-email-url');
    var csrfToken = config.data('csrf-token');

    $('#id_date_of_birth').mask('00/00/0000');
    $('#id_ssn').mask('000-00-0000');
    $('#id_primary_phone, #id_alt_phone, #id_secondary_phone').mask('0000000000');

    // AJAX form submission
    $('form.frm_ajax').submit(function (event) {
        var blocked_element = $(this).parent();
        $(blocked_element).block();
        event.preventDefault();

        var form = $(this);
        var action = form.attr('action');

        $.post({
            url: action,
            data: form.serialize(),
            error: function (xhr) {
                var span = document.createElement('span');
                span.innerHTML = xhr.responseJSON.message;
                swal({
                    title: xhr.responseJSON.message,
                    content: span,
                    icon: 'warning'
                });
                $(blocked_element).unblock();
            },
            success: function (response) {
                swal("Success", response.message, response.status);
                $(blocked_element).unblock();
            }
        });
        return false;
    });

    // Remind reviewer
    $("a.remind_reviewer").on('click', function (event) {
        event.preventDefault();

        if (!confirm("Are you sure you want to send the email to the reviewer?"))
            return false;

        $.ajax({
            type: "GET",
            url: remindReviewerUrl + "?reviewer_id=" + $(this).attr('data-id'),
            success: function (response) {
                swal("", response.message, response.status);
            }
        });
    });

    // Inline reviewer status edit
    $(document).on('click', '.edit_reviewer_status', function (event) {
        event.preventDefault();
        var id = $(this).data('id');
        $('.reviewer-status-display[data-id="' + id + '"]').hide();
        $('.reviewer-status-edit[data-id="' + id + '"]').show();
    });

    $(document).on('click', '.save-reviewer-status', function () {
        var id = $(this).data('id');
        var $select = $('.reviewer-status-select[data-id="' + id + '"]');
        var status = $select.val();
        var statusLabel = $select.find('option:selected').text();

        $.ajax({
            type: "POST",
            url: updateReviewerStatusUrl,
            data: {
                reviewer_id: id,
                status: status,
                csrfmiddlewaretoken: csrfToken
            },
            success: function (response) {
                $('.reviewer-status-display[data-id="' + id + '"]').text(statusLabel).show();
                $('.reviewer-status-edit[data-id="' + id + '"]').hide();
                swal("", response.message, response.status);
            },
            error: function (xhr) {
                swal("Error", xhr.responseJSON.message, "error");
            }
        });
    });

    $(document).on('click', '.cancel-reviewer-status', function () {
        var id = $(this).data('id');
        $('.reviewer-status-display[data-id="' + id + '"]').show();
        $('.reviewer-status-edit[data-id="' + id + '"]').hide();
    });

    // Send approval email
    $("#btn_send_approval_email").on('click', function (event) {
        event.preventDefault();

        if (!confirm('Are you sure you want to do this?'))
            return;

        $.blockUI();
        $.ajax({
            type: 'GET',
            url: sendApprovalEmailUrl,
            success: function (response) {
                $.unblockUI();
                swal("", response.message, response.status);
                if (response.status == 'success') {
                    window.location.reload();
                }
            }
        });
    });

    // 403s and 500s return HTML, not JSON, so responseJSON is undefined.
    function ajaxErrorMessage(xhr) {
        if (xhr.responseJSON && xhr.responseJSON.message) {
            return xhr.responseJSON.message;
        }
        if (xhr.status === 403) {
            return 'Your session may have expired, or you do not have permission. ' +
                'Please reload the page and try again.';
        }
        return 'Something went wrong (HTTP ' + xhr.status + '). Please try again.';
    }

    // Leave the page the way the delete response asked us to.
    function finishDelete(response) {
        if (response.status != 'success') return;

        if (window.frameElement !== null) {
            // close the modal
            window.parent.closeModal();
        } else {
            window.location = response.redirect;
        }
    }

    // Asked only when the deleted application was the applicant's last one.
    // Declining is fine — the applicant stays reachable from the Applicants
    // tab, where the same action is available later.
    function offerRoleRevocation(response) {
        var prompt = response.applicant_name + ' has no other applications. ' +
            'Remove their applicant access and applicant record?';

        if (response.other_roles && response.other_roles.length) {
            prompt += ' They will keep their ' +
                response.other_roles.join(', ') + ' access.';
        }

        swal({
            title: 'Remove applicant access?',
            text: prompt,
            icon: 'warning',
            buttons: ['Keep applicant access', 'Remove applicant access']
        }).then(function (confirmed) {
            if (!confirmed) {
                finishDelete(response);
                return;
            }

            $.blockUI();
            $.ajax({
                type: 'POST',
                url: response.revoke_url,
                headers: { 'X-CSRFToken': csrfToken },
                success: function (revokeResponse) {
                    $.unblockUI();
                    swal({
                        title: revokeResponse.status == 'success' ? 'Done' : 'Not removed',
                        text: revokeResponse.message,
                        icon: revokeResponse.status
                    }).then(function () {
                        finishDelete(response);
                    });
                },
                error: function (xhr) {
                    $.unblockUI();
                    swal('Error', ajaxErrorMessage(xhr), 'error').then(function () {
                        finishDelete(response);
                    });
                }
            });
        });
    }

    // Delete application
    $("input.delete").on("click", function () {
        if (!confirm("Are you sure you want to delete this application?"))
            return;

        var url = $(this).attr('data-url');

        $.blockUI();
        $.ajax({
            type: 'GET',
            url: url,
            success: function (response) {
                $.unblockUI();
                swal({
                    title: 'Success',
                    text: response.message,
                    icon: response.status
                }).then(function () {
                    if (response.status == 'success' && response.applicant_role_revocable) {
                        offerRoleRevocation(response);
                    } else {
                        finishDelete(response);
                    }
                });
            },
            error: function (xhr) {
                $.unblockUI();
                swal("Error", ajaxErrorMessage(xhr), "error");
            }
        });
    });
});

// Delegated handler for .do-action links (replaces inline onclick/javascript: hrefs)
$(document).on('click', '.do-action', function (event) {
    event.preventDefault();

    var $el = $(this);
    var action = $el.data('action');
    var url = $el.data('url');
    var shouldConfirm = $el.data('confirm');

    if (shouldConfirm) {
        if (!confirm('Are you sure you want to do this?'))
            return;
    }

    $.ajax({
        type: "GET",
        url: url,
        data: { action: action },
        success: function (response) {
            if (response.action === 'reload_page') {
                window.location.reload();
                return;
            }

            $("#bulk_modal_content").html(response);
            $("#modal-bulk_actions").modal('show');
        }
    });
});
