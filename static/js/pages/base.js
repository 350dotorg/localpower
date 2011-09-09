/*jslint maxerr: 1000, white: true, browser: true, devel: true, rhino: true, onevar: false, undef: true, nomen: true, eqeqeq: true, plusplus: true, bitwise: true, regexp: true, newcap: true, immed: true, sub: true */
/*global $: false, RAH: false, FB: false, jQuery: false, window: false, google: false, require: false, define: false */
require(["libs/jquery.ui", "libs/jquery.form", "libs/jquery.validation", "mods/messages", "mods/facebook"],
    function (ui, form, validation, messages, facebook) {

        // Setup datepicker
	    //$("input.datepicker").datepicker();

        // setup tabs
        $(".tabs").tabs();

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
        facebook.setup();
    });
