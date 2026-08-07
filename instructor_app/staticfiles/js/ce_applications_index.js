var table_all, table_active, table_reviewer, table_pending, table_no_applications;

// Tenants override CSRF_COOKIE_NAME (ewu uses 'ewu_csrftoken'), so reading the
// cookie by Django's default name returns null and the POST 403s. The hidden
// input rendered by {% csrf_token %} is named the same everywhere.
function csrfToken() {
    return $('input[name="csrfmiddlewaretoken"]').first().val() ||
        getCookie('csrftoken');
}

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

setInterval(function () {
    if (!table_all.rows('.selected').any())
        table_all.ajax.reload(null, false);

    if (!table_active.rows('.selected').any())
        table_active.ajax.reload(null, false);

    if (!table_reviewer.rows('.selected').any())
        table_reviewer.ajax.reload(null, false);

    if (!table_pending.rows('.selected').any())
        table_pending.ajax.reload(null, false);
}, 5000 * 60);

function refreshTable() {
    table_all.ajax.reload();
    table_active.ajax.reload();
    table_reviewer.ajax.reload();
    table_pending.ajax.reload();
}

function do_bulk_action(action, dt) {
    var data = {
        'action': action,
        'ids': []
    };

    if (!dt.rows('.selected').any()) {
        alert("Please select a row and try again.");
        return;
    }

    var selectedRows = dt.rows({ selected: true });
    selectedRows.every(function () {
        data.ids.push(this.id());
    });

    var bulkActionUrl = $('#index-config').data('bulk-action-url');
    var modal = "modal-bulk_actions";

    $.blockUI();
    $.ajax({
        type: "GET",
        url: bulkActionUrl,
        data: data,
        success: function (response) {
            $.unblockUI();

            if (response.action == 'display') {
                var span = document.createElement('span');
                span.innerHTML = response.message;
                swal({
                    title: response.title,
                    content: span,
                    icon: response.status
                });

                var selectedRows = dt.rows({ selected: true });
                selectedRows.deselect();

                dt.ajax.reload(null, false);
                data.ids = [];
            } else {
                $("#bulk_modal_content").html(response);
                $("#" + modal).modal('show');

                var selectedRows = dt.rows({ selected: true });
                selectedRows.deselect();
            }
        }
    });
}

