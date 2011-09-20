/*jslint maxerr: 1000, white: true, browser: true, devel: true, rhino: true, onevar: false, undef: true, nomen: true, eqeqeq: true, plusplus: true, bitwise: true, regexp: true, newcap: true, immed: true, sub: true */
/*global $: false, RAH: false, FB: false, WebFont: false, jQuery: false, window: false, google: false, require: false, define: false */
require(["mods/comments", "libs/jquery.ui", "libs/jquery.qtip"], function (comments) {

    comments.setup();

    $("div.date_commit_field").parent().hide();
    $(".group_action_form_picker").change(function() {
	    var group = $(this).val();
	    $(this).closest(".group_action_form_container").find("div.group_action_form_group").hide();
	    $(this).closest(".group_action_form_container").find("div.group_action_form_group." + group).show();
    });
    $(".commit_trigger").click(function () {
	    $(".action_commit_form").removeClass("active");
	    $(this).closest("form.action_commit_form").addClass("active");
	    $("#commit_widget").dialog("open");
        return false;
    });
    $(".undo_trigger").click(function () {
        $(".action_undo_form").submit();
    });
    $("#commit_widget").dialog({
        title: "Make a Commitment", 
        modal: true, 
        resizable: false, 
        draggable: false, 
        autoOpen: false, 
        width: 550,
        height: 450,
        open: function () {
	    $(this).find(".commit_calendar").datepicker({
                dateFormat: "yy-mm-dd", 
		defaultDate: $(".active input.date_commit_field").val(),
                maxDate: "+2y", 
                minDate: "0", 
                numberOfMonths: 2,
                onSelect: function (dateText, inst) { 
                    $(".active .date_commit_field").val(dateText);
                }
            });
        },
        buttons: { 
            "Commit": function () {
                $("#commit_widget").dialog("close");
                var form = $(".action_commit_form.active");
                form.submit();
            }
        }
    });
    $(".commit_cancel").click(function () {
        if (confirm("Are you sure you want to cancel your commitment?")) {
            $(this).closest(".action_forms").find(".action_cancel_form").submit();
        }
        return false; 
    });
    $(".action_forms .tooltip").qtip({
        position: {
            corner: {
                target: "bottomMiddle",
                tooltip: "topMiddle"
            }
        },
        style: {
            name: "green",
            tip: "topMiddle",
            background: "#E3EC9F",
            color: "#00AAD8",
            border: {
                width: 3,
                radius: 2,
                color: "#92C139"
            }
        },
        show: "mouseover",
        hide: "mouseout"
    });
});

