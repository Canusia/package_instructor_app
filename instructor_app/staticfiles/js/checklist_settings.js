/**
 * Checklist Settings Configurator
 *
 * Dynamic table UI for configuring teacher application checklist items.
 * Stores data as JSON in a hidden field: [{value: "...", label: "..."}, ...]
 */

function initChecklistConfig() {
    var $hiddenField = $('#id_checklist_config');
    if (!$hiddenField.length || $hiddenField.data('table-initialized')) return;

    var defaultItems = [
        {value: 'Class Assigned', label: 'Class Assigned'},
        {value: 'Hotel Room Requested', label: 'Hotel Room Requested'},
        {value: 'NetID Activated', label: 'NetID Activated'},
        {value: 'Imported into PS', label: 'Imported into PS'}
    ];

    var items = defaultItems;
    try {
        var val = $hiddenField.val();
        if (val) {
            var parsed = JSON.parse(val);
            if (Array.isArray(parsed) && parsed.length > 0) {
                items = parsed;
            }
        }
    } catch (e) {}

    var $container = $('<div class="checklist-config-container mb-3"></div>');
    var $label = $('<label class="form-label"><strong>Application Checklist Items</strong></label>');
    var $helpText = $('<small class="form-text text-muted mb-2 d-block">Add, remove, or rename checklist items for teacher applications</small>');
    var $table = $('<table class="table table-sm table-bordered" style="max-width: 500px;"></table>');
    var $thead = $('<thead class="thead-light"><tr><th>Label</th><th style="width: 50px;"></th></tr></thead>');
    var $tbody = $('<tbody></tbody>');
    var $addBtn = $('<button type="button" class="btn btn-sm btn-outline-primary mt-2"><i class="fa fa-plus"></i> Add Item</button>');

    function createRow(item) {
        var $row = $('<tr></tr>');
        var $labelInput = $('<input type="text" class="form-control form-control-sm checklist-label-input" placeholder="e.g., Class Assigned">');
        $labelInput.val(item.label || '');
        var $removeBtn = $('<button type="button" class="btn btn-sm btn-outline-danger"><i class="fa fa-times"></i></button>');

        $row.append($('<td></td>').append($labelInput));
        $row.append($('<td class="text-center"></td>').append($removeBtn));

        $removeBtn.on('click', function () {
            $row.remove();
            updateHiddenField();
        });

        $labelInput.on('change', updateHiddenField);

        return $row;
    }

    function updateHiddenField() {
        var config = [];
        $tbody.find('tr').each(function () {
            var label = $(this).find('.checklist-label-input').val().trim();
            if (label) {
                config.push({value: label, label: label});
            }
        });
        $hiddenField.val(JSON.stringify(config));
    }

    items.forEach(function (item) {
        $tbody.append(createRow(item));
    });

    $addBtn.on('click', function () {
        $tbody.append(createRow({value: '', label: ''}));
    });

    $table.append($thead).append($tbody);
    $container.append($label).append($helpText).append($table).append($addBtn);

    var $submitBtn = $hiddenField.closest('form').find('input[type="submit"], button[type="submit"]');
    if ($submitBtn.length) {
        $submitBtn.first().before($container);
    } else {
        $hiddenField.closest('div').after($container);
    }
    $hiddenField.data('table-initialized', true);

    updateHiddenField();
}

$(document).ajaxComplete(function () {
    initChecklistConfig();
});

$(document).ready(function () {
    initChecklistConfig();
});
