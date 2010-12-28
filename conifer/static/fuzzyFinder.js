function fuzzyFinder(Search, Matches, EditPanel, ViewPanel, ViewName, Change, Owner) {
    var here = {

	lastText: null,
	lastPress: null,
	waiting: false,
	minWait: 500,
	
	lookup: function() {
	    var text = $(this).val();
	    if (text != here.lastText) {
		here.lastText = text;
		if (text.length < 3) {
		    return;
		}
		here.lastPress = new Date();
	    }
	},
	
	interval: function() {
	    var now = new Date();
	    
	    if (here.lastPress == null || (now - here.lastPress) < here.minWait) {
		return;
	    }
	    
	    if (here.waiting) {
		return;
	    }
	    
	    here.waiting = true;
	    $(Search).css({backgroundColor: 'yellow'}); // debugging
	    $.post(ROOT + '/fuzzy_user_lookup', {'q': here.lastText},
		   function(data) {
		       here.waiting = false;
		       here.lastPress = null;
		       $(Search).css({backgroundColor: 'white'}); // debugging
		       $(Matches).text('');
		       if (data.results.length == 0) {
			   $(Matches).append('No matches.');
		       }
		       $.each(data.results, function(i,val) {
			   var link = $('<a class="fuzzychoice" href="#"/>');
			   link.text(val[1]);
			   link.data('userid', val[0]);
			   link.data('display', val[1]);
			   link.click(here.pick);
			   $(Matches).append(link);
		       });
		       if (data.notshown > 0) {
			   $(Matches).append('<div>and ' + data.notshown + ' more.</div>');
		       }
		   }, 'json');
	},
	
	pick: function(uid) {
	    $(EditPanel).hide();
	    $(ViewPanel).show();
	    
	    var inp = $(Owner);
	    inp.val($(this).data('userid'));
	    
	    $(ViewName).text($(this).data('display'));
	},
	
	edit: function() {
	    $(ViewPanel).hide();
	    $(EditPanel).show();
	    $(Search).focus();
	    here.lastText = $(Search).val();
	    here.lastPress = new Date(new Date() - 450);
	}
    };
    setInterval(here.interval, 250);
    $(Search).keyup(here.lookup);
    $(Change).click(here.edit);
    return here;
}
    
