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