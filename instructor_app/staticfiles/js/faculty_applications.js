$(document).ready(function () {
    var baseURL = $('#applications-config').data('api-url');
    var detailBaseURL = $('#applications-config').data('detail-url');

    function initTable(tableId, filterFormId, extraParams) {
        extraParams = extraParams || '';
        var filterForm = $('form#' + filterFormId);

        var table = $('#' + tableId).DataTable({
            ajax: baseURL + '&' + extraParams + filterForm.serialize(),
            serverSide: true,
            processing: true,
            stateSave: true,
            lengthMenu: [30, 50, 100],
            order: [[0, 'desc']],
            columns: [
                null,
                {
                    render: function (data, type, row) {
                        return row.user.last_name + ', ' + row.user.first_name;
                    }
                },
                {
                    render: function (data, type, row) {
                        if (row.highschool == null) return '';
                        return row.highschool.name;
                    }
                },
                {
                    searchable: false,
                    orderable: false
                },
                null,
                {
                    searchable: false,
                    orderable: false,
                    render: function (data, type, row) {
                        return "<a class='btn btn-sm btn-primary' href='" + detailBaseURL + row.id + "'>Details</a>";
                    }
                }
            ]
        });

        $(document).on('change', 'form#' + filterFormId + ' :input', function () {
            var newURL = baseURL + '&' + extraParams + filterForm.serialize();
            table.ajax.url(newURL).load();
        });

        return table;
    }

    initTable('records_active', 'filter_active', 'active_only=true&');
    initTable('records_all', 'filter_all', '');
});
