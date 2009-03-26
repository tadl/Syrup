function init_blocks() {
    $('span.menublock').each(make_opener);
    $('div').click(hideblocks);
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

function hideblocks() {
    $('span.menublock').hide();
}

function openblock(bid) {
    if (!resequencing) {
	hideblocks();
	$('#' + bid).fadeIn('fast');
    }
}

$(init_blocks);


// fixme, I need to rename menublocks.js to something more like
// 'course-item-stuff.js'.

// this is some item resequencing code. 

var resequencing = false;

function doResequence() {
    if (!resequencing)  {
	$('.itemtree:nth(0)').sortable({axis:'y'});
	$('.itemtree:nth(0) > .an_item').addClass('sort_item');
	$('#resequence_panel').after($('#ropanelmessage'));
	$('#resequence_panel a').text($('#i18n-save-order').text());
	resequencing = true;
    } else {
	$('.an_item').removeClass('sort_item');
	$('#ropanelmessage').remove();
	$('#resequence_panel a').text('...');
	$('.itemtree').sortable('destroy');
	resequencing = false;
	// get the LI item ids. Send them to the server.
	var new_sequence = $('.an_item').map(function() { return $(this).attr('id') });
	var new_seq_string = Array.join(new_sequence, ',');
	$.post('reseq', {'new_order':new_seq_string}, 
		   function() {
		       $('#resequence_panel a').text($('#i18n-resequence-items').text());
		       alert($('#i18n-new-order-saved').text());
		   });
    }
};

function doToggleItemTree() {
    if ($('.itemtree:hidden').length > 0) {
	$('.itemtree:hidden').fadeIn(1000);
    } else {
	$('.itemtree').not('.itemtree:nth(0)').fadeOut('slow');
    }
}
