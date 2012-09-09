/*jslint maxerr: 1000, white: true, browser: true, devel: true, rhino: true, onevar: false, undef: true, nomen: true, eqeqeq: true, plusplus: true, bitwise: true, regexp: true, newcap: true, immed: true, sub: true */
/*global $: false, RAH: false, FB: false, jQuery: false, window: false, google: false, require: false, define: false */
require(["libs/jquery.ui", "libs/jquery.form", "libs/jquery.validation", "mods/messages", "mods/facebook"],
    function (ui, form, validation, messages, facebook) {
        var LANG = $("meta[http-equiv='content-language']").attr("content");

	jQuery.ajax({
		    async: false,
		    type: "GET",
		    url: "/static/js/i18n/jquery.ui.datepicker-" + LANG + ".js",
		    data: null,
		    dataType: 'script'
		    });

        // Setup datepicker
	$("input.datepicker").datepicker();

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

	$("#language_dropdown").dialog({
		modal: true,
		autoOpen: false,
		resizable: true, draggable: true,
		width: 360
	});
	$("#header_language").click(function() {
	    $("#language_dropdown").dialog('open');
	    return false;
	});

    });
