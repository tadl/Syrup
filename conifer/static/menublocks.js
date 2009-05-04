function init_blocks() {
    $('span.menublock').each(make_opener);
    $('div').click(hideblocks);
}

var LINGER = 200; // # milliseconds linger-time required to trigger menu
var blocknum = 0;
function make_opener() {
    var menublock = $(this);
    var blockid = 'menublock' + (blocknum++);
    menublock.attr('id', blockid);
    var opener = '<a class="menublockopener" onmouseout="maybe_cancelblock(\'' + blockid + '\');" onmouseover="maybe_openblock(\'' + blockid + '\');" href="javascript:maybe_openblock(\'' + blockid + '\');">&raquo;</a>';
    menublock.before(opener);
    menublock.hide();
}

function hideblocks() {
    $('span.menublock').hide();
}

// the block we are scheduling to open (due to a mouseover).
var block_to_open = null;

function maybe_cancelblock(bid) {
    // if it is not open yet, this will stop it from opening.
    block_to_open = null;
}

function maybe_openblock(bid) {
    // it's 'maybe' because it's cancellable. You have to linger for
    // LINGER milliseconds for the open to happen; otherwise
    // maybe_cancelblock() will prevent it.
    block_to_open = bid;
    var cmd = 'openblock("' + bid + '")';
    setTimeout(cmd, LINGER);
}

function openblock(bid) {
    if (!resequencing) {	// it's annoying during reseq.
	if (block_to_open == bid) {
	    hideblocks();
	    $('#' + bid).fadeIn('fast');
	    block_to_open = null;
	}
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
	//$('#resequence_panel').after($('#ropanelmessage'));
	$('#ropanelmessage').show();
	$('#resequence_panel a').text($('#i18n-save-order').text());
	resequencing = true;
    } else {
	$('.an_item').removeClass('sort_item');
	$('#ropanelmessage').hide();
	$('#resequence_panel a').text('...');
	$('.itemtree').sortable('destroy');
	resequencing = false;
	// get the LI item ids. Send them to the server.
	var new_sequence_str = '';
	$('.an_item').each(function() { new_sequence_str += $(this).attr('id') + ' '; });
	$.post('reseq', {'new_order':new_sequence_str}, 
		   function() {
		       $('#resequence_panel a').text($('#i18n-resequence-items').text());
		       alert($('#i18n-new-order-saved').text());
		   });
    }
};

var xxx = null;

function doToggleItemTree() {
    if ($('.itemtree:hidden').length > 0) {
	$('.itemtree:hidden').fadeIn(500);
    } else {
	$('.itemtree').not('.itemtree:nth(0)').fadeOut('slow');
    }
}