$(document).ready(function () {
    var config = $('#index-config');
    var baseURL = config.data('api-url');
    var reviewerApiUrl = config.data('reviewer-api-url');
    var applicantApiUrl = config.data('applicant-api-url');

    var dtDom = 'B<"float-left mt-3 mb-3"l><"float-right mt-3"f><"row clear">rt<"row"<"col-6"i><"col-6 float-right"p>>';

    var csvButton = {
        extend: 'csv', className: 'btn btn-sm btn-primary text-white text-light',
        text: '<i class="fas fa-file-csv text-white"></i>&nbsp;CSV',
        titleAttr: 'Export results to CSV'
    };
    var printButton = {
        extend: 'print', className: 'btn btn-sm btn-primary text-white text-light',
        text: '<i class="fas fa-print text-white"></i>&nbsp;Print',
        titleAttr: 'Print'
    };

    function applicationColumns(hasCheckbox, hasMissingItems) {
        var cols = [];
        if (hasCheckbox) {
            cols.push({
                searchable: false,
                orderable: false,
                render: function () { return ''; }
            });
        }
        cols.push(null); // createdon
        cols.push({
            render: function (data, type, row) {
                return row.user.last_name + ', ' + row.user.first_name;
            }
        });
        cols.push({
            render: function (data, type, row) {
                if (row.highschool == null) return '';
                return row.highschool.name;
            }
        });
        cols.push({ searchable: false, orderable: false }); // courses
        cols.push({
            render: function (data, type, row) {
                return row.status_label || row.status || '';
            }
        }); // status
        if (hasMissingItems) {
            cols.push({
                searchable: false,
                orderable: false,
                render: function (data, type, row) {
                    return row.missing_items;
                }
            });
        }
        cols.push({
            searchable: false,
            orderable: false,
            render: function (data, type, row) {
                return "<a class='btn btn-sm btn-primary record-details' href='" + row.ce_url + "'>Details</a>";
            }
        });
        return cols;
    }

    var selectConfig = {
        columnDefs: [{
            orderable: false,
            className: 'select-checkbox',
            targets: 0
        }],
        select: {
            style: 'os',
            selector: 'td:first-child'
        }
    };

    // All Applications tab
    $(document).on("change", "form#class_section_filter :input", function () {
        var form = $('form#class_section_filter');
        var newURL = baseURL + '&' + form.serialize();
        table_all.ajax.url(newURL).load();
    });

    table_all = $('#records_all').DataTable($.extend({
        fnDrawCallback: function () { $.unblockUI(); },
        dom: dtDom,
        buttons: [csvButton, printButton],
        ajax: baseURL + '&' + $('form#class_section_filter').serialize(),
        rowId: 'id',
        serverSide: true,
        processing: true,
        stateSave: true,
        lengthMenu: [30, 50, 100],
        order: [[1, 'desc']],
        columns: applicationColumns(true, false)
    }, selectConfig));

    // Active tab
    $(document).on("change", "form#class_section_filter_active :input", function () {
        var form = $('form#class_section_filter_active');
        var newURL = baseURL + '&active_only=true&' + form.serialize();
        table_active.ajax.url(newURL).load();
    });

    table_active = $('#records_active').DataTable($.extend({
        fnDrawCallback: function () { $.unblockUI(); },
        dom: dtDom,
        buttons: [csvButton, printButton],
        ajax: baseURL + '&active_only=true&' + $('form#class_section_filter_active').serialize(),
        rowId: 'id',
        serverSide: true,
        lengthMenu: [30, 50, 100],
        order: [[1, 'desc']],
        columns: applicationColumns(true, true)
    }, selectConfig));

    // Reviewers tab
    $(document).on("change", "form#reviewer_filter :input", function () {
        var form = $('form#reviewer_filter');
        var newURL = reviewerApiUrl + '&' + form.serialize();
        table_reviewer.ajax.url(newURL).load();
    });

    table_reviewer = $('#records_reviewers').DataTable({
        fnDrawCallback: function () { $.unblockUI(); },
        dom: dtDom,
        buttons: [csvButton, printButton],
        ajax: reviewerApiUrl + '&' + $('form#reviewer_filter').serialize(),
        serverSide: true,
        processing: true,
        stateSave: true,
        lengthMenu: [30, 50, 100],
        order: [[0, 'desc']],
        columns: [
            null,
            {
                render: function (data, type, row) {
                    return row.application_course.teacherapplication.user.last_name + ', ' +
                        row.application_course.teacherapplication.user.first_name;
                }
            },
            {
                render: function (data, type, row) {
                    if (row.application_course.teacherapplication.highschool == null) return '';
                    return row.application_course.teacherapplication.highschool.name;
                }
            },
            { searchable: false, orderable: false },
            {
                render: function (data, type, row) {
                    return row.reviewer.last_name + ', ' + row.reviewer.first_name;
                }
            },
            null,
            {
                searchable: false,
                orderable: false,
                render: function (data, type, row) {
                    return "<a class='btn btn-sm btn-primary record-details' href='" + row.application_course.teacherapplication.ce_url + "'>Details</a>";
                }
            }
        ]
    });

    // Pending Verification tab
    table_pending = $('#records_pending').DataTable($.extend({
        fnDrawCallback: function () { $.unblockUI(); },
        dom: dtDom,
        buttons: [
            csvButton,
            printButton,
            {
                className: 'btn btn-sm btn-primary text-white text-light',
                text: '<i class="fas fa-edit text-white"></i>&nbsp;Resend Verification Link',
                titleAttr: 'resend_verification_link',
                action: function (e, dt) {
                    do_bulk_action('resend_verification_link', dt);
                }
            },
            {
                className: 'btn btn-sm btn-primary text-white text-light',
                text: '<i class="fas fa-edit text-white"></i>&nbsp;Get Verification Link',
                titleAttr: 'get_verification_link',
                action: function (e, dt) {
                    do_bulk_action('get_verification_link', dt);
                }
            }
        ],
        ajax: applicantApiUrl + '&pending_only=true',
        rowId: 'id',
        serverSide: true,
        processing: true,
        stateSave: true,
        lengthMenu: [30, 50, 100],
        order: [[1, 'asc']],
        columns: [
            {
                searchable: false,
                orderable: false,
                render: function () { return ''; }
            },
            {
                render: function (data, type, row) {
                    return row.user.last_name + ', ' + row.user.first_name;
                }
            },
            null, // email
            {
                render: function (data, type, row) {
                    return row.status_label || row.status || '';
                }
            }, // status
            {
                render: function (data, type, row) {
                    return row.account_verified ? '<span class="badge badge-success">Yes</span>' : '<span class="badge badge-warning">No</span>';
                }
            },
            {
                searchable: false,
                orderable: false,
                render: function (data, type, row) {
                    return "<button type='button' class='btn btn-sm btn-outline-primary show-verify-link' data-url='" + row.verify_email_url + "'><i class='fas fa-link'></i> Verify Link</button>";
                }
            }
        ]
    }, selectConfig));

    // Applicants w/o Applications tab. These applicants appear on no other
    // tab, so this is the only place staff can clear a role the delete prompt
    // left behind.
    table_no_applications = $('#records_no_applications').DataTable({
        fnDrawCallback: function () { $.unblockUI(); },
        dom: dtDom,
        buttons: [csvButton, printButton],
        ajax: applicantApiUrl + '&no_applications=1',
        rowId: 'id',
        serverSide: true,
        processing: true,
        stateSave: true,
        lengthMenu: [30, 50, 100],
        order: [[0, 'asc']],
        columns: [
            {
                render: function (data, type, row) {
                    return row.user.last_name + ', ' + row.user.first_name;
                }
            },
            null, // email
            {
                render: function (data, type, row) {
                    return row.status_label || row.status || '';
                }
            },
            {
                searchable: false,
                orderable: false,
                render: function (data, type, row) {
                    // Applicant names are self-registered, so they are
                    // attacker-controlled and must not reach markup unescaped.
                    return $('<button>')
                        .attr('type', 'button')
                        .addClass('btn btn-sm btn-outline-danger revoke-applicant')
                        .attr('data-url', row.revoke_url)
                        .attr('data-name', row.user.last_name + ', ' + row.user.first_name)
                        .text('Remove applicant access')
                        .prop('outerHTML');
                }
            }
        ]
    });

    $(document).on('click', '.revoke-applicant', function () {
        var url = $(this).data('url');
        var name = $(this).data('name');

        swal({
            title: 'Remove applicant access?',
            text: 'Remove applicant access and the applicant record for ' + name +
                '? Their other roles and their user account are not affected.',
            icon: 'warning',
            buttons: ['Cancel', 'Remove applicant access']
        }).then(function (confirmed) {
            if (!confirmed) return;

            $.blockUI();
            $.ajax({
                type: 'POST',
                url: url,
                headers: { 'X-CSRFToken': csrfToken() },
                success: function (response) {
                    $.unblockUI();
                    swal({
                        title: response.status == 'success' ? 'Done' : 'Not removed',
                        text: response.message,
                        icon: response.status
                    }).then(function () {
                        table_no_applications.ajax.reload();
                    });
                },
                error: function (xhr) {
                    $.unblockUI();
                    swal('Error', ajaxErrorMessage(xhr), 'error');
                }
            });
        });
    });

    $(document).on('click', '.show-verify-link', function () {
        var url = $(this).data('url') || '';
        $('#verify-link-modal-input').val(url);
        $('#verify-link-modal-copied').hide();
        $('#verify-link-modal').modal('show');
    });

    $(document).on('click', '#verify-link-modal-copy', function () {
        var $input = $('#verify-link-modal-input');
        $input.trigger('select');
        $input[0].setSelectionRange(0, 99999);
        try {
            document.execCommand('copy');
            $('#verify-link-modal-copied').show();
        } catch (e) { /* noop */ }
    });
});
