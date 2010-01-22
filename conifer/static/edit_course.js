/*
this seems to be causing a disable when we don't want it
*/
function do_init() {
    if ($('#id_code')[0].tagName == 'SELECT') {
	// code is a SELECT, so we add a callback to lookup titles.
	$('#id_code').change(function() {
	    $('#id_title')[0].disabled=true;
	    $.getJSON('/syrup/course/new/ajax_title', {course_code: $(this).val()},
		      function(resp) {
			  $('#id_title').val(resp.title)
			  $('#id_title')[0].disabled=false;

		      });
	});
    }
}

$(do_init);
