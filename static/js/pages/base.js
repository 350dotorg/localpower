/*jslint maxerr: 1000, white: true, browser: true, devel: true, rhino: true, onevar: false, undef: true, nomen: true, eqeqeq: true, plusplus: true, bitwise: true, regexp: true, newcap: true, immed: true, sub: true */
/*global $: false, RAH: false, FB: false, WebFont: false, jQuery: false, window: false, google: false, require: false, define: false */
require(["libs/jquery.ui", "libs/jquery.form", "libs/jquery.validation", "mods/feedback", "mods/messages", "mods/facebook"],
    function (ui, form, validation, feedback, messages, facebook) {
        // setup buttons
        //$("button, input:submit, a.button, input.button").button();
        //$(".buttonset").buttonset();
        
        // Setup datepicker
        $(".datepicker").datepicker();
        
        // setup tabs
        $(".tabs").tabs();

        // Highlight the right nav option if specified
        var rah_nav_select = RAH.ENV.nav_select;
        if (typeof(rah_nav_select) !== 'undefined' && rah_nav_select !== '') {
            $("#" + rah_nav_select).addClass("selected");
        }
        
        $.ajaxSetup({
            error: function (XMLHttpRequest, textStatus) { 
                var error_msg = $("<ul/>")
                    .attr({"class": "plain_list shadow"})
                    .append("<li/>")
                        .attr({"class": "messages error sticky"})
                        .text(textStatus)
                        .append("<a/>")
                            .attr({"href": "#", "class": "dismiss"})
                            .text("close");
                messages.add_message(error_msg);
            }
        });

        $.validator.setDefaults({
            submitHandler: function (form) {
                form.submit();
            }
        });

        messages.setup();
        feedback.setup();
        facebook.setup();
    });
