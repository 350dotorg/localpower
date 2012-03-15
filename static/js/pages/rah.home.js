/*jslint maxerr: 1000, white: true, browser: true, devel: true, rhino: true, onevar: false, undef: true, nomen: true, eqeqeq: true, plusplus: true, bitwise: true, regexp: true, newcap: true, immed: true, sub: true */
/*global $: false, FB: false, WebFont: false, jQuery: false, window: false, google: false, require: false, define: false */
require([], function () {
    var hash = window.location.hash,
        current_slide = 1,
        total_slides = $("#home_slide_nav a").length,
        slide_width = $($("#home_slide_holder .home_slide")[current_slide-1]).width();

    // num is a positive int representing the slide to go to (1-indexed)
    function go_to_slide(num) {
        $($("#home_slide_nav a")[current_slide-1]).removeClass("home_slide_nav_selected");
        $($("#home_slide_nav a")[num-1]).addClass("home_slide_nav_selected");
        $("#home_slide_holder").animate({
            left: (num - 1) * slide_width * -1
        });
        window.location.hash = num;
        current_slide = num;        
    }

    // See if there is a location hash and select the right slide nav if there is
    if( /^#(\d+)$/.exec(hash) ) {
        go_to_slide(parseInt(hash.substring(1), 10));
    }
    //Bind action to slide nav click
    $("#home_slide_nav a").live("click", function () {
        // Pull the slide we're about to move to from the anchor's position relative to its parent
        var requested_slide = $(this).index() + 1;
        if (requested_slide === current_slide) {
            return false;
        } else {
            go_to_slide(requested_slide);
	    return false;
        }
    });
    
    // Bind to the prev link
    $("#home_slide_nav_prev").live("click", function () {
        if (current_slide === 1) {
            go_to_slide(total_slides);
        } else {
            go_to_slide(current_slide - 1);
        }
        return false;
    });

    // Bind to the next link 
    $("#home_slide_nav_next").live("click", function () {
        if (current_slide === total_slides) {
            go_to_slide(1);
        } else {
            go_to_slide(current_slide + 1);
        }
        return false;
    });

    // Create an account link should advance to the 4th slide with a sign up form
    $("#home_account_link").live("click", function () {
        go_to_slide(4);
        return false;
    });

});
