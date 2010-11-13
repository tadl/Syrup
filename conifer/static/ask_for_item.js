function askToDownload() {
    $.post('askfor', function() {
	$('#ask_to_download_panel').fadeOut('fast', function() {
	    $('#downloadpanel').fadeIn(1000);
	});
    });
}
