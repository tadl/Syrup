$(function() {
    var fuzzy = fuzzyFinder(
	'#fuzzyinput', '#fuzzypanel', '#fuzzyedit', '#fuzzyview', '#fuzzyname', '#fuzzychange', '#owner');
    $('#id_start_term').change(onStartTermChange);
});

function onStartTermChange() {
    if ($('#id_end_term').val() == "") {
	$('#id_end_term').val($('#id_start_term').val());
    }
}