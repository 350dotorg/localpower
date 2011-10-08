/*jslint maxerr: 1000, white: true, browser: true, devel: true, rhino: true, onevar: false, undef: true, nomen: true, eqeqeq: true, plusplus: true, bitwise: true, regexp: true, newcap: true, immed: true, sub: true */
/*global $: false, FB: false, WebFont: false, jQuery: false, window: false, google: false, require: false, define: false */
require([], function () {
    var hash = window.location.hash,
        current_slide = 1,
        total_slides = 4,
        slide_width = $("#home_slide_" + current_slide).width();

    // num is a positive int representing the slide to go to (1-indexed)
    function go_to_slide(num) {
        $("#home_slide_nav_" + current_slide).removeClass("home_slide_nav_selected");
        $("#home_slide_nav_" + num).addClass("home_slide_nav_selected");
        $("#home_slide_holder").animate({
            left: (num - 1) * slide_width * -1
        });
        window.location.hash = num;
        current_slide = num;        
    }

    // See if there is a location hash and select the right slide nav if there is
    if (hash === "#1" || hash === "#2" || hash === "#3" || hash === "#4") {
        go_to_slide(parseInt(hash.substring(1), 10));
    }
    //Bind action to slide nav click
    $("#home_slide_nav a").live("click", function () {
        // Pull the slide we're about to move to from the href (e.g. "#3" --> 3)
        var requested_slide = parseInt($(this).attr("href").substring(1), 10);
        if (requested_slide === current_slide) {
            return false;
        } else {
            go_to_slide(requested_slide);
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
