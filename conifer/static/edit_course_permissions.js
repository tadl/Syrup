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