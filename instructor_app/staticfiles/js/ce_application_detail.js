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
        var status = $('.reviewer-status-select[data-id="' + id + '"]').val();

        $.ajax({
            type: "POST",
            url: updateReviewerStatusUrl,
            data: {
                reviewer_id: id,
                status: status,
                csrfmiddlewaretoken: csrfToken
            },
            success: function (response) {
                $('.reviewer-status-display[data-id="' + id + '"]').text(status).show();
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

    // Delete application
    $("input.delete").on("click", function () {
        if (!confirm("Are you sure you want to permanently delete this record and everything associated with it?"))
            return;

        var url = $(this).attr('data-url');

        $.blockUI();
        $.ajax({
            type: 'GET',
            url: url,
            success: function (response) {
                $.unblockUI();
                swal("", response.message, response.status);
                if (response.status == 'success') {
                    window.location = response.redirect;
                }
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
