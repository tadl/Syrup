function do_init() {
    show_specific_only();
    $('#id_access').change(show_specific_only);
}

function show_specific_only() {
    $('.specific').hide();
    var cur = $('#id_access').val();
    $('#' + cur + '_panel').fadeIn();
}

$(do_init);


function deleteGroup(linkid, groupid) {
    var link = $('#'+linkid);
    link.hide();
    var sure = $('<span>are you sure? </span>');
    var yes = $('<a href="javascript:void();">yes</a>');
    var no = $('<a href="javascript:void();">no</a>');
    yes.click(function() { 
	$.post('delete_group/', 
	       {id: groupid},
	       function() { 
		   link.parents('tr').fadeOut();
	       }); 
    });
    no.click(function() { 
	link.show(); sure.hide();
    });
    sure.append(yes).append(" / ").append(no);
    link.after(sure);
}