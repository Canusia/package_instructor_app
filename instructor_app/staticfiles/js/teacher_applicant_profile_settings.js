/**
 * Teacher Applicant Profile — Settings UI.
 *
 * Mirrors future_sections' Teaching Form Fields configurator: a single
 * hidden CharField `field_config` stores JSON; this script syncs the
 * visible table (Visible / Required / Custom Label / Weight) to and
 * from that JSON.
 *
 * JSON shape:
 *   {
 *     "visible":  ["first_name", ...],   // ordered, lighter weight first
 *     "required": ["first_name", ...],
 *     "labels":   {"first_name": "Given Name", ...},
 *     "weights":  {"first_name": 10, ...}
 *   }
 */
function initTeacherApplicantProfileConfig() {
    var $hidden = $('input[name="field_config"]');
    if (!$hidden.length) return;
    var $ui = $('#teacher-applicant-profile-config-ui');
    if (!$ui.length) return;
    if ($ui.data('tapfc-initialized')) return;
    $ui.data('tapfc-initialized', true);

    var config = {};
    try { config = JSON.parse($hidden.val() || '{}'); } catch (e) { config = {}; }
    if (!config || typeof config !== 'object') config = {};

    var visible  = config.visible  || [];
    var required = config.required || [];
    var labels   = config.labels   || {};
    var weights  = config.weights  || {};

    $ui.find('.tapfc-visible').each(function () {
        $(this).prop('checked', visible.indexOf($(this).data('field')) !== -1);
    });
    $ui.find('.tapfc-required').each(function () {
        $(this).prop('checked', required.indexOf($(this).data('field')) !== -1);
    });
    $ui.find('.tapfc-label').each(function () {
        var v = labels[$(this).data('field')];
        if (v) $(this).val(v);
    });
    $ui.find('.tapfc-weight').each(function () {
        var w = weights[$(this).data('field')];
        if (w !== undefined && w !== null) $(this).val(w);
    });

    function syncToHidden() {
        var newVisible  = [];
        var newRequired = [];
        var newLabels   = {};
        var newWeights  = {};

        $ui.find('.tapfc-visible:checked').each(function () {
            newVisible.push($(this).data('field'));
        });
        $ui.find('.tapfc-required:checked').each(function () {
            newRequired.push($(this).data('field'));
        });
        $ui.find('.tapfc-label').each(function () {
            var v = $(this).val().trim();
            if (v) newLabels[$(this).data('field')] = v;
        });
        $ui.find('.tapfc-weight').each(function () {
            var v = $(this).val();
            if (v !== '' && v !== undefined && v !== null) {
                newWeights[$(this).data('field')] = parseInt(v, 10);
            }
        });

        // Order visible by weight (lighter first; unweighted last).
        newVisible.sort(function (a, b) {
            var wa = newWeights.hasOwnProperty(a) ? newWeights[a] : Number.MAX_SAFE_INTEGER;
            var wb = newWeights.hasOwnProperty(b) ? newWeights[b] : Number.MAX_SAFE_INTEGER;
            return wa - wb;
        });

        $hidden.val(JSON.stringify({
            visible:  newVisible,
            required: newRequired,
            labels:   newLabels,
            weights:  newWeights,
        }));
    }

    // Required implies visible; unchecking visible un-requires.
    $ui.on('change', '.tapfc-required', function () {
        if ($(this).is(':checked')) {
            $ui.find('.tapfc-visible[data-field="' + $(this).data('field') + '"]')
                .prop('checked', true);
        }
        syncToHidden();
    });
    $ui.on('change', '.tapfc-visible', function () {
        if (!$(this).is(':checked')) {
            $ui.find('.tapfc-required[data-field="' + $(this).data('field') + '"]')
                .prop('checked', false);
        }
        syncToHidden();
    });
    $ui.on('input', '.tapfc-label, .tapfc-weight', syncToHidden);

    $hidden.closest('form').on('submit', syncToHidden);
}

$(document).ajaxComplete(initTeacherApplicantProfileConfig);
$(document).ready(initTeacherApplicantProfileConfig);
