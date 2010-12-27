var fuzzyLookup = {

	lastText: null,
	lastPress: null,
	waiting: false,
	
	lookup: function() {
		var text = $(this).val();
		if (text != fuzzyLookup.lastText) {
			fuzzyLookup.lastText = text;
			if (text.length < 3) {
				return;
			}
			fuzzyLookup.lastPress = new Date();
		}
	},

	minWait: 500,

	interval: function() {
		var now = new Date();

		if (fuzzyLookup.lastPress == null || (now - fuzzyLookup.lastPress) < fuzzyLookup.minWait) {
			return;
		}

		if (fuzzyLookup.waiting) {
			return;
		}

		fuzzyLookup.waiting = true;
		$('#fuzzyinput').css({backgroundColor: 'yellow'}); // debugging
		$.post('site_fuzzy_user_lookup', {'q': fuzzyLookup.lastText},
			   function(data) {
				   fuzzyLookup.waiting = false;
				   fuzzyLookup.lastPress = null;
				   $('#fuzzyinput').css({backgroundColor: 'white'}); // debugging
				   $('#fuzzypanel').text('');
				   if (data.results.length == 0) {
					   $('#fuzzypanel').append('No matches.');
				   }
				   $.each(data.results, function(i,val) {
					   var link = $('<a class="fuzzychoice" href="#"/>');
					   link.text(val[1]);
					   link.data('userid', val[0]);
					   link.data('display', val[1]);
					   link.click(fuzzyLookup.pick);
					   $('#fuzzypanel').append(link);
				   });
				   if (data.notshown > 0) {
					   $('#fuzzypanel').append('<div>and ' + data.notshown + ' more.</div>');
				   }
			   }, 'json');
	},

	pick: function(uid) {
		$('#fuzzyedit').hide();
		$('#fuzzyview').show();

		var inp = $('#owner');
		inp.val($(this).data('userid'));

		$('#fuzzyname').text($(this).data('display'));
	},

	edit: function() {
		$('#fuzzyview').hide();
		$('#fuzzyedit').show();
		$('#fuzzyinput').focus();
		fuzzyLookup.lastText = $('#fuzzyinput').val();
		fuzzyLookup.lastPress = new Date(new Date() - 450);
	}
}

$(function() {
	$('#fuzzyinput').keyup(fuzzyLookup.lookup);
	setInterval(fuzzyLookup.interval, 250);
});
