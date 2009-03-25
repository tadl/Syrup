function init_blocks() {
    $('span.menublock').each(make_opener);
}

var blocknum = 0;
function make_opener() {
    var menublock = $(this);
    var blockid = 'menublock' + (blocknum++);
    menublock.attr('id', blockid);
    var opener = '<a class="menublockopener" onmouseover="openblock(\'' + blockid + '\');" href="javascript:openblock(\'' + blockid + '\');">&raquo;</a>';
    menublock.before(opener);
    menublock.hide();
}

function openblock(bid) {
    $('span.menublock').hide();
    $('#' + bid).fadeIn('fast');
}

$(init_blocks);


// fixme, I need to rename menublocks.js to something more like
// 'course-item-stuff.js'.

// this is some item reordering code. 

var reordering = false;

function doReorder() {
    if (!reordering)  {
	$('.itemtree').sortable({axis:'y'});
	$('.an_item').css({ marginTop: '20px' });
	$('#reorder_panel').after($('#ropanelmessage'));
	$('#reorder_panel a').text($('#i18n-save-order').text());
	reordering = true;
    } else {
	$('.an_item').css({ marginTop: '4px' });
	$('#ropanelmessage').remove();
	$('#reorder_panel a').text('...');
	$('.itemtree').sortable('destroy');
	reordering = false;
	// get the LI item ids. Send them to the server.
	var new_sequence = $('.an_item').map(function() { return $(this).attr('id') });
	var new_seq_string = Array.join(new_sequence, ',');
	$.post('reseq', {'new_order':new_seq_string}, 
		   function() {
		       $('#reorder_panel a').text($('#i18n-reorder-items').text());
		       alert($('#i18n-new-order-saved').text());
		   });
    }
};
