/*jslint maxerr: 1000, white: true, browser: true, devel: true, rhino: true, onevar: false, undef: true, nomen: true, eqeqeq: true, plusplus: true, bitwise: true, regexp: true, newcap: true, immed: true, sub: true */
/*global $: false, RAH: false, FB: false, WebFont: false, jQuery: false, window: false, google: false, require: false, define: false */
define(function () {
    return {
        setup: function () {
            $("#message_box").delegate(".dismiss", "click", function () {
                $(this).parents(".messages").slideUp(400, function () {
                    $(this).remove();
                });
                return false;
            });
            this.auto_remove_messages();
        },
        auto_remove_messages: function () {
            $(".messages:not(.sticky)").each(function () {
                var elem = $(this);
                setTimeout(function () {
                    elem.slideUp(400, function () {
                        elem.remove();
                    });
                }, 5000);
            });
        },
        add_message: function (html) {
            if (html) {
                $("#message_box").hide().append(html).slideDown();
            }
            this.auto_remove_messages();
        }
    };
});
